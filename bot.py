#!/usr/bin/env python3
"""
Bot Telegram — Amazon Deals (Games & Eletrônicos)
- Busca promoções da Amazon Brasil (goldbox) filtrando por categorias (games / eletrônicos)
- Posta automaticamente no grupo com: imagem, título, preço e botão com link de afiliado
- Evita repostar ofertas já publicadas (SQLite)
- Scheduler assíncrono seguro (compatível python-telegram-bot v21+ / Python 3.11)

USO:
- Defina variáveis de ambiente: BOT_TOKEN, GROUP_ID, AFFILIATE_TAG, INTERVAL_MIN (opcional)
- Rode: python bot.py
"""

from __future__ import annotations
import os
import sqlite3
import requests
from bs4 import BeautifulSoup
import asyncio
import logging
import time
from typing import List, Dict, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")               # ex: "123456789:ABC..."
GROUP_ID = os.getenv("GROUP_ID", "-4983279500")  # ex: "-4983279500"
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", "5"))
DB_PATH = os.getenv("DB_PATH", "offers.db")
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"
MAX_PRODUCTS_PER_ROUND = 6     # quantos produtos por rodada
REQUEST_DELAY = 0.8            # segundos entre requests de produto (polidez)
REQUEST_TIMEOUT = 12           # seconds
# keywords to detect games/electronics in title/breadcrumb (pt + common en)
CATEGORY_KEYWORDS = [
    "games", "game", "videogame", "console", "ps5", "ps4", "xbox", "nintendo", "switch",
    "eletrônico", "eletronico", "eletrônicos", "eletronicos", "celular", "notebook",
    "fone", "headphone", "audio", "tv", "smartphone", "tablet", "monitor", "ssd", "hd", "controle",
]
# ----------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("amazon-deals-bot")


# ---------------- Database ----------------
def init_db(path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(path, check_same_thread=False)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            image TEXT,
            price_original TEXT,
            price_deal TEXT,
            added_at TEXT
        )
        """
    )
    conn.commit()
    return conn


conn = init_db()
db_lock = asyncio.Lock()  # used only in async functions with await


# ---------------- HTTP helpers ----------------
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def safe_get_text(url: str, headers: Optional[dict] = None, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """Blocking network call — keep it inside asyncio.to_thread to avoid blocking event loop."""
    headers = headers or DEFAULT_HEADERS
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.debug("HTTP error for %s: %s", url, e)
        return None


# ---------------- Scraping logic ----------------
def extract_text(el) -> str:
    return el.get_text(strip=True) if el else ""


def parse_product_page(html: str, url: str) -> Dict[str, str]:
    """Parse a product page HTML and return dict with title, image, price_deal, price_original."""
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find(id="productTitle")
    title = extract_text(title_tag) or None

    # image
    image_tag = soup.find(id="landingImage")
    if not image_tag:
        image_tag = soup.select_one("img[id*='img']")
    image = image_tag.get("src") if image_tag and image_tag.get("src") else ""

    # price detection (many variations)
    price_deal = None
    for pid in ("priceblock_dealprice", "priceblock_ourprice", "priceblock_saleprice"):
        t = soup.find(id=pid)
        if t and extract_text(t):
            price_deal = extract_text(t)
            break
    if not price_deal:
        p = soup.select_one("span.a-price > span.a-offscreen")
        if p:
            price_deal = extract_text(p)

    # original price (strike)
    price_original = None
    strike = soup.select_one("span.priceBlockStrikePriceString, span.a-text-strike")
    if strike:
        price_original = extract_text(strike)

    if not price_deal:
        price_deal = "Preço indisponível"
    if not price_original:
        price_original = price_deal

    # breadcrumb
    breadcrumb_nodes = soup.select("#wayfinding-breadcrumbs_container a")
    breadcrumb = " ".join([extract_text(n) for n in breadcrumb_nodes]) if breadcrumb_nodes else ""

    return {
        "title": title or "Produto",
        "image": image,
        "price_deal": price_deal,
        "price_original": price_original,
        "breadcrumb": breadcrumb,
        "url": url,
    }


def fetch_promotions_blocking(limit: int = MAX_PRODUCTS_PER_ROUND) -> List[Dict]:
    """
    Blocking function: scrape goldbox page, find candidate product links, fetch product pages,
    filter by CATEGORY_KEYWORDS, return list of product dicts.
    """
    html = safe_get_text(URL_AMAZON_GOLDBOX)
    if not html:
        logger.warning("Não foi possível acessar a página de ofertas da Amazon.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    promotions: List[Dict] = []
    # find candidate anchors - prefer /dp/ links but accept /gp/
    anchors = soup.select("a[href*='/dp/'], a[href*='/gp/']")
    seen = set()

    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        # normalize to product url without querystring
        if href.startswith("/"):
            prod_url = "https://www.amazon.com.br" + href.split("?")[0]
        else:
            prod_url = href.split("?")[0]
        if prod_url in seen:
            continue
        seen.add(prod_url)

        # politely wait a bit between requests
        time.sleep(REQUEST_DELAY)

        page_html = safe_get_text(prod_url)
        if not page_html:
            continue

        pdata = parse_product_page(page_html, prod_url)

        # decide if product matches categories by checking title + breadcrumb
        combined = (pdata.get("title", "") + " " + pdata.get("breadcrumb", "")).lower()
        if any(kw in combined for kw in CATEGORY_KEYWORDS):
            promotions.append({
                "title": pdata["title"],
                "url": pdata["url"],
                "image": pdata["image"],
                "price_original": pdata["price_original"],
                "price_deal": pdata["price_deal"],
            })

        if len(promotions) >= limit:
            break

    logger.info("fetch_promotions found %d candidate(s).", len(promotions))
    return promotions


def build_affiliate_url(url: str) -> str:
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url


# ---------------- Posting logic ----------------
async def post_promotions(application_bot: Bot):
    # run blocking scraping in thread to avoid blocking loop
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
        aff_url = build_affiliate_url(url)

        # check DB to avoid repeats (use async lock)
        async with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM offers WHERE url=?", (url,))
            if cur.fetchone():
                logger.debug("Oferta já postada anteriormente: %s", url)
                continue
            cur.execute(
                "INSERT INTO offers (url, title, image, price_original, price_deal, added_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (url, title, image, price_original, price_deal),
            )
            conn.commit()

        text = f"<b>{title}</b>\n\n💰 {price_deal}"
        if price_original and price_original != price_deal:
            text += f" (antes {price_original})"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta na Amazon", url=aff_url)]])

        try:
            if image:
                # send photo with caption (caption limited)
                await application_bot.send_photo(chat_id=GROUP_ID, photo=image, caption=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            else:
                await application_bot.send_message(chat_id=GROUP_ID, text=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            logger.info("Postado produto: %s", title)
        except Exception as e:
            logger.exception("Erro ao enviar mensagem para o grupo: %s", e)


# ---------------- Scheduler (async-safe) ----------------
_scheduler_task_name = "amazon_scheduler_task"


async def scheduler_loop(application):
    logger.info("Scheduler loop iniciado (interval %d minutos).", INTERVAL_MIN)
    try:
        while True:
            try:
                await post_promotions(application.bot)
            except Exception as e:
                logger.exception("Erro na rodada de postagens: %s", e)
            await asyncio.sleep(INTERVAL_MIN * 60)
    except asyncio.CancelledError:
        logger.info("Scheduler loop cancelado.")
        raise


async def start_scheduler(application) -> str:
    """Start scheduler if not already running. Returns id/name of task."""
    # store task reference in application.bot_data to avoid duplicates
    if _scheduler_task_name in application.bot_data:
        logger.info("Scheduler já está rodando.")
        return "already_running"
    task = asyncio.create_task(scheduler_loop(application), name="amazon_scheduler")
    application.bot_data[_scheduler_task_name] = task
    logger.info("Scheduler criado e em execução.")
    return "started"


async def stop_scheduler(application) -> bool:
    task = application.bot_data.get(_scheduler_task_name)
    if not task:
        return False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    application.bot_data.pop(_scheduler_task_name, None)
    logger.info("Scheduler parado.")
    return True


# ---------------- Telegram command handlers ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot inicializado. Use /start_posting para ativar postagens automáticas.")


async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_scheduler(context.application)
    await update.message.reply_text(f"🤖 Postagens automáticas ativadas a cada {INTERVAL_MIN} minutos.")


async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stopped = await stop_scheduler(context.application)
    if stopped:
        await update.message.reply_text("⛔ Postagens automáticas paradas.")
    else:
        await update.message.reply_text("⛔ Scheduler não estava rodando.")


async def cmd_postnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.application.bot)
    await update.message.reply_text("📤 Post realizado manualmente.")


# ---------------- Main ----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN faltando nas variáveis de ambiente. Configure e tente novamente.")

    # Build application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
    app.add_handler(CommandHandler("postnow", cmd_postnow))

    logger.info("Iniciando polling do bot...")
    app.run_polling(stop_signals=None)  # run until killed


if __name__ == "__main__":
    main()
