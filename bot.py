import asyncio
import logging
import random
import aiohttp
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.error import Conflict

# ===============================
# 🔧 CONFIGURAÇÕES
# ===============================
BOT_TOKEN = "8463817884:AAE23cMr1605qbMV4c79cMcr8F5dn0ETqRo"
CHAT_ID = -1003140787649
INTERVALO = 120  # segundos entre postagens (2 min)

# Shopee afiliado
SHOPEE_AFF_LINKS = [
    "https://s.shopee.com.br/1gACNJP1z9",
    "https://s.shopee.com.br/8pdMudgZun",
    "https://s.shopee.com.br/20n2m66Bj1"
]

# Mercado Livre afiliado
ML_AFF_ID = "im20250701092308"

# Categorias
CATEGORIAS = ["smartphone", "notebook", "ferramentas", "periféricos gamer", "teclado", "mouse", "monitor"]

# ===============================
# LOGS
# ===============================
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# LIMPEZA DE WEBHOOKS ANTIGOS
# ===============================
print("🧹 Limpando webhooks antigos e atualizações pendentes...")
requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true")

# ===============================
# FUNÇÕES DE BUSCA
# ===============================
async def buscar_shopee():
    categoria = random.choice(CATEGORIAS)
    headers = {"User-Agent": "Mozilla/5.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        url = f"https://shopee.com.br/api/v4/search/search_items?by=relevancy&limit=20&keyword={categoria}"
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if "items" not in data:
                return None
            produto = random.choice(data["items"])
            nome = produto["item_basic"]["name"]
            preco = produto["item_basic"]["price"] / 100000
            imagem = f"https://down-br.img.susercontent.com/file/{produto['item_basic']['image']}_tn"
            link = random.choice(SHOPEE_AFF_LINKS)
            return {"loja": "Shopee", "titulo": nome, "preco": f"R$ {preco:.2f}", "imagem": imagem, "link": link}

async def buscar_mercadolivre():
    categoria = random.choice(CATEGORIAS)
    async with aiohttp.ClientSession() as session:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={categoria}&limit=20"
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if "results" not in data or not data["results"]:
                return None
            produto = random.choice(data["results"])
            nome = produto["title"]
            preco = produto["price"]
            imagem = produto.get("thumbnail", "")
            link = f"{produto['permalink']}?utm_source={ML_AFF_ID}"
            return {"loja": "Mercado Livre", "titulo": nome, "preco": f"R$ {preco:.2f}", "imagem": imagem, "link": link}

# ===============================
# POSTAGEM AUTOMÁTICA
# ===============================
ULTIMO_MARKETPLACE = "mercadolivre"

async def postar_oferta(bot: Bot):
    global ULTIMO_MARKETPLACE
    oferta = await
