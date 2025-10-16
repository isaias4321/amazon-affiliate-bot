import os
import asyncio
import logging
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# -----------------------------------------------------
# 1️⃣ LOGS COLORIDOS E FORMATADOS
# -----------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 2️⃣ VARIÁVEIS DE AMBIENTE
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
# 3️⃣ FUNÇÃO DE RASPAGEM (SCRAPEOPS)
# -----------------------------------------------------
def buscar_html_amazon(query: str) -> str | None:
    """
    Faz a busca real na Amazon via ScrapeOps Proxy API.
    Retorna o HTML da página de busca.
    """
    url_base = "https://www.amazon.com.br/s"
    proxy_url = "https://proxy.scrapeops.io/v1/"

    try:
        resp = requests.get(
            proxy_url,
            params={
                "api_key": SCRAPEOPS_API_KEY,
                "url": f"{url_base}?k={query}",
            },
            timeout=25
        )

        if resp.status_code == 200:
            logger.info(f"✅ HTML recebido para '{query}' (200 OK)")
            return resp.text
        else:
            logger.warning(f"⚠️ Erro HTTP {resp.status_code} ao buscar '{query}'")
            return None

    except Exception as e:
        logger.error(f"❌ Erro ScrapeOps '{query}': {e}")
        return None

# -----------------------------------------------------
# 4️⃣ EXTRAÇÃO DE OFERTAS REAIS COM DESCONTO
# -----------------------------------------------------
def extrair_ofertas_real(html: str, categoria: str) -> list[dict]:
    """
    Extrai produtos com desconto real da Amazon e cria links válidos.
    """
    soup = BeautifulSoup(html, "html.parser")
    itens = soup.select("div.s-result-item[data-asin]")
    ofertas = []

    for item in itens[:12]:
        nome = item.select_one("h2 a span")
        preco_atual = item.select_one("span.a-price span.a-offscreen")
        preco_antigo = item.select_one("span.a-text-price span.a-offscreen")
        link = item.select_one("h2 a")

        if not nome or not preco_atual or not preco_antigo or not link:
            continue

        try:
            preco_atual_val = float(preco_atual.text.replace("R$", "").replace(".", "").replace(",", "."))
            preco_antigo_val = float(preco_antigo.text.replace("R$", "").replace(".", "").replace(",", "."))
            desconto = round(100 - (preco_atual_val / preco_antigo_val * 100), 1)
        except Exception:
            continue

        # ignora se desconto for baixo
        if desconto < 10:
            continue

        raw_link = link.get("href")
        if raw_link:
            if raw_link.startswith("/"):
                raw_link = urljoin("https://www.amazon.com.br", raw_link)

            if "tag=" not in raw_link:
                separator = "&" if "?" in raw_link else "?"
                raw_link = f"{raw_link}{separator}tag={AFFILIATE_TAG}"

        ofertas.append({
            "nome": nome.text.strip(),
            "preco_atual": f"R$ {preco_atual_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "preco_antigo": f"R$ {preco_antigo_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "desconto": desconto,
            "link": raw_link,
            "categoria": categoria.capitalize(),
        })

    return sorted(ofertas, key=lambda o: o["desconto"], reverse=True)

# -----------------------------------------------------
# 5️⃣ ENVIO PARA TELEGRAM
# -----------------------------------------------------
async def enviar_oferta_telegram(oferta: dict):
    """
    Envia mensagem formatada para o grupo Telegram.
    """
    fogo = "🔥" if oferta["desconto"] >= 20 else "💸"

    mensagem = (
        f"{fogo} <b>{oferta['categoria']} - Oferta Amazon</b>\n\n"
        f"🛍️ <i>{oferta['nome']}</i>\n"
        f"💰 <b>{oferta['preco_atual']}</b> (antes {oferta['preco_antigo']})\n"
        f"📉 Desconto: <b>{oferta['desconto']}%</b>\n\n"
        f"➡️ <a href=\"{oferta['link']}\">Ver oferta na Amazon</a>"
    )

    try:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=mensagem,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
        logger.info(f"✅ Enviado: {oferta['nome']} ({oferta['desconto']}%)")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar para Telegram: {e}")

# -----------------------------------------------------
# 6️⃣ CICLO PRINCIPAL DE BUSCA E ENVIO
# -----------------------------------------------------
async def job_buscar_e_enviar():
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca...")

    for categoria in categorias:
        html = buscar_html_amazon(categoria)
        if not html:
            continue

        ofertas = extrair_ofertas_real(html, categoria)
        if ofertas:
            for oferta in ofertas:
                await enviar_oferta_telegram(oferta)
                await asyncio.sleep(10)
        else:
            logger.warning(f"⚠️ Nenhuma oferta com desconto encontrada em {categoria}")

    logger.info("✅ Ciclo concluído!\n")

# -----------------------------------------------------
# 7️⃣ MAIN LOOP
# -----------------------------------------------------
async def main():
    logger.info("🤖 Iniciando bot Amazon Affiliate (filtro de promoções ativo)...")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=5)

    await job_buscar_e_enviar()  # roda uma vez imediatamente
    scheduler.start()

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("🛑 Bot encerrado manualmente.")

if __name__ == "__main__":
    asyncio.run(main())
