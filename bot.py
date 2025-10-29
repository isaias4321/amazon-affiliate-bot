import os
import logging
import asyncio
import nest_asyncio
from quart import Quart, request  # ⬅️ Substitui Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# --------------------------------------------------
# 🔧 CONFIGURAÇÕES INICIAIS
# --------------------------------------------------
load_dotenv()
nest_asyncio.apply()

# ✅ Um único event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# --------------------------------------------------
# 🔑 VARIÁVEIS DE AMBIENTE
# --------------------------------------------------
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "https://amazon-ofertas-api.up.railway.app")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --------------------------------------------------
# 🧠 LOGS
# --------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --------------------------------------------------
# 🚀 QUART (async Flask) + TELEGRAM
# --------------------------------------------------
app = Quart(__name__)
app_tg = Application.builder().token(TOKEN).build()

# --------------------------------------------------
# 🧩 COMANDOS DO BOT
# --------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot de ofertas pronto para começar!")

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Postagem automática iniciada aqui!")
    asyncio.create_task(postar_oferta(context))

# --------------------------------------------------
# 🛍️ FUNÇÃO DE POSTAGEM
# --------------------------------------------------
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🛍️ Verificando novas ofertas...")
    try:
        ofertas = [
            {"titulo": "SSD Kingston 1TB NV2", "link": "https://mercadolivre.com/exemplo"},
            {"titulo": "Furadeira Bosch 220V", "link": "https://mercadolivre.com/exemplo2"},
        ]
        for o in ofertas:
            msg = f"🔥 *{o['titulo']}*\n🔗 {o['link']}"
            await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        logger.info("✅ Ofertas enviadas com sucesso!")
    except Exception as e:
        logger.error(f"❌ Erro ao postar ofertas: {e}")

# --------------------------------------------------
# 🌐 WEBHOOK
# --------------------------------------------------
@app.post(f"/webhook/{TOKEN}")
async def webhook():
    try:
        data = await request.get_json()
        update = Update.de_json(data, app_tg.bot)
        await app_tg.process_update(update)
    except Exception as e:
        logger.error(f"❌ Erro no webhook: {e}")
    return "ok"

# --------------------------------------------------
# ⏰ AGENDADOR
# --------------------------------------------------
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: logger.info("🕒 Checando ofertas..."), "interval", minutes=2)
scheduler.start()

# --------------------------------------------------
# ⚙️ REGISTRA COMANDOS
# --------------------------------------------------
app_tg.add_handler(CommandHandler("start", cmd_start))
app_tg.add_handler(CommandHandler("start_posting", cmd_start_posting))

# --------------------------------------------------
# 🚀 INICIALIZAÇÃO
# --------------------------------------------------
async def init_bot():
    await app_tg.bot.delete_webhook()
    webhook_url = f"{WEBHOOK_BASE}/webhook/{TOKEN}"
    await app_tg.bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook configurado: {webhook_url}")

    await app_tg.initialize()
    await app_tg.start()
    logger.info("🤖 Bot e scheduler iniciados com sucesso!")

if __name__ == "__main__":
    loop.run_until_complete(init_bot())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
