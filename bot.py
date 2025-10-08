#!/usr/bin/env python3
import os
import sqlite3
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Update
import threading
import logging

# ---------- CONFIG ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Corrigido aqui!
GROUP_ID = os.environ.get("GROUP_ID", "-4983279500")
AFFILIATE_TAG = os.environ.get("AFFILIATE_TAG", "isaias06f-20")
INTERVAL_MIN = int(os.environ.get("INTERVAL_MIN", "5"))
DB_PATH = os.environ.get("DB_PATH", "offers.db")
URL_AMAZON = "https://www.amazon.com.br/gp/goldbox"
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
        price_original TEXT,
        price_deal TEXT,
        added_at TEXT
    )''')
    conn.commit()
    return conn

conn = init_db()
db_lock = threading.Lock()

# Fetch promotions from Amazon
def fetch_promotions():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(URL_AMAZON, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        promotions = []
        deal_items = soup.find_all("div", class_="DealGridItem-module__dealItem")
        for item in deal_items[:5]:
            title_tag = item.find("span", class_="DealContent-module__truncate_sWbxETx42ZPStTc9jwySW")
            price_tag = item.find("span", class_="PriceBlock__PriceString")
            url_tag = item.find("a", href=True)

            if title_tag and price_tag and url_tag:
                promotions.append({
                    "title": title_tag.text.strip(),
                    "url": "https://www.amazon.com.br" + url_tag["href"],
                    "price_original": "",
                    "price_deal": price_tag.text.strip()
                })
        return promotions
    except Exception as e:
        logger.exception("Erro ao buscar promoções: %s", e)
        return []

def build_affiliate_url(url):
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url

async def post_promotions(bot: Bot):
    promotions = fetch_promotions()
    for item in promotions:
        url = item["url"]
        title = item["title"]
        price_original = item["price_original"]
        price_deal = item["price_deal"]
        aff_url = build_affiliate_url(url)

        with db_lock:
            c = conn.cursor()
            c.execute("SELECT 1 FROM offers WHERE url=?", (url,))
            if c.fetchone():
                continue
            c.execute("INSERT INTO offers (url, title, price_original, price_deal, added_at) VALUES (?, ?, ?, ?, datetime('now'))",
                      (url, title, price_original, price_deal))
            conn.commit()

        msg_text = f"<b>{title}</b>\n💰 {price_deal}"
        if price_original:
            msg_text += f" (antes {price_original})"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Comprar / Ver Oferta", url=aff_url)]])
        try:
            await bot.send_message(chat_id=GROUP_ID, text=msg_text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            logger.info(f"Oferta postada: {title}")
        except Exception as e:
            logger.exception("Erro ao postar promoção: %s", e)

async def scheduled_job(application):
    await post_promotions(application.bot)

def start_scheduler(application):
    if sched.get_job("post_job"):
        sched.remove_job("post_job")
    sched.add_job(lambda: application.create_background_task(scheduled_job(application)),
                  'interval', minutes=INTERVAL_MIN, id="post_job", next_run_time=None)
    logger.info("Scheduler iniciado")

# Comandos Telegram
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot de ofertas Amazon iniciado!")

async def start_posting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_scheduler(context.application)
    await update.message.reply_text(f"🤖 Postagens automáticas ativadas a cada {INTERVAL_MIN} minutos.")

async def stop_posting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if sched.get_job("post_job"):
        sched.remove_job("post_job")
    await update.message.reply_text("⛔ Postagens paradas.")

async def postnow_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.application.bot)
    await update.message.reply_text("📤 Post realizado manualmente.")

def main():
    if not BOT_TOKEN:
        raise ValueError("❌ BOT_TOKEN não definido nas variáveis de ambiente!")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting_cmd))
    application.add_handler(CommandHandler("stop_posting", stop_posting_cmd))
    application.add_handler(CommandHandler("postnow", postnow_cmd))
    application.run_polling()

if __name__ == "__main__":
    main()
