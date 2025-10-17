import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import buscar_ofertas_e_enviar

# Configurações principais
TOKEN = "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A"
GROUP_ID = -4983279500
WEBHOOK_URL = "https://amazon-ofertas-api.up.railway.app"
PORT = 8080

# Inicialização do app Flask
app = Flask(__name__)
application = ApplicationBuilder().token(TOKEN).build()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Funções de comando do bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot de Ofertas Amazon Brasil iniciado!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ O bot está rodando normalmente!")

async def forcarbusca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Buscando ofertas agora...")
    await buscar_ofertas_e_enviar(context.bot, GROUP_ID)

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("status", status))
application.add_handler(CommandHandler("forcarbusca", forcarbusca))

# Webhook Flask
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

@app.route("/")
def home():
    return "🤖 Amazon Ofertas Brasil está online!", 200

# Agendador de busca automática
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: application.bot.loop.create_task(buscar_ofertas_e_enviar(application.bot, GROUP_ID)), "interval", minutes=5)
scheduler.start()

if __name__ == "__main__":
    logging.info("🚀 Iniciando bot com webhook ativo...")
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=PORT)