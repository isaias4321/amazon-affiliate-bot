"""
Bot de Ofertas Amazon (Games & Eletrônicos) com Afiliado
Atualizado: Intervalo fixo de 2 minutos + cálculo de desconto
"""

import os
import asyncio
import aiohttp
import time
import logging
import sqlite3
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from telegram import (
    Bot,
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

# ---------------- Configurações ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN") or "COLOQUE_SEU_TOKEN_AQUI"
GROUP_ID = int(os.getenv("GROUP_ID") or "-4983279500")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG") or "isaias06f-20"

INTERVAL_MIN = 2  # intervalo fixo de 2 minutos
MAX_PRODUCTS_PER_ROUND = 5
REQUEST_DELAY = 1.5

URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"
CATEGORY_KEYWORDS = ["game", "ps5", "xbox", "eletrônic", "notebook", "headset", "mouse", "monitor", "pc gamer"]

# Banco local para evitar repostagens duplicadas
conn = sqlite3.connect("offers.db", check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    title TEXT,
    image TEXT,
    price_original TEXT,
    price_deal TEXT,
    added_at TEXT
)
""")
conn.commit()
db_lock = asyncio.Lock()

# Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------- Funções de scraping ----------------
async def safe_get_text(url: str) -> Optional[str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.text()
                return None
    except Exception as e:
        logger.warning(f"Erro ao acessar {url}: {e}")
        return None


def parse_product_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")

    title = soup.select_one("#productTitle")
    title = title.get_text(strip=True) if title else "(sem título)"

    price_deal = soup.select_one(".a-price .a-offscreen")
    price_deal = price_deal.get_text(strip=True) if price_deal else ""

    price_original = soup.select_one(".a-price.a-text-price .a-offscreen")
    price_original = price_original.get_text(strip=True) if price_original else ""

    img = soup.select_one("#imgTagWrapperId img")
    img_url = img["src"] if img and "src" in img.attrs else ""

    breadcrumb = " ".join([b.get_text(strip=True) for b in soup.select("#wayfinding-breadcrumbs_feature_div li")])

    # Calcular desconto (se aplicável)
    desconto = ""
    if price_original and price_deal and price_original != price_deal:
        try:
            orig = float(price_original.replace("R$", "").replace(".", "").replace(",", "."))
            deal = float(price_deal.replace("R$", "").replace(".", "").replace(",", "."))
            pct = round((1 - deal / orig) * 100)
            desconto = f"{pct}% OFF"
        except Exception:
            desconto = ""

    return {
        "url": url,
        "title": title,
        "image": img_url,
        "price_original": price_original,
        "price_deal": price_deal,
        "breadcrumb": breadcrumb,
        "discount": desconto,
    }


def fetch_promotions_blocking(limit=MAX_PRODUCTS_PER_ROUND) -> List[Dict]:
    """Executa o scraping de forma síncrona (rodando em thread paralela)."""
    import requests

    try:
        resp = requests.get(URL_AMAZON_GOLDBOX, timeout=15)
        html = resp.text if resp.status_code == 200 else ""
    except Exception:
        return []

    soup = BeautifulSoup(html, "html.parser")
    promotions = []
    anchors = soup.select("a[href*='/dp/'], a[href*='/gp/']")
    seen = set()

    for a in anchors:
        href = a.get("href")
        if not href:
            continue
        prod_url = "https://www.amazon.com.br" + href.split("?")[0] if href.startswith("/") else href.split("?")[0]
        if prod_url in seen:
            continue
        seen.add(prod_url)
        time.sleep(REQUEST_DELAY)

        try:
            r = requests.get(prod_url, timeout=10)
            pdata = parse_product_page(r.text, prod_url)
        except Exception:
            continue

        combined = (pdata.get("title", "") + " " + pdata.get("breadcrumb", "")).lower()
        if any(kw in combined for kw in CATEGORY_KEYWORDS):
            # só adiciona se tiver desconto
            if pdata["discount"]:
                promotions.append(pdata)

        if len(promotions) >= limit:
            break

    logger.info("fetch_promotions encontrou %d produtos.", len(promotions))
    return promotions


def build_affiliate_url(url: str) -> str:
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url

# ---------------- Envio das promoções ----------------
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
        discount = item.get("discount", "")
        aff_url = build_affiliate_url(url)

        async with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM offers WHERE url=?", (url,))
            if cur.fetchone():
                continue
            cur.execute(
                "INSERT INTO offers (url, title, image, price_original, price_deal, added_at) VALUES (?, ?, ?, ?, ?, datetime('now'))",
                (url, title, image, price_original, price_deal),
            )
            conn.commit()

        text = f"<b>{title}</b>\n\n💰 {price_deal}"
        if price_original and price_original != price_deal:
            text += f" (antes {price_original})"
        if discount:
            text += f" 🎯 {discount}"

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta na Amazon", url=aff_url)]])

        try:
            if image:
                await bot.send_photo(chat_id=GROUP_ID, photo=image, caption=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            else:
                await bot.send_message(chat_id=GROUP_ID, text=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            logger.info("Produto postado: %s", title)
        except Exception as e:
            logger.error("Erro ao enviar produto: %s", e)


# ---------------- Scheduler ----------------
async def scheduler_loop(application):
    logger.info("Scheduler iniciado (intervalo %d minutos).", INTERVAL_MIN)
    while True:
        try:
            await post_promotions(application.bot)
        except Exception as e:
            logger.error("Erro no scheduler: %s", e)
        await asyncio.sleep(INTERVAL_MIN * 60)


async def start_scheduler(application):
    if "scheduler_task" in application.bot_data:
        return
    task = asyncio.create_task(scheduler_loop(application))
    application.bot_data["scheduler_task"] = task


async def stop_scheduler(application):
    task = application.bot_data.pop("scheduler_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# ---------------- Handlers Telegram ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot inicializado. Use /start_posting para ativar postagens automáticas.")


async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_scheduler(context.application)
    await update.message.reply_text(f"🤖 Postagens automáticas ativadas a cada {INTERVAL_MIN} minutos.")


async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_scheduler(context.application)
    await update.message.reply_text("⛔ Postagens automáticas paradas.")


async def cmd_postnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.application.bot)
    await update.message.reply_text("📤 Postagem manual enviada.")


# ---------------- Main ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
    app.add_handler(CommandHandler("postnow", cmd_postnow))

    logger.info("Bot iniciado. Polling ativo.")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
