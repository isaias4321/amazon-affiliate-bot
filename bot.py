import os
import asyncio
import time
import logging
import sqlite3
import aiohttp
from dotenv import load_dotenv
from typing import List, Dict
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ---------------- Carregar variáveis de ambiente ----------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")

if not BOT_TOKEN or not GROUP_ID:
    print("❌ ERRO: Variáveis de ambiente não encontradas!")
    print("BOT_TOKEN:", BOT_TOKEN)
    print("GROUP_ID:", GROUP_ID)
    raise ValueError("BOT_TOKEN e GROUP_ID precisam estar definidos.")

# ---------------- Configurações principais ----------------
INTERVAL_MIN = 1  # intervalo de postagens em minutos
MAX_PRODUCTS_PER_ROUND = 3
REQUEST_DELAY = 2
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

# ---------------- Logs ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------------- Banco de dados ----------------
DB_PATH = "offers.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    title TEXT,
    image TEXT,
    price_original TEXT,
    price_deal TEXT,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()
db_lock = asyncio.Lock()

# ---------------- Funções auxiliares ----------------
async def safe_get_text(url: str) -> str:
    """Faz requisição HTTP segura e retorna HTML."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status != 200:
                    logger.warning(f"Erro HTTP {resp.status} ao acessar {url}")
                    return ""
                return await resp.text()
    except Exception as e:
        logger.error(f"Erro ao acessar {url}: {e}")
        return ""

def parse_price(text: str) -> float:
    import re
    try:
        text = text.replace(".", "").replace(",", ".")
        num = float(re.search(r"(\d+(\.\d+)?)", text).group(1))
        return num
    except Exception:
        return 0.0

def parse_product_page(html: str, url: str) -> Dict:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find("span", id="productTitle")
    image_tag = soup.find("img", id="landingImage")
    price_deal = soup.find("span", class_="a-price-whole")
    price_original = soup.find("span", class_="a-text-price")

    pdata = {
        "title": title.text.strip() if title else "",
        "url": url,
        "image": image_tag["src"] if image_tag else "",
        "price_deal": price_deal.text.strip() if price_deal else "",
        "price_original": price_original.text.strip() if price_original else "",
    }
    return pdata

def fetch_promotions_blocking(limit: int = MAX_PRODUCTS_PER_ROUND) -> List[Dict]:
    """Busca promoções diretamente do Goldbox."""
    html = asyncio.run(safe_get_text(URL_AMAZON_GOLDBOX))
    if not html:
        logger.warning("Nenhum HTML retornado da Amazon.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select("a[href*='/dp/'], a[href*='/gp/']")
    seen = set()
    promotions = []

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
        page_html = asyncio.run(safe_get_text(prod_url))
        if not page_html:
            continue

        pdata = parse_product_page(page_html, prod_url)
        if pdata.get("title"):
            promotions.append(pdata)

        if len(promotions) >= limit:
            break

    logger.info("Encontradas %d promoções válidas.", len(promotions))
    return promotions

def build_affiliate_url(url: str) -> str:
    """Anexa a tag de afiliado ao link."""
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url

# ---------------- Postagem automática ----------------
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    """Envia produtos automaticamente no grupo."""
    promotions = await asyncio.to_thread(fetch_promotions_blocking, MAX_PRODUCTS_PER_ROUND)
    if not promotions:
        logger.info("Nenhuma promoção válida encontrada.")
        return

    for item in promotions:
        url = item["url"]
        title = item["title"]
        image = item.get("image", "")
        price_original = item.get("price_original", "")
        price_deal = item.get("price_deal", "")
        aff_url = build_affiliate_url(url)

        async with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM offers WHERE url=?", (url,))
            if cur.fetchone():
                continue
            cur.execute(
                "INSERT INTO offers (url, title, image, price_original, price_deal) VALUES (?, ?, ?, ?, ?)",
                (url, title, image, price_original, price_deal),
            )
            conn.commit()

        text = f"<b>{title}</b>\n\n💰 {price_deal or 'Preço indisponível'}"
        if price_original and price_original != price_deal:
            text += f" (antes {price_original})"

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta na Amazon", url=aff_url)]])

        try:
            if image:
                await context.bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=image,
                    caption=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
            else:
                await context.bot.send_message(
                    chat_id=GROUP_ID,
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                )
            logger.info("Produto postado: %s", title)
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")

# ---------------- Comandos do Telegram ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot ativo! Use /start_posting para iniciar as postagens automáticas.")

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.run_repeating(postar_ofertas, interval=60, first=10)
    await update.message.reply_text("📢 Postagens automáticas ativadas a cada 1 minuto.")

async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.stop()
    await update.message.reply_text("⛔ Postagens automáticas paradas.")

async def cmd_postnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await postar_ofertas(context)
    await update.message.reply_text("📤 Postagem manual concluída.")

# ---------------- Execução principal ----------------
def main():
    logger.info("🚀 Iniciando bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
    app.add_handler(CommandHandler("postnow", cmd_postnow))

    app.run_polling()

if __name__ == "__main__":
    main()
