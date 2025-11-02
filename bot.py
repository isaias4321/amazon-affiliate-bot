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
    "ferr
