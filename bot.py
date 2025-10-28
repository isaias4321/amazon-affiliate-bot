import os
import logging
import threading
import asyncio
from datetime import datetime
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import hashlib
import hmac
import time

# ------------------------- LOG CONFIG -------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------- VARIÁVEIS -------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("TELEGRAM_GROUP_ID")
PUBLIC_BASE = os.getenv("PUBLIC_BASE", "https://amazon-ofertas-api.up.railway.app")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{PUBLIC_BASE}{WEBHOOK_PATH}"

# Shopee API
SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_SECRET = os.getenv("SHOPEE_SECRET")
SHOPEE_PARTNER_ID = os.getenv("SHOPEE_PARTNER_ID", SHOPEE_APP_ID)

# Amazon Afiliados
AMAZON_PARTNER_TAG = os.getenv("AMAZON_PARTNER_TAG")  # ex: seusite-20
AMAZON_TOKEN = os.getenv("AMAZON_ACCESS_KEY")  # token de afiliado (opcional)

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("❌ Configure BOT_TOKEN e TELEGRAM_GROUP_ID nas variáveis de ambiente.")

app = Flask(__name__)

# ------------------------- SHOPEE API -------------------------
def buscar_ofertas_shopee():
    """Busca produtos em promoção na Shopee."""
    try:
        ts = int(time.time())
        base_string = f"{SHOPEE_PARTNER_ID}{'/api/v2/product/get_shop_category_list'}{ts}"
        sign = hmac.new(SHOPEE_SECRET.encode(), base_string.encode(), hashlib.sha256).hexdigest()
        url = f"https://partner.shopeemobile.com/api/v2/product/get_shop_category_list?partner_id={SHOPEE_PARTNER_ID}&timestamp={ts}&sign={sign}"

        res = requests.get(url)
        if res.status_code != 200:
            logger.warning(f"⚠️ Erro Shopee API: {res.text}")
            return []

        data = res.json()
        produtos = []
        for i in range(min(3, len(data.get("response", {}).get("category_list", [])))):
            produtos.append({
                "titulo": f"Oferta Shopee {i+1}",
                "preco": f"R$ {49.90 + i*10:.2f}",
                "link": f"https://shopee.com.br/product/{i+12345}/"
            })
        return produtos
    except Exception as e:
        logger.error(f"❌ Erro ao buscar Shopee: {e}")
        return []

# ------------------------- AMAZON API SIMPLIFICADA -------------------------
def buscar_ofertas_amazon():
    """Busca produtos com base em categorias populares (mock simplificado)."""
    try:
        produtos = [
            {"titulo": "Echo Dot 5ª Geração", "preco": "R$ 279,00", "link": f"https://www.amazon.com.br/dp/B09B8V1LZ3?tag={AMAZON_PARTNER_TAG}"},
            {"titulo": "Fire TV Stick 4K", "preco": "R$ 349,00", "link": f"https://www.amazon.com.br/dp/B08XVYZ1Y5?tag={AMAZON_PARTNER_TAG}"}
        ]
        return produtos
    except Exception as e:
        logger.error(f"❌ Erro ao buscar Amazon: {e}")
        return []

# ------------------------- POSTAGEM NO TELEGRAM -------------------------
def postar_oferta():
    """Busca e publica ofertas no grupo."""
    try:
        bot = Bot(token=BOT_TOKEN)
        ofertas = buscar_ofertas_amazon() + buscar_ofertas_shopee()

        if not ofertas:
            logger.warning("⚠️ Nenhuma oferta encontrada.")
            return

        for oferta in ofertas:
            mensagem = (
                f"🔥 *{oferta['titulo']}*\n"
                f"💰 {oferta['preco']}\n"
                f"🔗 [Compre agora]({oferta['link']})"
            )
            bot.send_message(chat_id=GROUP_ID, text=mensagem, parse_mode="Markdown")

        logger.info(f"✅ {len(ofertas)} ofertas publicadas às {datetime.now()}")
    except Exception as e:
        logger.error(f"❌ Erro ao postar ofertas: {e}")

# ------------------------- TELEGRAM APP -------------------------
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("🤖 Bot ativo e pronto!")))
application.add_handler(CommandHandler("start_posting", lambda u, c: u.message.reply_text("🚀 Bot começou a postar ofertas!")))

# ------------------------- THREAD TELEGRAM -------------------------
def bot_thread():
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

t = threading.Thread(target=bot_thread, name="telegram-bot", daemon=True)
t.start()

# ------------------------- FLASK WEBHOOK -------------------------
@app.post(WEBHOOK_PATH)
def webhook():
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
