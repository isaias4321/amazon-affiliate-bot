import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
import logging
import os

# === CONFIGURAÇÃO DO BOT ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Sou seu bot e estou pronto para te ajudar!")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Envie uma mensagem e eu irei responder!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    await update.message.reply_text(f"Você disse: {texto}")

# === FUNÇÃO PRINCIPAL ===
async def main():
    logging.info("🚀 Iniciando bot...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logging.info("✅ Bot iniciado e aguardando mensagens...")
    await app.run_polling()

# === EXECUÇÃO SEGURA ===
if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Render ou ambiente já com loop ativo
            loop.create_task(main())
            loop.run_forever()
        else:
            loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot finalizado.")
