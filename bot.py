import os
import random
import logging
import asyncio
import aiohttp
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from colorama import Fore, Style, init
import nest_asyncio

# Inicializa cores e corrige loops assíncronos
init(autoreset=True)
nest_asyncio.apply()

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

# Shopee
SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_APP_SECRET = os.getenv("SHOPEE_APP_SECRET")

# Categorias desejadas
CATEGORIAS = [
    "eletrônicos",
    "peças de computador",
    "eletrodomésticos",
    "ferramentas",
]

ULTIMOS_PRODUTOS = set()

# =====================================
# ⚙️ FUNÇÕES AUXILIARES
# =====================================
async def buscar_ofertas_mercadolivre():
    """Busca produtos do Mercado Livre."""
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
    """Busca ofertas da Shopee via API oficial."""
    if not SHOPEE_APP_ID or not SHOPEE_APP_SECRET:
        logger.error(Fore.RED + "❌ Credenciais Shopee não configuradas!")
        return []

    termo = random.choice(CATEGORIAS)
    ts = int(datetime.now(timezone.utc).timestamp())
    url = "https://open-api.affiliate.shopee.com.br/api/v1/offer/product_offer"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SHOPEE_APP_SECRET}",
        "X-Appid": str(SHOPEE_APP_ID),
    }

    payload = {
        "page_size": 3,
        "page": 1,
        "keyword": termo,
        "timestamp": ts,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
                items = data.get("data", {}).get("list", [])
                ofertas = []
                for item in items:
                    titulo = item.get("name")
                    if not titulo or titulo in ULTIMOS_PRODUTOS:
                        continue
                    ULTIMOS_PRODUTOS.add(titulo)
                    ofertas.append({
                        "titulo": titulo,
                        "preco": item.get("price"),
                        "link": item.get("short_url") or item.get("offer_link")
                    })
                return ofertas
    except Exception as e:
        logger.error(Fore.RED + f"Erro ao buscar ofertas Shopee: {e}")
        return []


async def postar_ofertas(app):
    """Publica ofertas no grupo do Telegram."""
    logger.info(Fore.BLUE + "🛍️ Verificando novas ofertas...")

    ofertas_meli = await buscar_ofertas_mercadolivre()
    ofertas_shopee = await buscar_ofertas_shopee()

    ofertas = (ofertas_meli or []) + (ofertas_shopee or [])
    if not ofertas:
        logger.info(Fore.YELLOW + "⚠️ Nenhuma oferta encontrada no momento.")
        return

    for o in ofertas:
        msg = f"📦 *{o['titulo']}*\n💰 R$ {o['preco']}\n🔗 {o['link']}"
        try:
            await app.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(Fore.RED + f"Erro ao enviar mensagem: {e}")

    logger.info(Fore.GREEN + "✅ Ofertas enviadas com sucesso!")


# =====================================
# 🤖 COMANDOS DO BOT
# =====================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot de Ofertas ativo e pronto para encontrar promoções!")


async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o agendamento de postagens automáticas."""
    scheduler = AsyncIOScheduler()
    loop = asyncio.get_running_loop()

    def job():
        asyncio.run_coroutine_threadsafe(
            postar_ofertas(context.application),
            loop
        )

    scheduler.add_job(job, "interval", minutes=2)
    scheduler.start()
    await update.message.reply_text("🚀 Postagem automática iniciada!")


# =====================================
# 🏁 INICIALIZAÇÃO DO BOT
# =====================================
logger.info(Fore.CYAN + "🚀 Iniciando bot de ofertas...")

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("start_posting", cmd_start_posting))


async def main():
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info(Fore.GREEN + "✅ Bot conectado e em execução.")
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
