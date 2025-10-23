import os
import asyncio
import logging
import random
import nest_asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# 🔧 Corrige event loop duplicado (Render, Replit, etc)
nest_asyncio.apply()

# 🌐 Imports das APIs
from shopee_api import buscar_produto_shopee as buscar_shopee
from ml_api import buscar_produto_mercadolivre as buscar_mercadolivre  # <- atualizado aqui

# 🚀 Configuração do log
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔑 Carrega variáveis do ambiente (.env)
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ⚙️ Scheduler para postagens automáticas
scheduler = AsyncIOScheduler()
alternador = {"plataforma": "shopee"}  # começa pela Shopee

# 🧠 Função principal de postagem automática
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    plataforma = alternador["plataforma"]

    logger.info(f"🤖 Buscando ofertas na plataforma: {plataforma.upper()}")

    if plataforma == "shopee":
        oferta = await buscar_shopee()
        alternador["plataforma"] = "mercadolivre"
    else:
        oferta = await buscar_mercadolivre()
        alternador["plataforma"] = "shopee"

    if not oferta:
        logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
        return

    msg = f"🔥 *{oferta['titulo']}*\n💰 R$ {oferta['preco']}\n🔗 [Ver oferta]({oferta['link']})"
    await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
    logger.info(f"✅ Oferta postada: {oferta['titulo']}")

# 🧩 Comando manual para começar postagens
async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    logger.info(f"🕒 Comando /start_posting iniciado por {user}")

    if not scheduler.running:
        scheduler.start()
        scheduler.add_job(postar_oferta, "interval", minutes=2, args=[context])
        await update.message.reply_text("🕒 Postagens automáticas iniciadas!")
    else:
        await update.message.reply_text("✅ O bot já está postando automaticamente.")

# 🧩 Comando para parar o bot
async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    logger.info(f"🛑 Comando /stop_posting recebido de {user}")

    if scheduler.running:
        scheduler.remove_all_jobs()
        scheduler.shutdown(wait=False)
        await update.message.reply_text("🛑 Postagens automáticas paradas.")
    else:
        await update.message.reply_text("⚠️ Nenhuma tarefa automática em andamento.")

# 🧩 Comando de inicialização
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou o bot de ofertas.\n"
        "Use /start_posting para começar a postar ofertas automaticamente!\n"
        "Use /stop_posting para parar."
    )

# 🚀 Função principal
async def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))
    application.add_handler(CommandHandler("stop_posting", stop_posting))

    logger.info("🧹 Limpando webhook anterior...")
    await application.bot.delete_webhook(drop_pending_updates=True)

    logger.info("🚀 Bot iniciado e escutando comandos.")
    await application.run_polling(close_loop=False)

# Executa o bot
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
