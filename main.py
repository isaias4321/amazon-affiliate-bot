import os
import re
import time
import requests
import asyncio
import logging
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# -----------------------------------------------------
# 1. LOGGING CONFIG
# -----------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 2. VARIÁVEIS DE AMBIENTE
# -----------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY", "3694ad1e-583c-4a39-bdf9-9de5674814ee")

if not TELEGRAM_TOKEN or not GROUP_ID:
    logger.error("❌ Faltando TELEGRAM_TOKEN ou GROUP_ID nas variáveis de ambiente!")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# -----------------------------------------------------
# 3. FUNÇÃO DE BUSCA DE PRODUTOS (ScrapeOps)
# -----------------------------------------------------
def buscar_ofertas(categoria):
    """
    Busca produtos reais da Amazon filtrando apenas links válidos /dp/.
    Testa cada link para evitar páginas inexistentes.
    """
    try:
        target_url = f"https://www.amazon.com.br/s?k={categoria}"
        api_url = f"https://proxy.scrapeops.io/v1/?api_key={SCRAPEOPS_API_KEY}&url={target_url}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "pt-BR,pt;q=0.9"
        }

        resp = requests.get(api_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"⚠️ Erro HTTP {resp.status_code} ao buscar {categoria}")
            return []

        logger.info(f"✅ HTML recebido para '{categoria}' ({resp.status_code} OK)")
        soup = BeautifulSoup(resp.text, "html.parser")

        produtos = []
        blocos = soup.find_all("div", {"data-component-type": "s-search-result"})

        for bloco in blocos:
            titulo_elem = bloco.find("span", class_="a-text-normal")
            preco_elem = bloco.find("span", class_="a-price-whole")
            link_elem = bloco.find("a", class_="a-link-normal", href=True)

            if not (titulo_elem and preco_elem and link_elem):
                continue

            link_bruto = link_elem["href"]
            if "/dp/" not in link_bruto or "/gp/" in link_bruto:
                continue

            titulo = titulo_elem.get_text(strip=True)
            preco = preco_elem.get_text(strip=True).replace(".", "")
            link = f"https://www.amazon.com.br{link_bruto.split('?')[0]}?tag={AFFILIATE_TAG}"

            # Testa se o link realmente funciona
            try:
                test_resp = requests.head(link, allow_redirects=True, timeout=10)
                if test_resp.status_code >= 400:
                    logger.warning(f"🚫 Link inválido ignorado: {link}")
                    continue
            except Exception:
                logger.warning(f"⚠️ Falha ao testar link: {link}")
                continue

            # Heurística simples para promoções
            if re.search(r"(\d{1,2}%|off|desconto|oferta|promo)", titulo, re.I):
                produtos.append({
                    "titulo": titulo,
                    "preco": f"R$ {preco}",
                    "categoria": categoria,
                    "link": link
                })
            else:
                try:
                    preco_num = float(preco.replace(",", "."))
                    if preco_num < 400:
                        produtos.append({
                            "titulo": titulo,
                            "preco": f"R$ {preco}",
                            "categoria": categoria,
                            "link": link
                        })
                except ValueError:
                    continue

        if not produtos:
            logger.warning(f"⚠️ Nenhuma promoção encontrada em {categoria}")
        else:
            logger.info(f"✅ {len(produtos)} produtos válidos encontrados em {categoria}")

        return produtos[:5]

    except Exception as e:
        logger.error(f"❌ Erro ao buscar ofertas de {categoria}: {e}")
        return []

# -----------------------------------------------------
# 4. ENVIO PARA TELEGRAM
# -----------------------------------------------------
async def enviar_oferta_telegram(oferta):
    """
    Envia uma mensagem de oferta formatada para o grupo.
    """
    mensagem = (
        f"🔥 <b>OFERTA RELÂMPAGO AMAZON ({oferta['categoria'].upper()})</b>\n\n"
        f"🛒 <i>{oferta['titulo']}</i>\n\n"
        f"💰 <b>Preço:</b> {oferta['preco']}\n"
        f"➡️ <a href=\"{oferta['link']}\">COMPRAR AGORA</a>"
    )

    try:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=mensagem,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
        logger.info(f"✅ Oferta enviada: {oferta['titulo']}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem para o Telegram: {e}")

# -----------------------------------------------------
# 5. CICLO PRINCIPAL
# -----------------------------------------------------
async def job_buscar_e_enviar():
    """
    Executa o ciclo completo: busca -> filtra -> envia.
    """
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca...")

    for categoria in categorias:
        ofertas = buscar_ofertas(categoria)
        for oferta in ofertas:
            await enviar_oferta_telegram(oferta)
            await asyncio.sleep(10)

    logger.info("✅ Ciclo concluído!\n")

# -----------------------------------------------------
# 6. LOOP PRINCIPAL
# -----------------------------------------------------
async def main():
    logger.info("🤖 Iniciando bot Amazon Affiliate (promoções reais, ScrapeOps ativo)...")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=5)

    # Executa imediatamente ao iniciar
    await job_buscar_e_enviar()

    scheduler.start()
    await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot encerrado manualmente.")
