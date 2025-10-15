import os
import aiohttp
import asyncio
import logging
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
API_URL = os.getenv("API_URL", "http://localhost:8000/buscar")

if not BOT_TOKEN or not GROUP_ID:
    raise SystemExit("❌ Variáveis de ambiente BOT_TOKEN e GROUP_ID ausentes!")

bot = Bot(token=BOT_TOKEN)

async def buscar_produto(categoria: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}?q={categoria}") as resp:
            data = await resp.json()
            if "erro" in data:
                logger.warning(f"Nenhum produto para {categoria}")
                return None
            return data

async def enviar_oferta(produto: dict, categoria: str):
    legenda = (
        f"🔥 <b>OFERTA AMAZON ({categoria.upper()})</b> 🔥\n\n"
        f"🛒 <b>{produto['titulo']}</b>\n"
        f"💰 <b>Preço:</b> {produto['preco']}\n\n"
        f"👉 <a href=\"{produto['link']}\">Compre com desconto aqui!</a>"
    )
    try:
        await bot.send_photo(
            chat_id=GROUP_ID,
            photo=produto["imagem"],
            caption=legenda,
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"✅ Produto enviado: {produto['titulo']}")
    except Exception as e:
        logger.error(f"Erro ao enviar oferta: {e}")

async def job_busca_envio():
    categorias = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]
    logger.info("🔁 Buscando novas ofertas...")

    for categoria in categorias:
        produto = await buscar_produto(categoria)
        if produto:
            await enviar_oferta(produto, categoria)
            await asyncio.sleep(15)

    logger.info("✅ Ciclo concluído!")

async def main():
    logger.info("🤖 Bot iniciado.")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_busca_envio, "interval", minutes=2)
    await job_busca_envio()
    scheduler.start()
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
