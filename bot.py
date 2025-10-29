import os
import asyncio
import logging
import nest_asyncio
import requests
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# --------------------------------------------------
# 🔧 CONFIGURAÇÕES INICIAIS
# --------------------------------------------------
load_dotenv()
nest_asyncio.apply()

# Garante um único event loop (evita "bound to a different event loop")
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# --------------------------------------------------
# 🔑 VARIÁVEIS DE AMBIENTE
# --------------------------------------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "https://amazon-ofertas-api.up.railway.app")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --------------------------------------------------
# 🧠 CONFIGURA LOGS
# --------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# 🚀 FLASK APP
# --------------------------------------------------
app = Flask(__name__)

# --------------------------------------------------
# 🤖 TELEGRAM BOT CONFIG
# --------------------------------------------------
app_tg = Application.builder().token(TOKEN).build()

# --------------------------------------------------
# 🛠️ FUNÇÕES DE COMANDO
# --------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Olá! Estou pronto para postar suas ofertas!")

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Postagem automática iniciada aqui!")
    context.job_queue.run_repeating(postar_oferta, interval=120, first=10)

# --------------------------------------------------
# 🛍️ FUNÇÃO DE POSTAGEM
# --------------------------------------------------
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🛍️ Verificando novas ofertas...")
    try:
        # aqui entraria sua lógica real para buscar ofertas do Mercado Livre ou Shopee
        ofertas = [
            {"titulo": "SSD 1TB Kingston NV2", "link": "https://mercadolivre.com/exemplo"},
            {"titulo": "Furadeira Bosch 220V", "link": "https://mercadolivre.com/exemplo2"}
        ]
        if not ofertas:
            logger.warning("⚠️ Nenhuma oferta encontrada.")
            return

        for oferta in ofertas:
            msg = f"🔥 *{oferta['titulo']}*\n🔗 {oferta['link']}"
            await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        logger.info("✅ Ofertas enviadas com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao postar ofertas: {e}")

# --------------------------------------------------
# 📡 CONFIGURAÇÃO DE WEBHOOK
# --------------------------------------------------
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), app_tg.bot)
        await app_tg.process_update(update)
    except Exception as e:
        logger.error(f"❌ Erro ao processar update: {e}")
    return "ok", 200

# --------------------------------------------------
# 🔁 JOB SCHEDULER
# --------------------------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: logger.info("🛍️ Verificando novas ofertas..."), "interval", minutes=2)
scheduler.start()

# --------------------------------------------------
# 🧩 REGISTRA OS COMANDOS
# --------------------------------------------------
app_tg.add_handler(CommandHandler("start", cmd_start))
app_tg.add_handler(CommandHandler("start_posting", cmd_start_posting))

# --------------------------------------------------
# 🚀 INICIALIZAÇÃO DO BOT
# --------------------------------------------------
async def init_bot():
    logger.info("🌍 Configurando webhook atual...")
    await app_tg.bot.delete_webhook()
    webhook_url = f"{WEBHOOK_BASE}/webhook/{TOKEN}"
    await app_tg.bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook configurado: {webhook_url}")
    await app_tg.initialize()
    await app_tg.start()
    logger.info("🤖 Bot e scheduler iniciados com sucesso!")

if __name__ == "__main__":
    asyncio.run(init_bot())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
