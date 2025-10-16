import os
import asyncio
import logging
import random
import aiohttp
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ---------------- CONFIGURAÇÕES ----------------
load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_CHAT_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")

SCRAPEOPS_PROXY = "https://proxy.scrapeops.io/v1/"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (X11; Linux x86_64)",
]

if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN não configurado!")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# ---------------- FUNÇÕES PRINCIPAIS ----------------

async def buscar_produtos_amazon(termo):
    """
    Busca produtos reais da Amazon BR via ScrapeOps Proxy
    """
    url = SCRAPEOPS_PROXY
    params = {
        "api_key": SCRAPEOPS_API_KEY,
        "url": f"https://www.amazon.com.br/s?k={termo}",
        "country": "br"
    }
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params, headers=headers, timeout=30) as resp:
                html = await resp.text()
                logger.info(f"🔍 [{termo}] Status {resp.status}")
                return html
        except Exception as e:
            logger.error(f"Erro ao buscar {termo}: {e}")
            return None

async def enviar_mensagem_telegram(texto):
    """
    Envia mensagem formatada para o grupo no Telegram
    """
    try:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=texto,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        logger.info("✅ Mensagem enviada com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")

async def processar_e_enviar_ofertas():
    """
    Busca produtos e envia pro Telegram
    """
    termos = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]

    for termo in termos:
        html = await buscar_produtos_amazon(termo)

        if html and "Amazon" in html:
            link_amazon = f"https://www.amazon.com.br/s?k={termo}&tag={AFFILIATE_TAG}"
            mensagem = (
                f"🔥 <b>Ofertas de {termo.capitalize()} na Amazon!</b>\n"
                f"🛒 <a href='{link_amazon}'>Clique aqui para ver as promoções!</a>\n"
                f"💰 Aproveite antes que acabe!"
            )
            await enviar_mensagem_telegram(mensagem)
        else:
            logger.warning(f"⚠️ Nenhum resultado encontrado para {termo}")

        await asyncio.sleep(10)

# ---------------- AGENDA PRINCIPAL ----------------

async def main():
    logger.info("🤖 Bot Amazon Ofertas iniciado...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(processar_e_enviar_ofertas, "interval", minutes=3)
    scheduler.start()

    await processar_e_enviar_ofertas()
    await asyncio.Future()  # Mantém o bot rodando

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot finalizado manualmente.")
