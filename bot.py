import os
import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests
import random

# ==================== CONFIGURAÇÕES GERAIS ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # ID do grupo ou canal para postar ofertas

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==================== FUNÇÃO DE SEGURANÇA ====================
def stop_previous_bot_instances():
    """Evita conflito de polling encerrando instâncias antigas."""
    try:
        if BOT_TOKEN:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                logging.info("🧹 Webhook antigo removido (evita conflito de polling).")
    except Exception as e:
        logging.warning(f"Falha ao limpar webhooks antigos: {e}")

# ==================== HANDLERS DE COMANDOS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Sou seu bot de ofertas automáticas.")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Use /start_posting para começar a postar ofertas automaticamente.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    await update.message.reply_text(f"Você disse: {texto}")

# ==================== SISTEMA DE POSTAGENS ====================
async def buscar_ofertas():
    """Simula a busca de ofertas (pode ser substituído por raspagem futura)."""
    ofertas = [
        {
            "titulo": "🔥 Echo Dot 5ª geração com Alexa",
            "link": "https://www.amazon.com.br/dp/B09B8V1LZ3?tag=SEULINK",
            "preco": "R$ 279,00",
        },
        {
            "titulo": "💻 Notebook Lenovo IdeaPad 3",
            "link": "https://www.amazon.com.br/dp/B0C3V7T6ZK?tag=SEULINK",
            "preco": "R$ 2.399,00",
        },
        {
            "titulo": "🎧 Fone Bluetooth JBL Tune 510BT",
            "link": "https://www.amazon.com.br/dp/B08WSY9RRG?tag=SEULINK",
            "preco": "R$ 279,00",
        }
    ]
    return ofertas if random.choice([True, False]) else []

async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    ofertas = await buscar_ofertas()
    if not ofertas:
        logging.info("Nenhuma promoção encontrada no momento.")
        return

    chat_id = CHAT_ID
    if not chat_id:
        logging.warning("CHAT_ID não configurado. Nenhum grupo para postar.")
        return

    for oferta in ofertas:
        msg = f"📦 *{oferta['titulo']}*\n💰 {oferta['preco']}\n🔗 [Ver oferta]({oferta['link']})"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        await asyncio.sleep(2)

# ==================== FUNÇÃO PRINCIPAL ====================
async def main():
    logging.info("🚀 Iniciando bot...")
    stop_previous_bot_instances()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    # Handlers básicos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Agendador automático
    scheduler = AsyncIOScheduler()
    scheduler.add_job(postar_ofertas, "interval", minutes=1, args=[app])
    scheduler.start()

    logging.info("✅ Bot iniciado e aguardando mensagens...")
    await app.run_polling(close_loop=False)

# ==================== EXECUÇÃO ====================
if __name__ == "__main__":
    stop_previous_bot_instances()

    # Cria um novo loop se não existir (fix para Python 3.12 / Render)
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Executa o bot sem recriar loop
    loop.run_until_complete(main())
