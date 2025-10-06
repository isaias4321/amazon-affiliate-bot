#!/usr/bin/env python3
import os
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
import threading
import logging
import asyncio

from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------- CONFIG ----------
BOT_TOKEN = "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A"  # Substitua pelo seu token real
GROUP_ID = os.environ.get("GROUP_ID", "-4983279500")
AFFILIATE_TAG = os.environ.get("AFFILIATE_TAG", "isaias06f-20")
INTERVAL_MIN = int(os.environ.get("INTERVAL_MIN", "5"))
DB_PATH = os.environ.get("DB_PATH", "offers.db")
# ----------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
sched = BackgroundScheduler()
sched.start()

# Database
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        title TEXT,
        image TEXT,
        price_original TEXT,
        price_deal TEXT,
        notes TEXT,
        added_at TEXT
    )''')
    conn.commit()
    return conn

conn = init_db()
db_lock = threading.Lock()

# Simulação de busca automática de promoções
def fetch_promotions():
    # Aqui você pode implementar scraping real da Amazon
    return [{
        "title": "Produto Exemplo",
        "url": "https://www.amazon.com.br/dp/B08EXAMPLE",
        "image": "",
        "price_original": "R$ 100,00",
        "price_deal": "R$ 79,90"
    }]

def build_affiliate_url(url):
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url

# Função que envia as promoções
async def post_promotions():
    bot = Bot(token=BOT_TOKEN)  # Cria o bot dentro do job
    promotions = fetch_promotions()
    for item in promotions:
        url = item["url"]
        title = item["title"]
        price_original = item["price_original"]
        price_deal = item["price_deal"]
        image = item["image"]
        aff_url = build_affiliate_url(url)
        msg_text = f"<b>{title}</b>\n💰 {price_deal} (antes {price_original})"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Comprar / Ver Oferta", url=aff_url)]])
        try:
            if image:
                await bot.send_photo(chat_id=GROUP_ID, photo=image, caption=msg_text,
                                     parse_mode=ParseMode.HTML, reply_markup=keyboard)
            else:
                await bot.send_message(chat_id=GROUP_ID, text=msg_text,
                                       parse_mode=ParseMode.HTML, reply_markup=keyboard)
            logger.info(f"Oferta postada: {title}")
        except Exception as e:
            logger.exception("Erro ao postar promoção: %s", e)

# Scheduler seguro
def start_scheduler():
    if sched.get_job("post_job"):
        sched.remove_job("post_job")

    def run_job():
        asyncio.create_task(post_promotions())

    sched.add_job(run_job, 'interval', minutes=INTERVAL_MIN)
    logger.info("Scheduler iniciado")

# Comandos Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot de ofertas Amazon iniciado!")

async def start_posting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_scheduler()
    await update.message.reply_text(f"Postagens automáticas ativadas a cada {INTERVAL_MIN} minutos.")

async def stop_posting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if sched.get_job("post_job"):
        sched.remove_job("post_job")
    await update.message.reply_text("Postagens paradas.")

async def postnow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_promotions()
    await update.message.reply_text("Post realizado.")

# Inicialização do bot
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting_cmd))
    application.add_handler(CommandHandler("stop_posting", stop_posting_cmd))
    application.add_handler(CommandHandler("postnow", postnow_cmd))
    application.run_polling()

if __name__ == "__main__":
    main()

