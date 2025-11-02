# bot.py
import os
import random
import logging
import asyncio
import aiohttp
import hmac
import hashlib
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from colorama import Fore, Style, init
from dotenv import load_dotenv
import nest_asyncio

# ===========================
# Inicialização
# ===========================
load_dotenv()
init(autoreset=True)
nest_asyncio.apply()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ofertas-bot")

# ===========================
# Configurações
# ===========================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE")
PORT = int(os.getenv("PORT", 8080))

# Shopee
SHOPEE_PARTNER_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_PARTNER_KEY = os.getenv("SHOPEE_APP_SECRET")

# Mercado Livre afiliados
MELI_MATT_TOOL = os.getenv("MELI_MATT_TOOL")
MELI_MATT_WORD = os.getenv("MELI_MATT_WORD")

CATEGORIAS = [
    "eletrodomésticos",
    "peças de computador",
    "notebooks",
    "celulares",
    "ferramentas",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/122.0",
]

ULTIMOS_TITULOS = set()
STATE = {"proximo": "mercadolivre"}

# ===========================
# Utilitários
# ===========================
def brl(valor):
    try:
        n = float(valor)
        inteiro, centavos = f"{n:.2f}".split(".")
        inteiro = f"{int(inteiro):,}".replace(",", ".")
        return f"R$ {inteiro},{centavos}"
    except Exception:
        return str(valor)

def build_keyboard(url: str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta 🔗", url=url)]])

# ===========================
# Mercado Livre via Proxy (sem bloqueio)
# ===========================
async def buscar_ofertas_mercadolivre():
    termo = random.choice(CATEGORIAS)
    url = f"https://api.allorigins.win/get?url=https://api.mercadolibre.com/sites/MLB/search?q={termo}&limit=3"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    logger.error(Fore.RED + f"[ML] HTTP {resp.status}")
                    return []
                raw = await resp.json()
                data = raw.get("contents")
                if not data:
                    return []
                import json as _json
                data = _json.loads(data)
                results = data.get("results", [])
                ofertas = []
                for r in results:
                    titulo = r["title"]
                    if titulo in ULTIMOS_TITULOS:
                        continue
                    link = f"{r['permalink']}?matt_tool={MELI_MATT_TOOL}&matt_word={MELI_MATT_WORD}"
                    ofertas.append({"titulo": titulo, "preco": r["price"], "link": link})
                return ofertas
    except Exception as e:
        logger.error(Fore.RED + f"Erro Mercado Livre: {e}")
        return []

# ===========================
# Shopee (assinatura HMAC)
# ===========================
async def buscar_ofertas_shopee():
    termo = random.choice(CATEGORIAS)
    timestamp = int(datetime.now(timezone.utc).timestamp())
    partner_id = str(SHOPEE_PARTNER_ID)
    partner_key = SHOPEE_PARTNER_KEY
    api_path = "/api/v1/offer/product_offer"

    base_string = f"{partner_id}{api_path}{timestamp}"
    sign = hmac.new(
        partner_key.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    url = f"https://open-api.affiliate.shopee.com.br{api_path}"
    headers = {
        "Content-Type": "application/json",
        "X-Appid": partner_id,
        "X-Timestamp": str(timestamp),
        "X-Sign": sign,
    }

    payload = {"page_size": 3, "page": 1, "keyword": termo}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    logger.error(Fore.RED + f"[Shopee] HTTP {resp.status}")
                    return []
                data = await resp.json()
                items = data.get("data", {}).get("list", [])
                ofertas = []
                for item in items:
                    titulo = item.get("name")
                    if not titulo or titulo in ULTIMOS_TITULOS:
                        continue
                    ofertas.append(
                        {
                            "titulo": titulo,
                            "preco": item.get("price"),
                            "link": item.get("short_url") or item.get("offer_link"),
                        }
                    )
                return ofertas
    except Exception as e:
        logger.error(Fore.RED + f"Erro Shopee: {e}")
        return []

# ===========================
# Postagens
# ===========================
async def postar_ofertas(app):
    origem = STATE["proximo"]
    logger.info(Fore.CYAN + f"🔁 Rodada: {origem.upper()}")

    if origem == "mercadolivre":
        ofertas = await buscar_ofertas_mercadolivre()
        STATE["proximo"] = "shopee"
    else:
        ofertas = await buscar_ofertas_shopee()
        STATE["proximo"] = "mercadolivre"

    if not ofertas:
        logger.info(Fore.YELLOW + "⚠️ Nenhuma oferta encontrada.")
        return

    for o in ofertas:
        titulo = o["titulo"]
        if titulo in ULTIMOS_TITULOS:
            continue
        msg = f"📦 <b>{titulo}</b>\n💰 <b>{brl(o['preco'])}</b>"
        try:
            await app.bot.send_message(
                chat_id=CHAT_ID,
                text=msg,
                parse_mode="HTML",
                reply_markup=build_keyboard(o["link"]),
            )
            ULTIMOS_TITULOS.add(titulo)
            logger.info(Fore.GREEN + f"✅ Enviado: {titulo}")
        except Exception as e:
            logger.error(Fore.RED + f"Erro ao enviar mensagem: {e}")

# ===========================
# Comando /start
# ===========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "🤖 <b>Bot de Ofertas Ativo!</b>\n"
        "Postagens automáticas a cada 1 minuto alternando entre:\n"
        "🟡 Mercado Livre e 🟠 Shopee\n\n"
        "Categorias: eletrodomésticos, peças de computador, notebooks, celulares, ferramentas."
    )

# ===========================
# Inicialização Railway
# ===========================
async def main():
    if not TOKEN or not CHAT_ID or not WEBHOOK_BASE:
        raise RuntimeError("⚠️ TELEGRAM_TOKEN, CHAT_ID ou WEBHOOK_BASE não configurados!")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    scheduler = AsyncIOScheduler()
    loop = asyncio.get_running_loop()

    async def job():
        await postar_ofertas(app)

    def schedule_job():
        asyncio.run_coroutine_threadsafe(job(), loop)

    # 1 minuto
    scheduler.add_job(schedule_job, "interval", minutes=1)
    scheduler.start()
    logger.info(Fore.GREEN + "🗓️ Agendador iniciado (1 min).")

    webhook_url = f"{WEBHOOK_BASE}/{TOKEN}"
    await app.bot.set_webhook(webhook_url)
    logger.info(Fore.CYAN + f"🌐 Webhook configurado: {webhook_url}")

    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=webhook_url,
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(Style.DIM + "Bot encerrado.")
