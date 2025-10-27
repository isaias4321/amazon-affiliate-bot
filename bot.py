import os
import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ml_api import buscar_produto_mercadolivre
from shopee_api import buscar_produto_shopee
from datetime import datetime

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Inicializa o agendador
scheduler = AsyncIOScheduler()

# Token do bot (Railway usa variáveis de ambiente)
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# 🧹 Remove webhooks antigos antes de iniciar o bot
async def limpar_webhook(bot_token: str):
    bot = Bot(token=bot_token)
    try:
        await bot.delete_webhook()
        logger.info("🧹 Limpando webhook anterior...")
    except Exception as e:
        logger.warning(f"⚠️ Não foi possível limpar webhook: {e}")


# 🛒 Função para postar ofertas
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    plataformas = ["MERCADOLIVRE", "SHOPEE"]
    plataforma = plataformas[datetime.utcnow().second % 2]

    logger.info(f"🤖 Buscando ofertas na plataforma: {plataforma}")

    if plataforma == "MERCADOLIVRE":
        produto = await buscar_produto_mercadolivre()
    else:
        produto = await buscar_produto_shopee()

    if not produto:
        logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
        return

    mensagem = (
        f"🔥 *OFERTA ENCONTRADA!*\n\n"
        f"🛍️ *{produto['titulo']}*\n"
        f"💰 R${produto['preco']}\n"
        f"🔗 [Ver no site]({produto['link']})"
    )

    await context.bot.send_message(
        chat_id=CHAT_ID,
        text=mensagem,
        parse_mode="Markdown",
        disable_web_page_preview=False
    )


# 🧠 Comando manual para testar o bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Olá! O bot está ativo e monitorando ofertas.")


# 🚀 Função principal
async def main():
    await limpar_webhook(TOKEN)

    application = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start))

    # Inicia agendamento de postagens
    scheduler.add_job(postar_oferta, "interval", minutes=2, args=[application.bot])
    scheduler.start()

    logger.info("🚀 Bot iniciado e escutando comandos.")
    await application.run_polling(close_loop=False)


if __name__ == "__main__":
    asyncio.run(main())
