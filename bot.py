import os
import logging
import threading
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler

# ------------------------- LOG -------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------- ENV -------------------------
TOKEN = os.getenv("BOT_TOKEN")  # Token do BotFather
if not TOKEN or ":" not in TOKEN:
    raise RuntimeError("BOT_TOKEN ausente ou inválido.")

PORT = int(os.getenv("PORT", 8080))
PUBLIC_BASE = os.getenv("PUBLIC_BASE", "https://amazon-ofertas-api.up.railway.app")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{PUBLIC_BASE}{WEBHOOK_PATH}"

# ------------------------- FLASK -------------------------
app = Flask(__name__)

# ------------------------- HANDLERS -------------------------
async def start(update, context):
    await update.message.reply_text("🤖 Olá! O bot está ativo e monitorando ofertas.")

async def start_posting(update, context):
    await update.message.reply_text("🚀 O bot começou a postar automaticamente as ofertas!")

# ------------------------- TELEGRAM APP -------------------------
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("start_posting", start_posting))

# ------------------------- CRON (exemplo) -------------------------
def postar_oferta():
    logger.info("🛍️ Verificando novas ofertas...")

scheduler = BackgroundScheduler()
scheduler.add_job(postar_oferta, "interval", minutes=2)

# ------------------------- THREAD DO BOT -------------------------
def bot_thread():
    """
    Sobe um event loop dedicado, inicializa e inicia o Application,
    configura o webhook e mantém tudo rodando.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def runner():
        # Inicializa + inicia o Application (cria update loop interno)
        await application.initialize()
        await application.start()

        # Configura webhook limpo
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            pass
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"✅ Webhook configurado: {WEBHOOK_URL}")

        # Inicia o scheduler depois que o loop está ativo
        scheduler.start()

        # Mantém o loop vivo “para sempre”
        while True:
            await asyncio.sleep(3600)

    try:
        loop.run_until_complete(runner())
    finally:
        loop.run_until_complete(application.stop())
        loop.run_until_complete(application.shutdown())
        loop.close()

# Sobe a thread do bot (loop dedicado)
t = threading.Thread(target=bot_thread, name="telegram-bot", daemon=True)
t.start()

# ------------------------- ENDPOINT DO WEBHOOK -------------------------
@app.post(WEBHOOK_PATH)
def webhook():
    """
    Endpoint síncrono: SOMENTE desserializa e enfileira o update.
    Quem processa é o event loop da thread do bot.
    """
    try:
        data = request.get_json(force=True, silent=False)
        update = Update.de_json(data, application.bot)
        application.update_queue.put_nowait(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"❌ Erro ao enfileirar update: {e}")
        return "error", 500

# ------------------------- MAIN -------------------------
if __name__ == "__main__":
    logger.info("🚀 Bot iniciado (thread do Telegram rodando). Servindo Flask...")
    app.run(host="0.0.0.0", port=PORT)
