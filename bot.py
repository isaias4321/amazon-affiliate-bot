import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler

# =========================
# 🔧 CONFIGURAÇÕES INICIAIS
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN não configurado no Railway!")

app = Flask(__name__)
scheduler = BackgroundScheduler()
application = Application.builder().token(TOKEN).build()

# =====================================
# 🤖 COMANDOS DO TELEGRAM
# =====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"📩 /start recebido de @{user.username or user.first_name}")
    await update.message.reply_text(
        "🤖 Bot ativo e pronto para postar ofertas!\n"
        "Use /start_posting para iniciar as postagens automáticas."
    )

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"🚀 /start_posting recebido de @{user.username or user.first_name}")
    await update.message.reply_text("🚀 Postagens automáticas iniciadas!")
    # Aqui você pode chamar manualmente a função de postar ofertas
    # Exemplo: await postar_oferta()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("start_posting", start_posting))

# =====================================
# 🔁 FUNÇÃO AUTOMÁTICA (POSTAR OFERTAS)
# =====================================

async def postar_oferta():
    logger.info("🤖 Buscando e postando ofertas automaticamente...")
    # Aqui vai a lógica para buscar ofertas das APIs
    # Exemplo:
    # ofertas = buscar_produtos()
    # await bot.send_message(chat_id=SEU_CHAT_ID, text=f"Nova oferta: {ofertas[0]['titulo']}")
    pass

# Agendador automático (a cada 2 minutos)
scheduler.add_job(lambda: asyncio.run(postar_oferta()), "interval", minutes=2)
scheduler.start()

# =====================================
# 🌐 FLASK WEBHOOK (corrigido)
# =====================================

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
async def webhook():
    """Recebe atualizações do Telegram e as processa de forma assíncrona."""
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        logger.info("✅ Update recebido e processado com sucesso.")
    except Exception as e:
        logger.error(f"❌ Erro ao processar update: {e}")
    return "ok", 200

@app.route("/")
def index():
    return "🤖 Bot está rodando com Flask + Webhook!", 200

# =====================================
# 🚀 EXECUÇÃO PRINCIPAL
# =====================================

if __name__ == "__main__":
    logger.info("🧹 Limpando webhooks antigos...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(application.bot.delete_webhook(drop_pending_updates=True))

    logger.info("🌍 Configurando webhook atual...")
    webhook_url = f"https://amazon-ofertas-api.up.railway.app/webhook/{TOKEN}"
    loop.run_until_complete(application.bot.set_webhook(url=webhook_url))
    logger.info(f"✅ Webhook configurado: {webhook_url}")

    logger.info("🚀 Bot iniciado e escutando comandos!")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
