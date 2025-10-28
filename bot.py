import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler

# ------------------------- CONFIGURAÇÃO DE LOGS -------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------- VARIÁVEIS GERAIS -------------------------
TOKEN = os.getenv("BOT_TOKEN")  # Token do BotFather
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = f"https://amazon-ofertas-api.up.railway.app/webhook/{TOKEN}"

app = Flask(__name__)

# ------------------------- HANDLERS DO BOT -------------------------
async def start(update: Update, context):
    """Responde ao comando /start"""
    await update.message.reply_text("🤖 Olá! O bot está ativo e monitorando ofertas.")

async def start_posting(update: Update, context):
    """Responde ao comando /start_posting"""
    await update.message.reply_text("🚀 O bot começou a postar automaticamente as ofertas!")

# ------------------------- APLICAÇÃO TELEGRAM -------------------------
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("start_posting", start_posting))

# ------------------------- WEBHOOK SÍNCRONO -------------------------
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    """Versão síncrona — compatível com Flask normal"""
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        asyncio.run(application.process_update(update))
        logger.info("✅ Update recebido e processado com sucesso (modo síncrono).")
    except Exception as e:
        logger.error(f"❌ Erro ao processar update: {e}")
    return "ok", 200

# ------------------------- CONFIGURAÇÃO DE TAREFAS -------------------------
def postar_oferta():
    """Simulação de postagem automática"""
    logger.info("🛍️ Verificando novas ofertas...")

scheduler = BackgroundScheduler()
scheduler.add_job(postar_oferta, "interval", minutes=2)
scheduler.start()

# ------------------------- INICIALIZAÇÃO -------------------------
async def configurar_webhook():
    logger.info("🌍 Configurando webhook atual...")
    try:
        await application.bot.delete_webhook()
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"✅ Webhook configurado: {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"❌ Erro ao configurar webhook: {e}")

def start_bot():
    """Inicia o Flask e o webhook"""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(configurar_webhook())
    logger.info("🚀 Bot iniciado e escutando comandos!")
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    start_bot()
