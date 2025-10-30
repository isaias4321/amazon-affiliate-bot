import os
import random
import logging
import asyncio
import aiohttp
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# =====================================
# 🔧 CONFIGURAÇÃO INICIAL
# =====================================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Mercado Livre
MELI_MATT_TOOL = os.getenv("MELI_MATT_TOOL")
MELI_MATT_WORD = os.getenv("MELI_MATT_WORD")

# Shopee API
SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_APP_SECRET = os.getenv("SHOPEE_APP_SECRET")

# Categorias principais
CATEGORIAS = [
    "eletrônicos",
    "peças de computador",
    "eletrodomésticos",
    "ferramentas"
]

# Evitar produtos repetidos
ULTIMOS_PRODUTOS = set()

# =====================================
# ⚙️ Funções auxiliares
# =====================================
async def buscar_ofertas_mercadolivre():
    """Busca ofertas reais do Mercado Livre via API pública."""
    url = "https://api.mercadolibre.com/sites/MLB/search"
    params = {"q": random.choice(CATEGORIAS), "limit": 3}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            results = data.get("results", [])
            ofertas = []
            for r in results:
                link_af = (
                    f"{r['permalink']}?matt_tool={MELI_MATT_TOOL}&matt_word={MELI_MATT_WORD}"
                )
                ofertas.append({
                    "titulo": r["title"],
                    "preco": r["price"],
                    "link": link_af
                })
            return ofertas


async def buscar_ofertas_shopee():
    """Busca produtos da Shopee via API oficial."""
    termo = random.choice(CATEGORIAS)
    ts = int(datetime.utcnow().timestamp())
    url = "https://open-api.affiliate.shopee.com.br/api/v1/product_offer_list"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SHOPEE_APP_SECRET}",
        "X-Appid": SHOPEE_APP_ID
    }

    payload = {
        "page_size": 3,
        "page": 1,
        "keyword": termo or "",
        "timestamp": ts
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
                items = data.get("data", {}).get("list", [])
                ofertas = []
                for item in items:
                    titulo = item.get("name")
                    if titulo in ULTIMOS_PRODUTOS:
                        continue  # evita repetição
                    ULTIMOS_PRODUTOS.add(titulo)

                    ofertas.append({
                        "titulo": titulo,
                        "preco": item.get("price"),
                        "link": item.get("short_url") or item.get("offer_link")
                    })
                return ofertas
    except Exception as e:
        logger.error(f"Erro ao buscar ofertas Shopee: {e}")
        return []


async def postar_ofertas():
    """Envia as ofertas encontradas para o grupo."""
    logger.info("🛍️ Verificando novas ofertas...")

    ofertas_meli = await buscar_ofertas_mercadolivre()
    ofertas_shopee = await buscar_ofertas_shopee()

    ofertas = (ofertas_meli or []) + (ofertas_shopee or [])
    if not ofertas:
        logger.info("Nenhuma oferta encontrada no momento.")
        return

    app = Application.builder().token(TOKEN).build()

    for o in ofertas:
        msg = f"📦 *{o['titulo']}*\n💰 R$ {o['preco']}\n🔗 {o['link']}"
        try:
            await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")

    logger.info("✅ Ofertas enviadas com sucesso!")


# =====================================
# 🤖 Comandos do bot
# =====================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot de Ofertas ativo e pronto!")


async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.run(postar_ofertas()), "interval", minutes=2)
    scheduler.start()
    await update.message.reply_text("🚀 Postagem automática iniciada com sucesso!")


# =====================================
# 🏁 Inicialização do Bot
# =====================================
if __name__ == "__main__":
    logger.info("Bot iniciado 🚀")

    app_tg = Application.builder().token(TOKEN).build()
    app_tg.add_handler(CommandHandler("start", start))
    app_tg.add_handler(CommandHandler("start_posting", cmd_start_posting))

    app_tg.run_polling()
