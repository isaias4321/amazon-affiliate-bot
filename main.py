import os
import time
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.background import BackgroundScheduler

# -----------------------------------------------------
# CONFIGURAÇÕES PRINCIPAIS
# -----------------------------------------------------
TELEGRAM_TOKEN = "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A"
GROUP_ID = "-4983279500"
AFFILIATE_TAG = "isaias06f-20"
SCRAPEOPS_API_KEY = "3694ad1e-583c-4a39-bdf9-9de5674814ee"

# -----------------------------------------------------
# LOGGING
# -----------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)

# -----------------------------------------------------
# FUNÇÃO DE BUSCA DE OFERTAS
# -----------------------------------------------------
def buscar_ofertas(categoria):
    """
    Busca ofertas reais na Amazon Brasil via ScrapeOps.
    Filtra apenas promoções com 15% de desconto ou mais.
    """
    logger.info(f"🔍 Buscando ofertas em '{categoria}'...")

    url = f"https://www.amazon.com.br/s?k={categoria}&tag={AFFILIATE_TAG}"

    try:
        proxy_url = "https://proxy.scrapeops.io/v1/"
        params = {
            "api_key": SCRAPEOPS_API_KEY,
            "url": url,
        }

        response = requests.get(proxy_url, params=params, timeout=30)
        response.raise_for_status()

        logger.info(f"✅ HTML recebido para '{categoria}' ({response.status_code} OK)")

        # ✅ USAR PARSER NATIVO COMPATÍVEL
        soup = BeautifulSoup(response.text, "html.parser")

        produtos = []
        itens = soup.select("div[data-component-type='s-search-result']")

        for item in itens:
            nome_elem = item.select_one("h2 a span")
            preco_elem = item.select_one("span.a-price > span.a-offscreen")
            preco_antigo_elem = item.select_one("span.a-text-price > span.a-offscreen")
            link_elem = item.select_one("h2 a")

            if not (nome_elem and preco_elem and link_elem):
                continue

            nome = nome_elem.text.strip()
            preco = preco_elem.text.strip().replace("R$", "").replace(",", ".").strip()
            preco = float(preco) if preco else 0.0

            if preco_antigo_elem:
                preco_antigo = preco_antigo_elem.text.strip().replace("R$", "").replace(",", ".").strip()
                preco_antigo = float(preco_antigo) if preco_antigo else 0.0
            else:
                preco_antigo = 0.0

            if preco_antigo > preco:
                desconto = round((1 - preco / preco_antigo) * 100, 1)
            else:
                desconto = 0

            if desconto >= 15:
                link_produto = f"https://www.amazon.com.br{link_elem['href'].split('?')[0]}?tag={AFFILIATE_TAG}"

                produtos.append({
                    "nome": nome,
                    "preco_atual": f"R$ {preco:.2f}".replace(".", ","),
                    "preco_antigo": f"R$ {preco_antigo:.2f}".replace(".", ",") if preco_antigo else "—",
                    "desconto": f"{desconto}%",
                    "link": link_produto,
                })

        logger.info(f"🔍 {len(produtos)} ofertas encontradas em {categoria}")
        return produtos

    except Exception as e:
        logger.error(f"❌ Erro ao buscar {categoria}: {e}")
        return []


# -----------------------------------------------------
# ENVIO DAS OFERTAS PARA O TELEGRAM
# -----------------------------------------------------
def enviar_para_telegram(produtos, categoria):
    if not produtos:
        logger.info(f"⚠️ Nenhuma oferta válida encontrada em {categoria}.")
        return

    for p in produtos:
        msg = (
            f"🔥 *{p['nome']}*\n\n"
            f"💰 De: ~{p['preco_antigo']}~\n"
            f"✅ Por: *{p['preco_atual']}*\n"
            f"💥 Desconto: *{p['desconto']}*\n\n"
            f"[🛒 Ver na Amazon]({p['link']})"
        )

        try:
            bot.send_message(
                chat_id=GROUP_ID,
                text=msg,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True,
            )
            time.sleep(5)
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem: {e}")


# -----------------------------------------------------
# CICLO PRINCIPAL
# -----------------------------------------------------
def ciclo_de_busca():
    logger.info("🔄 Iniciando ciclo de busca de ofertas...")
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]

    for categoria in categorias:
        produtos = buscar_ofertas(categoria)
        enviar_para_telegram(produtos, categoria)

    logger.info("✅ Ciclo concluído!")


# -----------------------------------------------------
# AGENDADOR
# -----------------------------------------------------
if __name__ == "__main__":
    logger.info("🤖 Iniciando bot Amazon Ofertas Brasil (5 em 5 minutos)...")

    scheduler = BackgroundScheduler()
    scheduler.add_job(ciclo_de_busca, "interval", minutes=5)
    scheduler.start()

    # Executa a primeira busca imediatamente
    ciclo_de_busca()

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        scheduler.shutdown()
        logger.info("🛑 Bot finalizado.")
