import os
import logging
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests
import random

# ==================== CONFIGURAÇÕES ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==================== LIMPA WEBHOOKS ====================
def limpar_webhook():
    try:
        if BOT_TOKEN:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
            requests.get(url, timeout=10)
            logging.info("🧹 Webhook antigo removido (evita conflito de polling).")
    except Exception as e:
        logging.warning(f"Erro ao limpar webhook: {e}")

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Sou seu bot de ofertas automáticas da Amazon!")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Use /start_posting para iniciar as postagens automáticas de ofertas!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Você disse: {update.message.text}")

# ==================== POSTAGEM DE OFERTAS ====================
async def buscar_ofertas():
    """Simula busca de ofertas"""
    ofertas = [
        {"titulo": "🔥 Echo Dot 5ª Geração com Alexa", "preco": "R$ 279,00", "link": "https://www.amazon.com.br/dp/B09B8V1LZ3"},
        {"titulo": "💻 Notebook Lenovo IdeaPad 3", "preco": "R$ 2.399,00", "link": "https://www.amazon.com.br/dp/B0C3V7T6ZK"},
        {"titulo": "🎧 Fone JBL Tune 510BT", "preco": "R$ 279,00", "link": "https://www.amazon.com.br/dp/B08WSY9RRG"},
    ]
    return random.sample(ofertas, random.randint(0, len(ofertas)))

async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    ofertas = await buscar_ofertas()
    if not ofertas:
        logging.info("Nenhuma promoção encontrada no momento.")
        return

    if not CHAT_ID:
        logging.warning("CHAT_ID não configurado — não há destino para enviar as ofertas.")
        return

    for oferta in ofertas:
        msg = f"📦 *{oferta['titulo']}*\n💰 {oferta['preco']}\n🔗 [Ver oferta]({oferta['link']})"
        await context.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        await asyncio.sleep(2)

# ==================== FUNÇÃO PRINCIPAL ====================
async def iniciar_bot():
    logging.info("🚀 Iniciando bot...")
    limpar_webhook()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Agendador
    scheduler = AsyncIOScheduler()
    scheduler.add_job(postar_ofertas, "interval", minutes=1, args=[app])
    scheduler.start()

    logging.info("✅ Bot iniciado e aguardando mensagens...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()  # mantém o bot ativo indefinidamente

# ==================== EXECUÇÃO ====================
if __name__ == "__main__":
    limpar_webhook()
    asyncio.run(iniciar_bot())
