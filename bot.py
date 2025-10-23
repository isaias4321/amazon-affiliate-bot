import logging
import asyncio
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from shopee_api import buscar_produto_shopee as buscar_shopee
from mercadolivre_api import buscar_produto_ml as buscar_mercadolivre
from dotenv import load_dotenv

# =============================
# CONFIGURAÇÕES E VARIÁVEIS
# =============================
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
INTERVALO_MINUTOS = int(os.getenv("INTERVALO_MINUTOS", 2))

scheduler = AsyncIOScheduler()
loja_atual = "Shopee"

# =============================
# LOGGING
# =============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================
# FUNÇÃO DE POSTAGEM AUTOMÁTICA
# =============================
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    global loja_atual

    try:
        if loja_atual == "Shopee":
            oferta = await buscar_shopee()
            loja_atual = "Mercado Livre"
        else:
            oferta = await buscar_mercadolivre()
            loja_atual = "Shopee"

        if not oferta:
            logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
            return

        mensagem = (
            f"🛍️ *{oferta['loja']}* 🔥\n\n"
            f"*{oferta['titulo']}*\n"
            f"💰 {oferta['preco']}\n"
            f"[🛒 Ver oferta]({oferta['link']})"
        )

        await context.bot.send_photo(
            chat_id=CHAT_ID,
            photo=oferta["imagem"],
            caption=mensagem,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Oferta enviada: {oferta['titulo']}")

    except Exception as e:
        logger.error(f"❌ Erro ao postar oferta: {e}")

# =============================
# COMANDOS DO BOT
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Use /start_posting para iniciar as postagens automáticas.")

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not scheduler.get_jobs():
        scheduler.add_job(
            postar_oferta,
            trigger="interval",
            minutes=INTERVALO_MINUTOS,
            args=[context],
        )
        scheduler.start()
        await update.message.reply_text("🕒 Postagens automáticas iniciadas!")
        logger.info("🕒 Ciclo automático iniciado via /start_posting")
    else:
        await update.message.reply_text("⚠️ O bot já está postando automaticamente!")

async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scheduler.remove_all_jobs()
    await update.message.reply_text("🛑 Postagens automáticas paradas.")
    logger.info("🛑 Postagens automáticas interrompidas.")

# =============================
# MAIN
# =============================
async def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))
    application.add_handler(CommandHandler("stop_posting", stop_posting))

    await application.bot.delete_webhook()
    await application.bot.get_updates(offset=-1)
    logger.info("🧹 Webhook limpo e atualizações antigas removidas.")
    logger.info("🚀 Bot iniciado e escutando comandos.")

    await application.run_polling(close_loop=False)

# =============================
# EXECUÇÃO SEGURA
# =============================
if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        asyncio.get_event_loop().create_task(main())
        asyncio.get_event_loop().run_forever()
