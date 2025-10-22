import asyncio
import logging
import random
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import Conflict

# ===============================
# 🔧 CONFIGURAÇÕES
# ===============================
BOT_TOKEN = "8463817884:AAE23cMr1605qbMV4c79cMcr8F5dn0ETqRo"
CHAT_ID = -1003140787649
INTERVALO = 120  # tempo entre ofertas em segundos (2 min)

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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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

    oferta = await (buscar_shopee() if ULTIMO_MARKETPLACE == "mercadolivre" else buscar_mercadolivre())
    ULTIMO_MARKETPLACE = "shopee" if ULTIMO_MARKETPLACE == "mercadolivre" else "mercadolivre"

    if not oferta:
        logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
        return

    texto = (
        f"🛒 <b>{oferta['loja']}</b> está com oferta!\n\n"
        f"🔥 <b>{oferta['titulo']}</b>\n"
        f"💰 <b>Preço:</b> {oferta['preco']}\n\n"
        f"👉 <a href='{oferta['link']}'>Compre agora</a>"
    )

    try:
        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=oferta["imagem"],
            caption=texto,
            parse_mode="HTML"
        )
        logger.info(f"✅ Enviado: {oferta['titulo'][:70]} ({oferta['loja']})")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar oferta: {e}")

# ===============================
# COMANDOS
# ===============================
async def start(update, context):
    await update.message.reply_text("🤖 Bot de ofertas ativo! Use /start_posting para iniciar postagens automáticas.")

async def start_posting(update, context):
    bot = context.bot
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(postar_oferta, "interval", seconds=INTERVALO, args=[bot])
    scheduler.start()
    await update.message.reply_text("🚀 Postagens automáticas iniciadas com sucesso!")
    logger.info("🕒 Postagens automáticas ativadas via /start_posting")

# ===============================
# INÍCIO DO BOT (com proteção extra)
# ===============================
async def iniciar_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # 🔧 Remove webhook e atualizações antigas
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("🧹 Webhook e atualizações antigas removidos.")

    # Adiciona comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))

    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("🚀 Bot iniciado e escutando atualizações.")
        await asyncio.Event().wait()
    except Conflict:
        logger.warning("⚠️ Conflito detectado: outra instância estava ativa. Encerrando webhook antigo...")
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Conflito resolvido. Reiniciando bot...")
        await iniciar_bot()
    except Exception as e:
        logger.error(f"❌ Erro ao iniciar bot: {e}")

if __name__ == "__main__":
    asyncio.run(iniciar_bot())
