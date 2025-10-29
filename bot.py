import os, logging, asyncio, time, hmac, hashlib, json
from datetime import datetime
from typing import List, Dict
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import httpx

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- VARIÁVEIS ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "").rstrip("/")
PORT = int(os.getenv("PORT", 8080))

# Mercado Livre
ML_APP_ID = os.getenv("ML_APP_ID")
ML_SECRET = os.getenv("ML_SECRET")
ML_USER_ID = os.getenv("ML_USER_ID")
ML_NICK = os.getenv("ML_NICK", "oficial")
ML_CATEGORIAS = ["MLB1648", "MLB263532", "MLB1132", "MLB1809"]  # Eletrônicos, PC, Eletrodomésticos, Ferramentas

# Shopee (opcional)
SHOPEE_PARTNER_ID = os.getenv("SHOPEE_PARTNER_ID")
SHOPEE_PARTNER_KEY = os.getenv("SHOPEE_PARTNER_KEY")
SHOPEE_SHOP_ID = os.getenv("SHOPEE_SHOP_ID")

POST_INTERVAL = int(os.getenv("POST_INTERVAL_SECONDS", "120"))

if not TOKEN:
    raise RuntimeError("❌ Configure TELEGRAM_BOT_TOKEN no .env")

# --- APP TELEGRAM ---
app_tg = ApplicationBuilder().token(TOKEN).build()
POSTING_ON = set()

async def cmd_start(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot de Ofertas!\n"
        "/start_posting – começar a postar\n"
        "/stop_posting – parar\n"
        "/status – ver status"
    )

async def cmd_start_posting(update: Update, _: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    POSTING_ON.add(cid)
    await update.message.reply_text("🚀 Postagem automática iniciada aqui!")

async def cmd_stop_posting(update: Update, _: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    POSTING_ON.discard(cid)
    await update.message.reply_text("🧯 Postagem pausada neste chat.")

async def cmd_status(update: Update, _: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    s = "ON" if cid in POSTING_ON else "OFF"
    await update.message.reply_text(f"📊 Status: {s}")

app_tg.add_handler(CommandHandler("start", cmd_start))
app_tg.add_handler(CommandHandler("start_posting", cmd_start_posting))
app_tg.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
app_tg.add_handler(CommandHandler("status", cmd_status))

# --- FUNÇÕES DE OFERTAS ---
async def buscar_ofertas_ml() -> List[Dict]:
    """Busca ofertas no Mercado Livre."""
    resultados = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for cat in ML_CATEGORIAS:
                url = f"https://api.mercadolibre.com/sites/MLB/search?category={cat}&limit=3"
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                for it in r.json().get("results", []):
                    link = it["permalink"] + f"?utm_source={ML_NICK}"
                    resultados.append({
                        "fonte": "MERCADO LIVRE",
                        "titulo": it["title"],
                        "preco": f"R$ {it['price']:.2f}",
                        "link": link
                    })
        return resultados
    except Exception as e:
        logger.error(f"Erro ML: {e}")
        return []

async def buscar_ofertas_shopee() -> List[Dict]:
    """Retorna ofertas da Shopee (se configurada)."""
    if not (SHOPEE_PARTNER_ID and SHOPEE_PARTNER_KEY and SHOPEE_SHOP_ID):
        return []
    try:
        ts = int(time.time())
        path = "/api/v2/product/get_item_list"
        base = f"{SHOPEE_PARTNER_ID}{path}{ts}{SHOPEE_SHOP_ID}".encode()
        sign = hmac.new(SHOPEE_PARTNER_KEY.encode(), base, hashlib.sha256).hexdigest()
        url = f"https://partner.shopeemobile.com{path}?partner_id={SHOPEE_PARTNER_ID}&timestamp={ts}&sign={sign}&shop_id={SHOPEE_SHOP_ID}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json={"page_size": 2, "page_no": 1})
            if r.status_code != 200:
                return []
            data = r.json()
            out = []
            for item in (data.get("response") or {}).get("item_list", []):
                out.append({
                    "fonte": "SHOPEE",
                    "titulo": item.get("item_name", "Produto Shopee"),
                    "preco": "—",
                    "link": f"https://shopee.com.br/product/{SHOPEE_SHOP_ID}/{item['item_id']}"
                })
            return out
    except Exception as e:
        logger.error(f"Erro Shopee: {e}")
        return []

async def postar_ofertas():
    """Publica ofertas no Telegram."""
    try:
        ofertas = await buscar_ofertas_ml()
        ofertas += await buscar_ofertas_shopee()
        if not ofertas:
            logger.info("🙈 Nenhuma oferta encontrada.")
            return

        destinos = list(POSTING_ON)
        if CHAT_ID and CHAT_ID not in destinos:
            destinos.append(int(CHAT_ID))

        for cid in destinos:
            for of in ofertas[:4]:
                msg = (
                    f"🛍️ <b>{of['fonte']}</b>\n"
                    f"{of['titulo']}\n"
                    f"💰 {of['preco']}\n"
                    f"🔗 <a href='{of['link']}'>Compre aqui</a>"
                )
                try:
                    await app_tg.bot.send_message(cid, msg, parse_mode="HTML", disable_web_page_preview=False)
                except Exception as e:
                    logger.warning(f"Falha ao enviar: {e}")
        logger.info(f"✅ {len(ofertas)} ofertas postadas.")
    except Exception as e:
        logger.exception(e)

# --- SCHEDULER ---
scheduler = AsyncIOScheduler()

# --- FLASK / WEBHOOK ---
flask_app = Flask(__name__)

@flask_app.get("/")
def ok():
    return "OK", 200

@flask_app.post(f"/webhook/{TOKEN}")
async def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, app_tg.bot)

        # 🔧 Corrige erro “Application not initialized”
        if not app_tg._initialized:
            logger.info("⚙️ Inicializando Application (lazy)...")
            await app_tg.initialize()
        if not app_tg.running:
            await app_tg.start()

        await app_tg.process_update(update)
        return jsonify({"ok": True}), 200
    except Exception as e:
        logger.exception("❌ Erro ao processar update")
        return jsonify({"ok": False, "error": str(e)}), 500

async def setup_webhook():
    await app_tg.bot.delete_webhook(drop_pending_updates=True)
    await app_tg.bot.set_webhook(url=f"{WEBHOOK_BASE}/webhook/{TOKEN}")
    logger.info("✅ Webhook configurado.")

async def main():
    await app_tg.initialize()
    await app_tg.start()
    await setup_webhook()
    scheduler.add_job(postar_ofertas, "interval", seconds=POST_INTERVAL, id="postar")
    scheduler.start()
    while True:
        await asyncio.sleep(3600)

def start_bg():
    asyncio.get_event_loop().create_task(main())

if __name__ == "__main__":
    start_bg()
    flask_app.run(host="0.0.0.0", port=PORT)
