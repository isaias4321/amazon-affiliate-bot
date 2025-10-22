import asyncio
import logging
import random
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler

# ===============================
# 🔧 CONFIGURAÇÕES
# ===============================
BOT_TOKEN = "SEU_TOKEN_DO_BOT"
CHAT_ID = -1003140787649
INTERVALO = 120  # 2 minutos

# Shopee links afiliados
SHOPEE_AFF_LINKS = [
    "https://s.shopee.com.br/1gACNJP1z9",
    "https://s.shopee.com.br/8pdMudgZun",
    "https://s.shopee.com.br/20n2m66Bj1"
]

# ID afiliado Mercado Livre
ML_AFF_ID = "im20250701092308"

# Categorias
CATEGORIAS = ["smartphone", "notebook", "ferramentas", "periféricos gamer"]

# ===============================
# LOGS
# ===============================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===============================
# BUSCA SHOPEE
# ===============================
async def buscar_shopee():
    categoria = random.choice(CATEGORIAS)
    async with aiohttp.ClientSession() as session:
        url = f"https://shopee.com.br/api/v4/search/search_items?by=relevancy&limit=20&keyword={categoria}"
        async with session.get(url) as resp:
            data = await resp.json()
            if "items" not in data:
                return None

            produto = random.choice(data["items"])
            nome = produto["item_basic"]["name"]
            preco = produto["item_basic"]["price"] / 100000
            imagem = f"https://down-br.img.susercontent.com/file/{produto['item_basic']['image']}_tn"
            link_afiliado = random.choice(SHOPEE_AFF_LINKS)

            return {
                "titulo": nome,
                "preco": f"R$ {preco:.2f}",
                "imagem": imagem,
                "link": link_afiliado
            }

# ===============================
# BUSCA MERCADO LIVRE
# ===============================
async def buscar_mercadolivre():
    categoria = random.choice(CATEGORIAS)
    async with aiohttp.ClientSession() as session:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={categoria}&limit=20"
        async with session.get(url) as resp:
            data = await resp.json()
            if "results" not in data or not data["results"]:
                return None

            produto = random.choice(data["results"])
            nome = produto["title"]
            preco = produto["price"]
            imagem = produto.get("thumbnail", "")
            link_afiliado = f"{produto['permalink']}?utm_source={ML_AFF_ID}"

            return {
                "titulo": nome,
                "preco": f"R$ {preco:.2f}",
                "imagem": imagem,
                "link": link_afiliado
            }

# ===============================
# POSTAGEM AUTOMÁTICA
# ===============================
ULTIMO_MARKETPLACE = "mercadolivre"

async def postar_oferta(bot: Bot):
    global ULTIMO_MARKETPLACE

    if ULTIMO_MARKETPLACE == "mercadolivre":
        oferta = await buscar_shopee()
        ULTIMO_MARKETPLACE = "shopee"
    else:
        oferta = await buscar_mercadolivre()
        ULTIMO_MARKETPLACE = "mercadolivre"

    if not oferta:
        logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
        return

    texto = (
        f"🔥 <b>{oferta['titulo']}</b>\n"
        f"💰 <b>Preço:</b> {oferta['preco']}\n\n"
        f"🛒 <b>Compre agora:</b>"
    )

    botao = InlineKeyboardMarkup([
        [InlineKeyboardButton("👉 Ver Oferta", url=oferta["link"])]
    ])

    try:
        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=oferta["imagem"],
            caption=texto,
            parse_mode="HTML",
            reply_markup=botao
        )
        logger.info(f"✅ Oferta enviada: {oferta['titulo']}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar oferta: {e}")

# ===============================
# COMANDO /start
# ===============================
async def start(update, context):
    await update.message.reply_text("🤖 Bot de ofertas iniciado!")

# ===============================
# MAIN
# ===============================
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    bot = application.bot

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(postar_oferta, "interval", seconds=INTERVALO, args=[bot])
    scheduler.start()

    application.add_handler(CommandHandler("start", start))

    logger.info("🚀 Bot iniciado com alternância Shopee ↔ Mercado Livre!")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await asyncio.Event().wait()  # mantém rodando

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
