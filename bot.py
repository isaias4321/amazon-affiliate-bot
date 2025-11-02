# bot.py
import os
import random
import logging
import asyncio
import aiohttp
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
SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_APP_SECRET = os.getenv("SHOPEE_APP_SECRET")

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
# Mercado Livre — renovação automática
# =====================================
async def renovar_token_mercadolivre():
    """Renova o token do Mercado Livre automaticamente e salva no .env."""
    global ML_ACCESS_TOKEN, ML_REFRESH_TOKEN
    url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": ML_CLIENT_ID,
        "client_secret": ML_CLIENT_SECRET,
        "refresh_token": ML_REFRESH_TOKEN,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            if resp.status != 200:
                logger.error(Fore.RED + f"Erro ao renovar token ML: {data}")
                return

            ML_ACCESS_TOKEN = data.get("access_token")
            ML_REFRESH_TOKEN = data.get("refresh_token")

            os.environ["ML_ACCESS_TOKEN"] = ML_ACCESS_TOKEN
            os.environ["ML_REFRESH_TOKEN"] = ML_REFRESH_TOKEN

            # Atualiza o .env local
            try:
                with open(".env", "r", encoding="utf-8") as f:
                    env_lines = f.readlines()
            except FileNotFoundError:
                env_lines = []

            new_lines = []
            keys_to_update = {
                "ML_ACCESS_TOKEN": ML_ACCESS_TOKEN,
                "ML_REFRESH_TOKEN": ML_REFRESH_TOKEN,
            }
            for line in env_lines:
                key = line.split("=")[0].strip()
                if key in keys_to_update:
                    new_lines.append(f"{key}={keys_to_update[key]}\n")
                    keys_to_update.pop(key)
                else:
                    new_lines.append(line)

            for k, v in keys_to_update.items():
                new_lines.append(f"{k}={v}\n")

            with open(".env", "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            logger.info(Fore.GREEN + "🔑 Token Mercado Livre renovado e salvo no .env!")

# =====================================
# Mercado Livre — busca (sem token)
# =====================================
async def buscar_ofertas_mercadolivre():
    """Busca produtos do Mercado Livre (API pública, sem token)."""
    termo = random.choice(CATEGORIAS)
    url = "https://api.mercadolibre.com/sites/MLB/search"
    params = {"q": termo, "limit": 3}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OfertasBot/1.0)"}

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
# Shopee — busca
# =====================================
async def buscar_ofertas_shopee():
    """Busca produtos da Shopee via API de afiliados."""
    termo = random.choice(CATEGORIAS)
    ts = int(datetime.now(timezone.utc).timestamp())
    url = "https://open-api.affiliate.shopee.com.br/api/v1/offer/product_offer"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SHOPEE_APP_SECRET}",
        "X-Appid": str(SHOPEE_APP_ID),
    }
    payload = {"page_size": 3, "page": 1, "keyword": termo, "timestamp": ts}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
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

# =====================================
# Postagens
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
