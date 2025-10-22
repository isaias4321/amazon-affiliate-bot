import asyncio
import logging
import random
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler

# ===============================
# 🔧 CONFIGURAÇÕES PRINCIPAIS
# ===============================
BOT_TOKEN = "SEU_TOKEN_DO_BOT"
CHAT_ID = -1003140787649  # substitua pelo ID do seu grupo
INTERVALO = 120  # 2 minutos

# Links afiliados Shopee
SHOPEE_AFF_LINKS = [
    "https://s.shopee.com.br/1gACNJP1z9",
    "https://s.shopee.com.br/8pdMudgZun",
    "https://s.shopee.com.br/20n2m66Bj1",
]

# ID de afiliado Mercado Livre
ML_AFF_ID = "im20250701092308"

# Categorias de busca
CATEGORIAS = ["smartphone", "notebook", "ferramentas", "periféricos gamer"]

# ===============================
# 🧠 CONFIGURAÇÃO DE LOGS
# ===============================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===============================
# 🔍 FUNÇÕES DE BUSCA
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
            link_base = produto["permalink"]
            link_afiliado = f"{link_base}?utm_source={ML_AFF_ID}"

            return {
                "titulo": nome,
                "preco": f"R$ {preco:.2f}",
                "imagem": imagem,
                "link": link_afiliado
            }

# ===============================
# 📦 POSTAGENS AUTOMÁTICAS
# ===============================
ULTIMO_MARKETPLACE = "mercadolivre"  # inicia alternando

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
        f"🛍️ <b>{oferta['titulo']}</b>\n"
        f"💰 <b>Preço:</b> {oferta['preco']}\n\n"
        f"👇 <b>Compre agora com desconto:</b>"
    )

    botao = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Compre agora", url=oferta["link"])]
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
# 🚀 INÍCIO DO BOT
# ===============================
async def start(update, context):
    await update.message.reply_text("🤖 Bot de ofertas iniciado com sucesso!")

async def main():
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    bot = application.bot
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(postar_oferta, "interval", seconds=INTERVALO, args=[bot])
    scheduler.start()

    application.add_handler(CommandHandler("start", start))

    logger.info("🚀 Bot iniciado com alternância automática Shopee ↔ Mercado Livre!")
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
