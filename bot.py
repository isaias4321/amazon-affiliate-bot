#!/usr/bin/env python3
import os
import time
import sqlite3
import asyncio
import logging
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    Update,
)

# ---------- CONFIG ----------
BOT_TOKEN = os.environ.get("BOT_TOKEN", "SEU_TOKEN_DO_BOT_AQUI")
GROUP_ID = os.environ.get("GROUP_ID", "-4983279500")
AFFILIATE_TAG = os.environ.get("AFFILIATE_TAG", "isaias06f-20")
INTERVAL_MIN = int(os.environ.get("INTERVAL_MIN", "5"))
DB_PATH = os.environ.get("DB_PATH", "offers.db")
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"
CATEGORY_KEYWORDS = ["game", "console", "eletrônico", "gamer", "monitor", "notebook", "teclado", "mouse"]
REQUEST_DELAY = 1
MAX_PRODUCTS_PER_ROUND = 5
# ----------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- Database ----------------
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
        discount_percent REAL,
        added_at TEXT
    )''')
    conn.commit()
    return conn

conn = init_db()
db_lock = asyncio.Lock()

# ---------------- Helpers ----------------
def safe_get_text(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning(f"Erro ao acessar {url}: {e}")
        return ""

def parse_product_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.select_one("#productTitle")
    img_tag = soup.select_one("#imgTagWrapperId img, img#landingImage")
    price_deal = soup.select_one(".a-price .a-offscreen")
    price_original = soup.select_one(".a-text-price .a-offscreen, .priceBlockStrikePriceString")

    return {
        "url": url,
        "title": title_tag.get_text(strip=True) if title_tag else "",
        "image": img_tag["src"] if img_tag and img_tag.get("src") else "",
        "price_deal": price_deal.get_text(strip=True) if price_deal else "",
        "price_original": price_original.get_text(strip=True) if price_original else "",
        "breadcrumb": " ".join([b.get_text(strip=True) for b in soup.select("#wayfinding-breadcrumbs_container a")])
    }

# ---------------- Scraper principal ----------------
def fetch_promotions_blocking(limit: int = 10) -> List[Dict]:
    html = safe_get_text(URL_AMAZON_GOLDBOX)
    if not html:
        logger.warning("Não foi possível acessar a página de ofertas da Amazon.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    promotions: List[Dict] = []
    anchors = soup.select("a[href*='/dp/'], a[href*='/gp/']")
    seen = set()

    for a in anchors:
        href = a.get("href")
        if not href:
            continue

        if href.startswith("/"):
            prod_url = "https://www.amazon.com.br" + href.split("?")[0]
        else:
            prod_url = href.split("?")[0]

        if prod_url in seen:
            continue
        seen.add(prod_url)

        time.sleep(REQUEST_DELAY)
        page_html = safe_get_text(prod_url)
        if not page_html:
            continue

        pdata = parse_product_page(page_html, prod_url)
        title = pdata.get("title", "")
        breadcrumb = pdata.get("breadcrumb", "")
        combined = (title + " " + breadcrumb).lower()

        if not any(kw in combined for kw in CATEGORY_KEYWORDS):
            continue

        price_original = pdata.get("price_original")
        price_deal = pdata.get("price_deal")

        if not price_original or not price_deal:
            continue

        try:
            old = float(price_original.replace("R$", "").replace(".", "").replace(",", "."))
            new = float(price_deal.replace("R$", "").replace(".", "").replace(",", "."))
        except ValueError:
            continue

        if old <= 0 or new >= old:
            continue

        discount_percent = round(((old - new) / old) * 100, 0)
        if discount_percent < 5:
            continue

        promotions.append({
            "title": pdata["title"],
            "url": pdata["url"],
            "image": pdata["image"],
            "price_original": pdata["price_original"],
            "price_deal": pdata["price_deal"],
            "discount_percent": discount_percent,
        })

        if len(promotions) >= limit:
            break

    logger.info("fetch_promotions encontrou %d produto(s) com desconto.", len(promotions))
    return promotions

def build_affiliate_url(url: str) -> str:
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url

# ---------------- Postagem ----------------
async def post_promotions(bot: Bot):
    promotions = await asyncio.to_thread(fetch_promotions_blocking, MAX_PRODUCTS_PER_ROUND)
    if not promotions:
        logger.info("Nenhuma promoção encontrada nesta rodada.")
        return

    for item in promotions:
        url = item["url"]
        title = item["title"]
        image = item.get("image", "")
        price_original = item.get("price_original", "")
        price_deal = item.get("price_deal", "")
        discount_percent = item.get("discount_percent", 0)
        aff_url = build_affiliate_url(url)

        async with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM offers WHERE url=?", (url,))
            if cur.fetchone():
                continue
            cur.execute(
                "INSERT INTO offers (url, title, image, price_original, price_deal, discount_percent, added_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (url, title, image, price_original, price_deal, discount_percent),
            )
            conn.commit()

        text = (
            f"<b>{title}</b>\n\n"
            f"💰 <b>{price_deal}</b> (antes {price_original})\n"
            f"📉 <b>-{discount_percent}% OFF!</b>"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta na Amazon", url=aff_url)]])

        try:
            if image:
                await bot.send_photo(chat_id=GROUP_ID, photo=image, caption=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            else:
                await bot.send_message(chat_id=GROUP_ID, text=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            logger.info("Produto postado: %s", title)
        except Exception as e:
            logger.exception("Erro ao enviar produto: %s", e)

# ---------------- Scheduler ----------------
async def scheduler_loop(application):
    logger.info("Scheduler iniciado (intervalo: %d minutos).", INTERVAL_MIN)
    while True:
        try:
            await post_promotions(application.bot)
        except Exception as e:
            logger.exception("Erro na execução do scheduler: %s", e)
        await asyncio.sleep(INTERVAL_MIN * 60)

async def start_scheduler(application):
    if "scheduler_task" in application.bot_data:
        return
    task = asyncio.create_task(scheduler_loop(application))
    application.bot_data["scheduler_task"] = task

async def stop_scheduler(application):
    task = application.bot_data.get("scheduler_task")
    if task:
        task.cancel()
        application.bot_data.pop("scheduler_task", None)
        logger.info("Scheduler parado.")

# ---------------- Comandos ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot iniciado! Use /start_posting para começar a postar ofertas automaticamente.")

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_scheduler(context.application)
    await update.message.reply_text(f"🤖 Postagens automáticas ativadas a cada {INTERVAL_MIN} minutos.")

async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_scheduler(context.application)
    await update.message.reply_text("⛔ Postagens automáticas paradas.")

async def cmd_postnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.application.bot)
    await update.message.reply_text("📤 Postagem manual feita com sucesso.")

# ---------------- Main ----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado!")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
    app.add_handler(CommandHandler("postnow", cmd_postnow))

    logger.info("🤖 Bot de ofertas iniciado. Aguardando comandos...")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
