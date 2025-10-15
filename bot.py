import asyncio
import aiohttp
import logging
import os
import nest_asyncio
from fastapi import FastAPI
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue
import uvicorn

# ======================================================
# CONFIGURAÇÕES GERAIS
# ======================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
API_URL = "https://amazon-affiliate-bot-production.up.railway.app/api/search"

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("❌ As variáveis BOT_TOKEN e GROUP_ID precisam estar configuradas!")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# ======================================================
# FUNÇÃO PARA BUSCAR PRODUTOS DA API
# ======================================================
async def buscar_produtos():
    produtos = []
    termos = ["notebook", "monitor", "cadeira gamer", "mouse", "pc gamer", "ferramenta"]

    async with aiohttp.ClientSession() as session:
        for termo in termos:
            try:
                async with session.get(f"{API_URL}?q={termo}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        produtos.extend(data.get("produtos", []))
                    else:
                        logger.warning(f"⚠️ Erro {resp.status} ao buscar '{termo}'")
            except Exception as e:
                logger.error(f"❌ Erro ao buscar '{termo}': {e}")

    return produtos

# ======================================================
# POSTAR OFERTAS NO GRUPO
# ======================================================
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    produtos = await buscar_produtos()
    if not produtos:
        logger.warning("⚠️ Nenhum produto encontrado nesta rodada.")
        return

    for p in produtos[:5]:
        nome = p.get("titulo", "Produto sem nome")
        preco = p.get("preco", "Preço indisponível")
        imagem = p.get("imagem")
        link = p.get("link")

        legenda = f"💥 *{nome}*\n💰 *Preço:* {preco}\n🔗 [Compre agora]({link})"
        try:
            if imagem:
                await bot.send_photo(chat_id=GROUP_ID, photo=imagem, caption=legenda, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=GROUP_ID, text=legenda, parse_mode="Markdown")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"❌ Erro ao enviar produto: {e}")

# ======================================================
# COMANDOS
# ======================================================
async def start(update, context):
    await update.message.reply_text("🤖 Bot ativo! Enviando ofertas a cada 1 minuto.")
    context.job_queue.run_repeating(postar_ofertas, interval=60, first=5)

# ======================================================
# INICIALIZAR BOT + FASTAPI JUNTOS
# ======================================================
async def main():
    # Inicializa o bot Telegram
    job_queue = JobQueue()
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .job_queue(job_queue)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    job_queue.set_application(application)
    job_queue.run_repeating(postar_ofertas, interval=60, first=10)

    # Inicializa o servidor FastAPI e o bot juntos
    async def start_fastapi():
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    logger.info("🚀 Inicializando bot e servidor web...")

    # Executa FastAPI e Telegram simultaneamente
    await asyncio.gather(application.run_polling(), start_fastapi())

# ======================================================
# ENDPOINT PARA TESTE MANUAL
# ======================================================
@app.get("/")
async def root():
    return {"status": "ok", "mensagem": "🤖 Bot de ofertas ativo no Railway!"}

@app.get("/force")
async def force_post():
    """Força o envio manual de uma rodada de ofertas."""
    await postar_ofertas(None)
    return {"status": "ok", "mensagem": "📤 Ofertas enviadas manualmente."}

# ======================================================
# EXECUÇÃO
# ======================================================
if __name__ == "__main__":
    asyncio.run(main())
