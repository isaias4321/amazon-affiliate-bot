#!/usr/bin/env python3
import os
import asyncio
import sqlite3
import requests
import time
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import logging
from typing import List, Dict

# ---------- CONFIG ----------
BOT_TOKEN = "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A"
GROUP_ID = "-4983279500"
AFFILIATE_TAG = "isaias06f-20"
INTERVAL_MIN = 2
DB_PATH = "offers.db"
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"
CATEGORY_KEYWORDS = ["jogo", "console", "xbox", "ps5", "playstation", "headset", "fone", "notebook", "teclado", "mouse", "eletrônico", "monitor", "pc", "ssd"]
MAX_PRODUCTS_PER_ROUND = 5
REQUEST_DELAY = 1.0
# ----------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Banco de dados
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute(
    """CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        title TEXT,
        image TEXT,
        price_original TEXT,
        price_deal TEXT,
        added_at TEXT
    )"""
)
conn.commit()
db_lock = asyncio.Lock()

# --------- FUNÇÕES DE SUPORTE ---------
def safe_get_text(url: str) -> str:
    """Obtém HTML da página com headers de segurança"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.text
        else:
            logger.warning("Erro HTTP %s ao acessar %s", resp.status_code, url)
            return ""
    except Exception as e:
        logger.error("Erro ao acessar %s: %s", url, e)
        return ""

def parse_product_page(html: str, url: str) -> Dict:
    """Extrai título, imagem, preços e calcula desconto"""
    soup = BeautifulSoup(html, "html.parser")
    title_tag = soup.select_one("#productTitle")
    img_tag = soup.select_one("#landingImage")
    price_deal_tag = soup.select_one(".a-price .a-offscreen")
    price_original_tag = soup.select_one(".a-price.a-text-price .a-offscreen")

    title = title_tag.get_text(strip=True) if title_tag else ""
    image = img_tag["src"] if img_tag else ""
    price_deal = price_deal_tag.get_text(strip=True) if price_deal_tag else ""
    price_original = price_original_tag.get_text(strip=True) if price_original_tag else ""

    discount_percent = ""
    if price_original and price_deal:
        try:
            p_orig = float(price_original.replace("R$", "").replace(".", "").replace(",", "."))
            p_deal = float(price_deal.replace("R$", "").replace(".", "").replace(",", "."))
            if p_orig > p_deal:
                discount = ((p_orig - p_deal) / p_orig) * 100
                discount_percent = f" (-{int(discount)}%)"
        except Exception:
            pass

    return {
        "title": title,
        "url": url,
        "image": image,
        "price_original": price_original,
        "price_deal": price_deal,
        "discount": discount_percent
    }

def fetch_promotions_blocking(limit=MAX_PRODUCTS_PER_ROUND) -> List[Dict]:
    """Busca produtos com desconto nas categorias definidas"""
    html = safe_get_text(URL_AMAZON_GOLDBOX)
    if not html:
        logger.warning("Não foi possível acessar a página de ofertas.")
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
        if not pdata["price_original"] or not pdata["price_deal"]:
            continue

        combined = pdata["title"].lower()
        if any(kw in combined for kw in CATEGORY_KEYWORDS):
            if pdata["discount"]:  # só produtos com desconto
                promotions.append(pdata)

        if len(promotions) >= limit:
            break

    logger.info("Encontradas %d promoções elegíveis.", len(promotions))
    return promotions

def build_affiliate_url(url: str) -> str:
    """Adiciona tag de afiliado à URL"""
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url

# --------- POSTAGENS ---------
async def post_promotions(bot: Bot):
    promotions = await asyncio.to_thread(fetch_promotions_blocking)
    if not promotions:
        logger.info("Nenhuma promoção encontrada nesta rodada.")
        return

    for item in promotions:
        url = item["url"]
        title = item["title"]
        image = item["image"]
        price_original = item["price_original"]
        price_deal = item["price_deal"]
        discount = item["discount"]
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

        text = f"<b>{title}</b>\n\n💰 {price_deal}{discount}"
        if price_original and price_original != price_deal:
            text += f" (antes {price_original})"

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta na Amazon", url=aff_url)]])

        try:
            if image:
                await bot.send_photo(chat_id=GROUP_ID, photo=image, caption=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            else:
                await bot.send_message(chat_id=GROUP_ID, text=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            logger.info("Produto postado: %s", title)
        except Exception as e:
            logger.error("Erro ao enviar mensagem: %s", e)

# --------- AGENDADOR ---------
async def scheduler_loop(application):
    logger.info("Scheduler rodando a cada %d minutos.", INTERVAL_MIN)
    while True:
        try:
            await post_promotions(application.bot)
        except Exception as e:
            logger.exception("Erro no loop: %s", e)
        await asyncio.sleep(INTERVAL_MIN * 60)

async def start_scheduler(application):
    if "scheduler_task" in application.bot_data:
        logger.info("Scheduler já ativo.")
        return
    task = asyncio.create_task(scheduler_loop(application))
    application.bot_data["scheduler_task"] = task
    logger.info("Scheduler iniciado.")

async def stop_scheduler(application):
    task = application.bot_data.get("scheduler_task")
    if not task:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    del application.bot_data["scheduler_task"]
    logger.info("Scheduler parado.")

# --------- COMANDOS TELEGRAM ---------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot de ofertas Amazon ativo!\nUse /start_posting para começar a postar automaticamente.")

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_scheduler(context.application)
    await update.message.reply_text(f"🤖 Postagens automáticas ativadas a cada {INTERVAL_MIN} minutos.")

async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await stop_scheduler(context.application)
    await update.message.reply_text("⛔ Postagens automáticas paradas.")

async def cmd_postnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.application.bot)
    await update.message.reply_text("📤 Postagem manual concluída.")

# --------- MAIN ---------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
    app.add_handler(CommandHandler("postnow", cmd_postnow))
    logger.info("Bot iniciado com polling...")
    app.run_polling(stop_signals=None)

if __name__ == "__main__":
    main()
