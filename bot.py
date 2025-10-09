import os
import asyncio
import logging
import sqlite3
import time
import re
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from telegram import (
    Bot,
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ---------------- CONFIGURAÇÕES ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = "isaias06f-20"  # Seu ID de afiliado Amazon
INTERVAL_MIN = 5  # intervalo em minutos
MAX_PRODUCTS_PER_ROUND = 5
REQUEST_DELAY = 1.5
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

CATEGORY_KEYWORDS = [
    "eletrônico", "fones", "notebook", "mouse", "teclado",
    "smartphone", "tablet", "monitor", "tv", "ssd", "hd",
    "headset", "caixa de som", "periférico", "acessório"
]

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------- BANCO DE DADOS ----------------
conn = sqlite3.connect("offers.db", check_same_thread=False)
conn.execute(
    """CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        title TEXT,
        image TEXT,
        price_original TEXT,
        price_deal TEXT,
        added_at TEXT DEFAULT CURRENT_TIMESTAMP
    )"""
)
conn.commit()
db_lock = asyncio.Lock()


# ---------------- FUNÇÕES DE PARSE ----------------
def safe_get_text(url: str) -> Optional[str]:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        logger.warning("Erro ao acessar %s: %s", url, e)
    return None


def parse_price(text: str) -> Optional[float]:
    if not text:
        return None
    text = text.replace("R$", "").replace(".", "").replace(",", ".")
    try:
        return float(re.findall(r"\d+\.\d+", text)[0])
    except IndexError:
        return None


def parse_product_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("#productTitle")
    image = soup.select_one("#landingImage, #imgBlkFront, img[data-old-hires]")
    price_deal = soup.select_one(".a-price .a-offscreen")
    price_original = soup.select_one(".a-text-price .a-offscreen")

    title = title.get_text(strip=True) if title else "Produto sem título"
    image = image.get("src") if image else ""
    price_deal_text = price_deal.get_text(strip=True) if price_deal else ""
    price_original_text = price_original.get_text(strip=True) if price_original else ""

    return {
        "title": title,
        "image": image,
        "url": url,
        "price_original": price_original_text,
        "price_deal": price_deal_text,
        "price_original_value": parse_price(price_original_text),
        "price_deal_value": parse_price(price_deal_text),
        "breadcrumb": " ".join([b.get_text(strip=True) for b in soup.select("#wayfinding-breadcrumbs_feature_div a")]),
    }


# ---------------- COLETA DE PROMOÇÕES ----------------
def fetch_promotions_blocking(limit: int) -> List[Dict]:
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

        # Calcula desconto
        p_original = pdata.get("price_original_value")
        p_deal = pdata.get("price_deal_value")

        if not p_original or not p_deal or p_deal >= p_original:
            continue  # pula produtos sem desconto real

        discount_pct = round(((p_original - p_deal) / p_original) * 100)
        pdata["discount_pct"] = discount_pct

        combined = (pdata.get("title", "") + " " + pdata.get("breadcrumb", "")).lower()
        if any(kw in combined for kw in CATEGORY_KEYWORDS):
            promotions.append(pdata)

        if len(promotions) >= limit:
            break

    logger.info("fetch_promotions encontrou %d produtos com desconto.", len(promotions))
    return promotions


# ---------------- CONSTRUÇÃO DO LINK AFILIADO ----------------
def build_affiliate_url(url: str) -> str:
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url


# ---------------- POSTAGEM NO TELEGRAM ----------------
async def post_promotions(application_bot: Bot):
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
        discount_pct = item.get("discount_pct", 0)
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

        text = f"<b>{title}</b>\n\n💰 {price_deal} (-{discount_pct}%)"
        if price_original and price_original != price_deal:
            text += f" (antes {price_original})"

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta na Amazon 🔗", url=aff_url)]])

        try:
            if image:
                await application_bot.send_photo(
                    chat_id=GROUP_ID, photo=image, caption=text,
                    parse_mode=ParseMode.HTML, reply_markup=keyboard
                )
            else:
                await application_bot.send_message(
                    chat_id=GROUP_ID, text=text,
                    parse_mode=ParseMode.HTML, reply_markup=keyboard
                )
            logger.info("Postado: %s", title)
        except Exception as e:
            logger.exception("Erro ao enviar mensagem: %s", e)


# ---------------- SCHEDULER ----------------
_scheduler_task_name = "amazon_scheduler_task"

async def scheduler_loop(application):
    logger.info("Scheduler iniciado, postando a cada %d minutos.", INTERVAL_MIN)
    try:
        while True:
            start_time = time.time()
            try:
                await post_promotions(application.bot)
            except Exception as e:
                logger.exception("Erro na rodada de postagens: %s", e)

            elapsed = time.time() - start_time
            await asyncio.sleep(max(0, INTERVAL_MIN * 60 - elapsed))
    except asyncio.CancelledError:
        logger.info("Scheduler cancelado.")
        raise


async def start_scheduler(application) -> str:
    if _scheduler_task_name in application.bot_data:
        return "already_running"
    task = asyncio.create_task(scheduler_loop(application), name=_scheduler_task_name)
    application.bot_data[_scheduler_task_name] = task
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
    return True


# ---------------- COMANDOS ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ativo. Use /start_posting para iniciar postagens automáticas.")


async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start_scheduler(context.application)
    await update.message.reply_text(f"🤖 Postagens automáticas ativadas a cada {INTERVAL_MIN} minutos.")


async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stopped = await stop_scheduler(context.application)
    msg = "⛔ Postagens automáticas paradas." if stopped else "⛔ Scheduler não estava rodando."
    await update.message.reply_text(msg)


async def cmd_postnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.application.bot)
    await update.message.reply_text("📤 Postagem manual concluída.")


# ---------------- MAIN ----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN ausente nas variáveis de ambiente.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
    app.add_handler(CommandHandler("postnow", cmd_postnow))

    logger.info("Bot iniciado e aguardando comandos...")
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
