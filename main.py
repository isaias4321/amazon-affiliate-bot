import os
import asyncio
import logging
from telegram import Bot
from telegram.constants import ParseMode
from dotenv import load_dotenv
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from rich.logging import RichHandler

# ========== CONFIGURAÇÃO DE LOGS ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("rich")

# ========== CARREGA VARIÁVEIS ==========
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_API_URL = os.getenv("AFFILIATE_API_URL", "https://amazon-ofertas-api.up.railway.app")

if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN não definido!")
if not GROUP_ID:
    logger.error("❌ GROUP_ID não definido!")

bot = Bot(token=TELEGRAM_TOKEN)

# ========== FUNÇÃO DE BUSCA ==========
async def buscar_ofertas(categoria: str):
    """Busca ofertas na API e retorna os resultados formatados."""
    url = f"{AFFILIATE_API_URL}/buscar?q={categoria}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=60) as resp:
                logger.info(f"📡 Consultando {categoria} -> {resp.status}")
                if resp.status != 200:
                    texto = await resp.text()
                    logger.warning(f"⚠️ Erro HTTP {resp.status} ao buscar {categoria}: {texto[:200]}")
                    return None
                
                data = await resp.json()
                if data.get("status") != "ok":
                    logger.warning(f"⚠️ Nenhum resultado para {categoria}")
                    return None
                
                html_preview = data.get("html_preview", "")
                return f"🛍️ <b>Ofertas de {categoria.title()}</b>\n\n<pre>{html_preview[:800]}</pre>"
    except Exception as e:
        logger.exception(f"💥 Erro inesperado ao buscar {categoria}: {e}")
        return None

# ========== FUNÇÃO DE ENVIO ==========
async def enviar_ofertas():
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    logger.info("🚀 Iniciando verificação de ofertas...")

    for categoria in categorias:
        resultado = await buscar_ofertas(categoria)
        if resultado:
            try:
                await bot.send_message(chat_id=GROUP_ID, text=resultado, parse_mode=ParseMode.HTML)
                logger.info(f"✅ Enviado: {categoria}")
            except Exception as e:
                logger.exception(f"❌ Erro ao enviar mensagem para {categoria}: {e}")
        await asyncio.sleep(3)

    logger.info("✅ Verificação concluída com sucesso!\n")

# ========== AGENDADOR ==========
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(enviar_ofertas, "interval", minutes=30)
    scheduler.start()
    logger.info("🤖 Bot Amazon Affiliate iniciado e monitorando ofertas...")

    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("🛑 Bot finalizado manualmente.")
