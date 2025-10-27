import os
import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
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

# Variáveis de ambiente
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


# 🛒 Função principal de postagens automáticas
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
        disable_web_page_preview=False,
    )


# 🧠 Comando /start para testar o bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Olá! O bot está ativo e monitorando ofertas.")


# 🚀 Função principal
async def main():
    if not TOKEN:
        logger.error("❌ TELEGRAM_TOKEN não configurado!")
        return

    await limpar_webhook(TOKEN)

    application = Application.builder().token(TOKEN).build()

    # Comandos do bot
    application.add_handler(CommandHandler("start", start))

    # Agendamento automático de postagens
    scheduler.add_job(postar_oferta, "interval", minutes=2, args=[application.bot])
    scheduler.start()

    logger.info("🚀 Bot iniciado e escutando comandos.")
    await application.run_polling(close_loop=False)


# 🧠 Corrige o erro “RuntimeError: event loop is already running”
if __name__ == "__main__":
    import nest_asyncio

    nest_asyncio.apply()

    try:
        asyncio.get_event_loop().run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot encerrado manualmente.")
