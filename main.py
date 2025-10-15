import os
import random
import asyncio
import logging
import aiohttp
from fastapi import FastAPI, Query
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.constants import ParseMode
import uvicorn

# 🔧 Configurações e logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 🔐 Variáveis de ambiente
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "seu-tag-aqui")

# 🧠 Inicializa API e bot
app = FastAPI()
bot = Bot(token=BOT_TOKEN)

# ------------------------------------------------------------------
# 🔹 API ENDPOINT
# ------------------------------------------------------------------
@app.get("/")
def home():
    return {"status": "online", "message": "🚀 API e Bot Amazon Affiliate estão ativos!"}

@app.get("/buscar")
def buscar(q: str = Query(..., description="Categoria de produto")):
    produtos_exemplo = [
        {
            "titulo": f"{q.title()} Ultra 2025",
            "preco": "R$ 2.499,00",
            "link": f"https://www.amazon.com.br/s?k={q.replace(' ', '+')}&tag={AFFILIATE_TAG}",
            "imagem": "https://m.media-amazon.com/images/I/71KZfQA-Y7L._AC_SL1500_.jpg",
        },
        {
            "titulo": f"{q.title()} Max Performance",
            "preco": "R$ 3.299,00",
            "link": f"https://www.amazon.com.br/s?k={q.replace(' ', '+')}&tag={AFFILIATE_TAG}",
            "imagem": "https://m.media-amazon.com/images/I/81QpkIctqPL._AC_SL1500_.jpg",
        },
    ]
    return random.choice(produtos_exemplo)

# ------------------------------------------------------------------
# 🔹 Lógica do bot
# ------------------------------------------------------------------
async def buscar_produto(categoria: str):
    """Busca 1 produto da categoria via API local."""
    url = f"http://localhost:8000/buscar?q={categoria}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Erro HTTP {resp.status} ao buscar {categoria}")
                    return None
                return await resp.json()
        except Exception as e:
            logger.error(f"Erro ao buscar {categoria}: {e}")
            return None

async def enviar_oferta(produto, categoria):
    if not produto:
        return
    msg = (
        f"🛒 <b>{produto['titulo']}</b>\n"
        f"💰 {produto['preco']}\n"
        f"🔗 <a href='{produto['link']}'>Ver oferta na Amazon</a>\n"
        f"🏷️ Categoria: {categoria}"
    )
    await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode=ParseMode.HTML)

async def job_busca_envio():
    categorias = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]
    for categoria in categorias:
        produto = await buscar_produto(categoria)
        await enviar_oferta(produto, categoria)
    logger.info("✅ Ciclo concluído!")

async def iniciar_bot():
    logger.info("🤖 Bot de Ofertas Amazon iniciado com sucesso!")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_busca_envio, "interval", minutes=10)
    scheduler.start()
    await job_busca_envio()
    while True:
        await asyncio.sleep(60)

# ------------------------------------------------------------------
# 🔹 Inicialização unificada
# ------------------------------------------------------------------
if __name__ == "__main__":
    loop = asyncio.get_event_loop()

    async def main():
        asyncio.create_task(iniciar_bot())
        config = uvicorn.Config(app=app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
        server = uvicorn.Server(config)
        await server.serve()

    loop.run_until_complete(main())
