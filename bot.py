import asyncio
import logging
import random
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ===============================
# 🔧 CONFIGURAÇÕES
# ===============================
BOT_TOKEN = "8463817884:AAE23cMr1605qbMV4c79cMcr8F5dn0ETqRo"
CHAT_ID = -1003140787649
INTERVALO = 120  # tempo entre ofertas (2 minutos)

# Shopee afiliado
SHOPEE_AFF_LINKS = [
    "https://s.shopee.com.br/1gACNJP1z9",
    "https://s.shopee.com.br/8pdMudgZun",
    "https://s.shopee.com.br/20n2m66Bj1"
]

# Mercado Livre afiliado
ML_AFF_ID = "im20250701092308"

# Categorias aleatórias
CATEGORIAS = ["smartphone", "notebook", "ferramentas", "periféricos gamer", "teclado", "mouse", "monitor"]

# ===============================
# LOGS FORMATADOS
# ===============================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===============================
# FUNÇÕES DE BUSCA
# ===============================
async def buscar_shopee():
    categoria = random.choice(CATEGORIAS)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
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
            link_afiliado = random.choice(SHOPEE_AFF_LINKS)

            logger.info(f"🟠 [SHOPEE] Produto capturado: {nome[:60]}...")
            return {
                "loja": "Shopee",
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
            if resp.status != 200:
                return None
            data = await resp.json()
            if "results" not in data or not data["results"]:
                return None

            produto = random.choice(data["results"])
            nome = produto["title"]
            preco = produto["price"]
            imagem = produto.get("thumbnail", "")
            link_afiliado = f"{produto['permalink']}?utm_source={ML_AFF_ID}"

            logger.info(f"🟡 [MERCADO LIVRE] Produto capturado: {nome[:60]}...")
            return {
                "loja": "Mercado Livre",
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

    prefixo = "🔶 Oferta Shopee do momento!" if oferta["loja"] == "Shopee" else "🔷 Promoção Mercado Livre agora!"

    texto = (
        f"{prefixo}\n\n"
        f"🔥 <b>{oferta['titulo']}</b>\n"
        f"💰 <b>Preço:</b> {oferta['preco']}\n\n"
        f"🏬 <b>Loja:</b> {oferta['loja']}\n"
        f"🛒 <b>Compre agora:</b>"
    )

    botao = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Ver oferta", url=oferta["link"])]
    ])

    try:
        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=oferta["imagem"],
            caption=texto,
            parse_mode="HTML",
            reply_markup=botao
        )
        logger.info(f"✅ Oferta enviada ({oferta['loja']}): {oferta['titulo'][:70]}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar oferta: {e}")

# ===============================
# COMANDOS
# ===============================
async def start(update, context):
    await update.message.reply_text("🤖 Bot de ofertas iniciado! Use /start_posting para começar as postagens automáticas.")

async def start_posting(update, context):
    bot = context.bot
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(postar_oferta, "interval", seconds=INTERVALO, args=[bot])
    scheduler.start()
    await update.message.reply_text("🚀 Postagens automáticas iniciadas com sucesso!")
    logger.info("🕒 Postagens automáticas iniciadas via comando /start_posting.")

# ===============================
# INÍCIO DO BOT
# ===============================
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))

    logger.info("🚀 Bot carregado — aguardando comandos ou agendamento automático...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
