import asyncio
import aiohttp
import logging
import os
import nest_asyncio
from fastapi import FastAPI
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import uvicorn

# ======================================================
# CONFIGURAÇÕES
# ======================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
API_URL = "https://amazon-affiliate-bot-production.up.railway.app/api/search"

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("❌ BOT_TOKEN e GROUP_ID são obrigatórios.")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# ======================================================
# FUNÇÕES DE PRODUTOS E POSTAGEM
# ======================================================
async def buscar_produtos():
    termos = ["notebook", "monitor", "cadeira gamer", "mouse", "pc gamer"]
    produtos = []

    async with aiohttp.ClientSession() as session:
        for termo in termos:
            try:
                async with session.get(f"{API_URL}?q={termo}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        produtos.extend(data.get("produtos", []))
            except Exception as e:
                logger.error(f"Erro ao buscar '{termo}': {e}")

    return produtos

async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE = None):
    produtos = await buscar_produtos()
    if not produtos:
        logger.info("Nenhum produto encontrado nesta busca.")
        return

    for p in produtos[:5]:
        nome = p.get("titulo", "Produto sem nome")
        preco = p.get("preco", "Preço indisponível")
        imagem = p.get("imagem")
        link = p.get("link")
        legenda = f"💥 *{nome}*\n💰 *Preço:* {preco}\n🔗 [Compre agora]({link})"

        try:
            if imagem:
                await bot.send_photo(GROUP_ID, photo=imagem, caption=legenda, parse_mode="Markdown")
            else:
                await bot.send_message(GROUP_ID, text=legenda, parse_mode="Markdown")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Erro ao enviar produto: {e}")

# ======================================================
# COMANDOS DO BOT
# ======================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot ativo! Enviando ofertas automáticas a cada 1 minuto.")
    context.job_queue.run_repeating(postar_ofertas, interval=60, first=5)

# ======================================================
# INICIAR BOT EM BACKGROUND
# ======================================================
async def iniciar_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    job = app_bot.job_queue
    job.run_repeating(postar_ofertas, interval=60, first=10)

    logger.info("🤖 Bot Telegram iniciado com sucesso.")
    await app_bot.run_polling()

# ======================================================
# ENDPOINTS FASTAPI
# ======================================================
@app.get("/")
async def root():
    return {"status": "ok", "mensagem": "🚀 API e Bot de ofertas rodando no Railway!"}

@app.get("/force")
async def force_post():
    await postar_ofertas()
    return {"status": "ok", "mensagem": "📤 Ofertas enviadas manualmente."}

# ======================================================
# EXECUÇÃO PRINCIPAL
# ======================================================
if __name__ == "__main__":
    async def main():
        # Inicia o bot em paralelo
        asyncio.create_task(iniciar_bot())

        # Roda o servidor FastAPI
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main())
