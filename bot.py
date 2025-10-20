import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# === CONFIGURAÇÕES DO BOT ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ A variável de ambiente BOT_TOKEN não está definida!")

# === LOGGING CONFIGURADO ===
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === COMANDOS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "👋 Olá! Sou seu bot e estou pronto para te ajudar!\n"
        "Use /ajuda para ver os comandos disponíveis."
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /ajuda"""
    await update.message.reply_text(
        "ℹ️ Comandos disponíveis:\n"
        "/start - Inicia o bot\n"
        "/ajuda - Mostra esta mensagem\n"
        "Ou envie qualquer mensagem para eu repetir!"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde o que o usuário digitar"""
    texto = update.message.text
    await update.message.reply_text(f"Você disse: {texto}")

# === FUNÇÃO PRINCIPAL ===
def main():
    logging.info("🚀 Iniciando bot...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    # Adiciona os handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logging.info("✅ Bot iniciado e aguardando mensagens...")
    app.run_polling(close_loop=False)  # evita o erro do loop no Render

# === EXECUÇÃO ===
if __name__ == "__main__":
    main()
