import os
import logging
import asyncio
import nest_asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# --------------------------------------------------
# 🔧 CONFIGURAÇÕES INICIAIS
# --------------------------------------------------
load_dotenv()
nest_asyncio.apply()

# ✅ Garante que Flask e Telegram compartilhem o mesmo event loop
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
# 🚀 FLASK E TELEGRAM
# --------------------------------------------------
app = Flask(__name__)
app_tg = Application.builder().token(TOKEN).build()

# --------------------------------------------------
# 🧩 FUNÇÕES DE COMANDO
# --------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Olá! Estou pronto para postar suas ofertas!")

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Postagem automática iniciada aqui!")
    # Executa a rotina de postagens dentro do mesmo event loop
    asyncio.create_task(postar_oferta(context))

# --------------------------------------------------
# 🛍️ FUNÇÃO DE POSTAGEM AUTOMÁTICA
# --------------------------------------------------
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    logger.info("🛍️ Verificando novas ofertas...")
    try:
        # 🔽 Aqui entra sua lógica real (ex: Mercado Livre / Shopee)
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
# 🌐 ENDPOINT DE WEBHOOK
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
# ⚙️ REGISTRA COMANDOS
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
    loop.run_until_complete(init_bot())
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
