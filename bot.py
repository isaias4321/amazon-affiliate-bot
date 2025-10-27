import os
import asyncio
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ml_api import buscar_produto_mercadolivre
from shopee_api import buscar_produto_shopee

# ========== CONFIGURAÇÃO ==========
PORT = int(os.environ.get("PORT", 8080))
TOKEN = os.environ.get("BOT_TOKEN")

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# ========== FUNÇÕES DO BOT ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Olá! Estou ativo e pronto para buscar ofertas automaticamente!")

async def oferta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Buscando ofertas...")

    produto = await buscar_produto_mercadolivre()
    if not produto:
        produto = await buscar_produto_shopee()

    if produto:
        msg = f"💥 {produto['titulo']}\n💰 R$ {produto['preco']}\n🔗 {produto['link']}"
    else:
        msg = "⚠️ Nenhuma oferta encontrada no momento."

    await update.message.reply_text(msg)

# ========== AGENDAMENTO ==========

async def postar_oferta():
    logger.info("🕐 Executando tarefa automática de postagem de oferta...")
    produto = await buscar_produto_mercadolivre() or await buscar_produto_shopee()
    if produto:
        bot = Bot(token=TOKEN)
        msg = f"🔥 Oferta do momento:\n\n💥 {produto['titulo']}\n💰 R$ {produto['preco']}\n🔗 {produto['link']}"
        await bot.send_message(chat_id="@seu_canal_aqui", text=msg)
        logger.info("✅ Oferta postada com sucesso!")
    else:
        logger.warning("⚠️ Nenhuma oferta encontrada para postar.")

# ========== CONFIGURAÇÃO DO TELEGRAM ==========
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("oferta", oferta))

# ========== WEBHOOK FLASK ==========
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok"

async def setup_webhook():
    logger.info("🧹 Limpando webhooks antigos...")
    await application.bot.delete_webhook(drop_pending_updates=True)

    url = f"https://{os.environ.get('RAILWAY_STATIC_URL')}/webhook/{TOKEN}"
    await application.bot.set_webhook(url)
    logger.info(f"✅ Webhook configurado com sucesso: {url}")

# ========== INICIALIZAÇÃO ==========
if __name__ == "__main__":
    async def start_async():
        try:
            await setup_webhook()
        except Exception as e:
            logger.error(f"❌ Erro ao configurar webhook: {e}")

    loop = asyncio.get_event_loop()
    loop.create_task(start_async())

    # Inicia o agendador
    scheduler.add_job(postar_oferta, "interval", minutes=2)
    scheduler.start()

    # Inicia o Flask
    app.run(host="0.0.0.0", port=PORT)
