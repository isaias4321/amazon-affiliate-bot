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

# =====================================
# Inicialização
# =====================================
load_dotenv()
init(autoreset=True)
nest_asyncio.apply()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ofertas-bot")

# =====================================
# Variáveis de ambiente
# =====================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE")
PORT = int(os.getenv("PORT", 8080))

# Mercado Livre
ML_CLIENT_ID = os.getenv("ML_CLIENT_ID")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
ML_ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN")
ML_REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN")
MELI_MATT_TOOL = os.getenv("MELI_MATT_TOOL")
MELI_MATT_WORD = os.getenv("MELI_MATT_WORD")

# Shopee
SHOPEE_PARTNER_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_PARTNER_KEY = os.getenv("SHOPEE_APP_SECRET")

# Categorias desejadas
CATEGORIAS = [
    "eletrodomésticos",
    "peças de computador",
    "notebooks",
    "celulares",
    "ferramentas",
]

# Controle de cache e alternância
ULTIMOS_TITULOS = set()
MAX_CACHE_TITULOS = 100
STATE = {"proximo": "mercadolivre"}

# =====================================
# Utilitários
# =====================================
def brl(valor):
    try:
        n = float(valor)
        inteiro, centavos = f"{n:.2f}".split(".")
        inteiro = f"{int(inteiro):,}".replace(",", ".")
        return f"R$ {inteiro},{centavos}"
    except Exception:
        return str(valor)

def clear_cache():
    if len(ULTIMOS_TITULOS) > MAX_CACHE_TITULOS:
        ULTIMOS_TITULOS.clear()

def build_keyboard(url: str):
    return InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta 🔗", url=url)]])

# =====================================
# Mercado Livre — busca pública
# =====================================
async def buscar_ofertas_mercadolivre():
    """Busca produtos do Mercado Livre (API pública, sem token)."""
    termo = random.choice(CATEGORIAS)
    url = "https://api.mercadolibre.com/sites/MLB/search"
    params = {"q": termo, "limit": 3}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status != 200:
                logger.error(Fore.RED + f"[ML] HTTP {resp.status}")
                return []

            data = await resp.json()
            results = data.get("results", [])
            ofertas = []
            for r in results:
                titulo = r["title"]
                if titulo in ULTIMOS_TITULOS:
                    continue
                link = (
                    f"{r['permalink']}?matt_tool={MELI_MATT_TOOL}&matt_word={MELI_MATT_WORD}"
                )
                ofertas.append({
                    "titulo": titulo,
                    "preco": r["price"],
                    "link": link
                })
            return ofertas

# =====================================
# Shopee — busca com assinatura HMAC
# =====================================
async def buscar_ofertas_shopee():
    """Busca produtos da Shopee (API BR com assinatura HMAC)."""
    termo = random.choice(CATEGORIAS)
    timestamp = int(datetime.now(timezone.utc).timestamp())
    partner_id = str(SHOPEE_PARTNER_ID)
    partner_key = SHOPEE_PARTNER_KEY
    api_path = "/api/v1/offer/product_offer"

    # Cria assinatura (HMAC-SHA256)
    base_string = f"{partner_id}{api_path}{timestamp}"
    sign = hmac.new(
        partner_key.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    url = f"https://open-api.affiliate.shopee.com.br{api_path}"
    headers = {
        "Content-Type": "application/json",
        "X-Appid": partner_id,
        "X-Timestamp": str(timestamp),
        "X-Sign": sign,
    }

    payload = {"page_size": 3, "page": 1, "keyword": termo}

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
                ofertas.append({
                    "titulo": titulo,
                    "preco": item.get("price"),
                    "link": item.get("short_url") or item.get("offer_link"),
                })
            return ofertas

# =====================================
# Postagens automáticas
# =====================================
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

    clear_cache()

# =====================================
# Comando /start
# =====================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "🤖 <b>Bot de Ofertas Ativo!</b>\n"
        "Postagens automáticas a cada 1 minuto, alternando entre:\n"
        "🟡 Mercado Livre e 🟠 Shopee\n\n"
        "Categorias: eletrodomésticos, peças de computador, notebooks, celulares, ferramentas."
    )

# =====================================
# Inicialização (Webhook Railway)
# =====================================
async def main():
    if not TOKEN or not CHAT_ID or not WEBHOOK_BASE:
        raise RuntimeError("⚠️ TELEGRAM_TOKEN, CHAT_ID ou WEBHOOK_BASE não configurados!")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Agendador (1 min)
    scheduler = AsyncIOScheduler()
    loop = asyncio.get_running_loop()

    async def job():
        await postar_ofertas(app)

    def schedule_job():
        asyncio.run_coroutine_threadsafe(job(), loop)

    scheduler.add_job(schedule_job, "interval", minutes=1)
    scheduler.start()
    logger.info(Fore.GREEN + "🗓️ Agendador iniciado (1 min).")

    # Configuração do Webhook
    webhook_url = f"{WEBHOOK_BASE}/{TOKEN}"
    await app.bot.set_webhook(webhook_url)
    logger.info(Fore.CYAN + f"🌐 Webhook configurado: {webhook_url}")

    # Executa servidor webhook
    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(Style.DIM + "Bot encerrado.")
