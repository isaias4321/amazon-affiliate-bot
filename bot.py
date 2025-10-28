import os
import logging
import threading
import asyncio
from datetime import datetime
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler

# ------------------------- CONFIGURAÇÃO DE LOG -------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------- VARIÁVEIS DE AMBIENTE -------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")  # ID do grupo onde o bot posta
PUBLIC_BASE = os.getenv("PUBLIC_BASE", "https://amazon-ofertas-api.up.railway.app")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{PUBLIC_BASE}{WEBHOOK_PATH}"

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN não configurado nas variáveis de ambiente.")
if not GROUP_ID:
    raise ValueError("❌ TELEGRAM_GROUP_ID não configurado nas variáveis de ambiente.")

# ------------------------- FLASK -------------------------
app = Flask(__name__)

# ------------------------- HANDLERS DE COMANDOS -------------------------
async def start(update, context):
    await update.message.reply_text("🤖 Olá! Estou ativo e pronto para postar ofertas!")

async def start_posting(update, context):
    await update.message.reply_text("🚀 O bot começou a postar automaticamente as ofertas!")

# ------------------------- FUNÇÃO DE BUSCA E POSTAGEM -------------------------
def buscar_ofertas():
    """Exemplo de busca simulada de ofertas (integre sua lógica real aqui)."""
    return [
        {
            "titulo": "SSD Kingston NV2 1TB",
            "preco": "R$ 289,90",
            "link": "https://shopee.com.br/product/123456"
        },
        {
            "titulo": "Headset Gamer Redragon Zeus X",
            "preco": "R$ 239,90",
            "link": "https://www.amazon.com.br/dp/B09Z3"
        }
    ]

def postar_oferta():
    """Busca e publica novas ofertas no grupo Telegram."""
    try:
        bot = Bot(token=BOT_TOKEN)
        logger.info("🛍️ Buscando novas ofertas...")
        ofertas = buscar_ofertas()

        if not ofertas:
            logger.warning("⚠️ Nenhuma oferta encontrada.")
            return

        for oferta in ofertas:
            mensagem = (
                f"🔥 *{oferta['titulo']}*\n"
                f"💰 {oferta['preco']}\n"
                f"🔗 [Aproveite aqui]({oferta['link']})"
            )
            bot.send_message(
                chat_id=GROUP_ID,
                text=mensagem,
                parse_mode="Markdown"
            )
        logger.info(f"✅ {len(ofertas)} ofertas publicadas às {datetime.now()}.")

    except Exception as e:
        logger.error(f"❌ Erro ao postar ofertas: {e}")

# ------------------------- TELEGRAM APPLICATION -------------------------
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("start_posting", start_posting))

# ------------------------- THREAD DO TELEGRAM -------------------------
def bot_thread():
    """Thread que gerencia o loop do Telegram e o webhook."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def runner():
        await application.initialize()
        await application.start()

        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"✅ Webhook configurado: {WEBHOOK_URL}")

        scheduler = BackgroundScheduler()
        scheduler.add_job(postar_oferta, "interval", minutes=2)
        scheduler.start()

        while True:
            await asyncio.sleep(3600)

    loop.run_until_complete(runner())

# Inicia o bot em uma thread separada
t = threading.Thread(target=bot_thread, name="telegram-bot", daemon=True)
t.start()

# ------------------------- ENDPOINT DO WEBHOOK -------------------------
@app.post(WEBHOOK_PATH)
def webhook():
    """Recebe updates e repassa para o Telegram Application."""
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        application.update_queue.put_nowait(update)
        return "ok", 200
    except Exception as e:
        logger.error(f"❌ Erro ao processar webhook: {e}")
        return "error", 500

# ------------------------- MAIN -------------------------
if __name__ == "__main__":
    logger.info("🚀 Bot iniciado e servindo Flask...")
    app.run(host="0.0.0.0", port=PORT)
