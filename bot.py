# bot.py
import os
import random
import logging
import asyncio
import aiohttp
import json
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
# Mercado Livre — busca
# =====================================
async def buscar_ofertas_mercadolivre():
    """Busca produtos do Mercado Livre."""
    termo = random.choice(CATEGORIAS)
    url = "https://api.mercadolibre.com/sites/MLB/search"
    params = {"q": termo, "limit": 3}
    headers = {
        "Authorization": f"Bearer {ML_ACCESS_TOKEN}",
        "User-Agent": "Mozilla/5.0 (compatible; OfertasBot/1.0)",
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers) as resp:
            if resp.status == 401:
                logger.warning(Fore.YELLOW + "[ML]()
