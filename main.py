import os
import asyncio
import aiohttp
import logging
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
API_URL = os.getenv("API_URL", "https://amazon-ofertas-api.up.railway.app/buscar")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN or not GROUP_ID:
    logger.error("❌ Variáveis de ambiente ausentes! Verifique BOT_TOKEN e GROUP_ID.")
    exit(1)

bot = Bot(token=BOT_TOKEN)

CATEGORIAS = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]

async def buscar_produto(categoria: str):
    """Busca 1 produto da categoria informada usando nossa API."""
    url = f"{API_URL}?q={categoria}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Erro HTTP {resp.status} ao buscar {categoria}")
                    return None
                data = await resp.json()
                return data.get("produto")
        except Exception as e:
            logger.error(f"Erro ao buscar {categoria}: {e}")
            return None

async def enviar_oferta(produto, categoria):
    """Envia uma oferta para o grupo."""
    if not produto:
        logger.warning(f"⚠️ Nenhum produto encontrado para {categoria}")
        return

    mensagem = (
        f"🛍️ <b>{produto['titulo']}</b>\n"
        f"💰 Preço: {produto['preco']}\n"
        f"🔗 <a href='{produto['link']}?tag={AFFILIATE_TAG}'>Compre aqui</a>\n"
        f"#️⃣ Categoria: {categoria.capitalize()}"
    )

    try:
        await bot.send_message(chat_id=GROUP_ID, text=mensagem, parse_mode="HTML")
        logger.info(f"✅ Oferta enviada: {produto['titulo']}")
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")

async def job_busca_envio():
    logger.info("🔄 Iniciando ciclo de busca e envio de ofertas...")
    for categoria in CATEGORIAS:
        produto = await buscar_produto(categoria)
        await enviar_oferta(produto, categoria)
    logger.info("✅ Ciclo concluído!")

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_busca_envio, "interval", minutes=60)
    scheduler.start()

    await job_busca_envio()
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
