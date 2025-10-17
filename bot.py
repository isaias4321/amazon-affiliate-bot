import asyncio
import logging
import os
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from amazon_scraper import buscar_ofertas

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("8463817884:AAE23cMr1605qbMV4c79cMcr8F5dn0ETqRo")
GROUP_ID = os.getenv("-4983279500")

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("BOT_TOKEN e GROUP_ID precisam estar definidos.")

bot = Bot(token=BOT_TOKEN)

# ======================================================
# FUNÇÃO PRINCIPAL DE POSTAGEM
# ======================================================
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE = None):
    produtos = await buscar_ofertas()
    if not produtos:
        logger.info("Nenhum produto encontrado nas Ofertas do Dia.")
        return

    for p in produtos:
        nome = p["titulo"]
        preco = p["preco"]
        link = p["link"]
        imagem = p["imagem"]

        texto = f"🔥 *{nome}*\n💰 *Preço:* {preco}\n🔗 [Ver na Amazon]({link})"

        try:
            if imagem:
                await bot.send_photo(GROUP_ID, photo=imagem, caption=texto, parse_mode="Markdown")
            else:
                await bot.send_message(GROUP_ID, text=texto, parse_mode="Markdown")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Erro ao enviar oferta: {e}")

# ======================================================
# COMANDOS DO BOT
# ======================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot de Ofertas Amazon ativo!")
    context.job_queue.run_repeating(postar_ofertas, interval=60, first=10)

# ======================================================
# INICIAR BOT
# ======================================================
async def iniciar_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.job_queue.run_repeating(postar_ofertas, interval=60, first=10)

    logger.info("🤖 Bot Telegram iniciado.")
    await app.run_polling()
