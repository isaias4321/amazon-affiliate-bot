import asyncio
import nest_asyncio
import aiohttp
import logging
import os
from fastapi import FastAPI
from threading import Thread
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ======================================================
# CONFIGURAÇÕES GERAIS
# ======================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

nest_asyncio.apply()  # Evita erros de loop já em execução

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")  # Exemplo: -4983279500
API_URL = "https://amazon-affiliate-bot-production.up.railway.app/api/search"

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("❌ As variáveis BOT_TOKEN e GROUP_ID precisam estar definidas!")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()  # Mantém o Railway ativo

# ======================================================
# FUNÇÃO PARA BUSCAR PRODUTOS NA API
# ======================================================
async def buscar_produtos():
    produtos = []
    palavras_chave = ["notebook", "monitor", "mouse", "teclado"]

    async with aiohttp.ClientSession() as session:
        for termo in palavras_chave:
            try:
                async with session.get(f"{API_URL}?q={termo}") as response:
                    if response.status == 200:
                        data = await response.json()
                        produtos.extend(data.get("produtos", []))
                    else:
                        logger.warning(f"⚠️ Erro HTTP {response.status} ao buscar {termo}")
            except Exception as e:
                logger.error(f"❌ Erro ao buscar {termo}: {e}")

    return produtos

# ======================================================
# FUNÇÃO PARA POSTAR NO GRUPO
# ======================================================
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    produtos = await buscar_produtos()
    if not produtos:
        logger.warning("⚠️ Nenhum produto encontrado.")
        return

    for produto in produtos[:5]:  # Limita para 5 por ciclo
        nome = produto.get("titulo", "Produto sem nome")
        preco = produto.get("preco", "Preço indisponível")
        imagem = produto.get("imagem")
        link = produto.get("link")

        legenda = f"💥 *{nome}*\n💰 *Preço:* {preco}\n🔗 [Compre agora]({link})"
        try:
            if imagem:
                await bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=imagem,
                    caption=legenda,
                    parse_mode="Markdown",
                )
            else:
                await bot.send_message(chat_id=GROUP_ID, text=legenda, parse_mode="Markdown")
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"❌ Erro ao postar produto: {e}")

# ======================================================
# COMANDO /start
# ======================================================
async def start(update, context):
    await update.message.reply_text("🤖 Bot de ofertas iniciado! Enviando promoções a cada minuto.")
    context.job_queue.run_repeating(postar_ofertas, interval=60, first=3)

# ======================================================
# FUNÇÃO PRINCIPAL
# ======================================================
def iniciar_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.job_queue.run_repeating(postar_ofertas, interval=60, first=10)

    logger.info("🚀 Bot iniciado e aguardando comandos...")
    application.run_polling()

# ======================================================
# SERVIDOR FASTAPI (mantém Railway online)
# ======================================================
@app.get("/")
def root():
    return {"status": "ok", "mensagem": "🤖 Bot de ofertas Amazon ativo!"}

# Inicia o bot em thread paralela
def iniciar_thread_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.to_thread(iniciar_bot))

Thread(target=iniciar_bot).start()
