import os
import asyncio
import logging
import aiohttp
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import nest_asyncio

# Corrige loop do asyncio no Railway
nest_asyncio.apply()

# ---------------- CONFIGURAÇÕES ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Seu token do BotFather
GROUP_ID = os.getenv("GROUP_ID", "-4983279500")
API_URL = "https://amazon-affiliate-bot-production.up.railway.app/buscar"
SEARCH_TERMS = [
    "notebook", "monitor", "mouse gamer", "cadeira gamer", "ssd", "tv", "fone bluetooth",
    "geladeira", "ferramenta", "placa de vídeo", "processador", "fonte gamer"
]
INTERVAL_MIN = 1  # minutos

# ---------------- LOGS ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ---------------- FUNÇÕES ----------------
async def fetch_from_api(session, term: str):
    """Busca produtos da sua API hospedada no Railway"""
    try:
        async with session.get(API_URL, params={"q": term}) as resp:
            if resp.status != 200:
                logger.warning(f"Erro {resp.status} ao buscar {term}")
                return []
            data = await resp.json()
            return data.get("results", [])
    except Exception as e:
        logger.error(f"Erro ao buscar {term}: {e}")
        return []


async def get_promotions():
    """Busca múltiplas categorias de produtos"""
    async with aiohttp.ClientSession() as session:
        results = []
        for term in SEARCH_TERMS:
            produtos = await fetch_from_api(session, term)
            results.extend(produtos)
            await asyncio.sleep(1)  # evita flood
        return results[:5]  # limita a 5 por rodada


async def post_promotions(application_bot):
    """Posta as ofertas automaticamente no grupo"""
    produtos = await get_promotions()
    if not produtos:
        logger.warning("Nenhum produto encontrado nesta rodada.")
        return

    for p in produtos:
        title = p.get("title", "Produto sem título")
        price = p.get("price", "N/A")
        image = p.get("image", "")
        url = p.get("url", "")

        text = f"<b>{title}</b>\n💰 Preço: {price}\n\n<a href='{url}'>Ver na Amazon</a>"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Ver oferta", url=url)]])

        try:
            if image:
                await application_bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=image,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
            else:
                await application_bot.send_message(
                    chat_id=GROUP_ID,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
            logger.info(f"✅ Produto postado: {title}")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Erro ao postar produto: {e}")


# ---------------- COMANDOS TELEGRAM ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ativo! Use /start_posting para começar as postagens automáticas.")


async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    job_queue = context.job_queue
    job_queue.run_repeating(postar_job, interval=INTERVAL_MIN * 60, first=5)
    await update.message.reply_text(f"🤖 Postagens automáticas a cada {INTERVAL_MIN} minuto(s).")


async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.stop()
    await update.message.reply_text("⛔ Postagens automáticas interrompidas.")


async def cmd_postnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.application.bot)
    await update.message.reply_text("📤 Postagem manual concluída!")


# ---------------- JOB ----------------
async def postar_job(context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.application.bot)


# ---------------- EXECUÇÃO PRINCIPAL ----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado nas variáveis de ambiente!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
    app.add_handler(CommandHandler("postnow", cmd_postnow))

    logger.info("🚀 Bot iniciado e aguardando comandos...")
    app.run_polling()


if __name__ == "__main__":
    main()
