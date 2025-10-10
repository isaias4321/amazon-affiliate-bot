import os
import asyncio
import time
import logging
import sqlite3
import aiohttp
from typing import List, Dict
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    JobQueue,
)

# ---------------- Configurações principais ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID", "-4983279500")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")

INTERVAL_MIN = 2  # Intervalo de postagens automáticas (em minutos)
MAX_PRODUCTS_PER_ROUND = 3
REQUEST_DELAY = 2
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

# ---------------- Categorias específicas ----------------
CATEGORY_KEYWORDS = [
    # Produtos gamers
    "gamer", "cadeira gamer", "mouse gamer", "teclado gamer", "monitor gamer",
    "headset gamer", "console", "playstation", "xbox", "nintendo", "rgb",
    "pc gamer", "gabinete", "placa de vídeo", "gpu", "ssd", "memória ram", "cooler",
    "processador", "fonte", "placa mãe",

    # Eletrônicos
    "eletrônico", "eletronico", "smartphone", "celular", "notebook", "tablet",
    "televisão", "tv", "caixa de som", "fone", "carregador", "usb", "bluetooth",

    # Eletrodomésticos
    "geladeira", "micro-ondas", "microondas", "fogão", "cafeteira", "batedeira",
    "liquidificador", "aspirador", "ventilador", "ar condicionado", "lava-louças",
    "lavadora", "secadora", "panela elétrica", "airfryer", "fritadeira elétrica",

    # Ferramentas
    "ferramenta", "furadeira", "parafusadeira", "chave de fenda", "compressor",
    "serra", "multímetro", "trena", "caixa de ferramentas", "maçarico",
]

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
    html = asyncio.run(safe_get_text(URL_AMAZON_GOLDBOX))
    if not html:
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
        title_lower = pdata.get("title", "").lower()

        if any(kw in title_lower for kw in CATEGORY_KEYWORDS):
            p1 = parse_price(pdata.get("price_original", ""))
            p2 = parse_price(pdata.get("price_deal", ""))
            if p1 > 0 and p2 > 0 and p2 < p1:
                discount_pct = round((1 - (p2 / p1)) * 100)
                pdata["discount"] = discount_pct
                promotions.append(pdata)

        if len(promotions) >= limit:
            break

    logger.info("Encontradas %d promoções com desconto válido.", len(promotions))
    return promotions


def build_affiliate_url(url: str) -> str:
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url


# ---------------- Postagem automática ----------------
async def post_promotions(application_bot):
    promotions = await asyncio.to_thread(fetch_promotions_blocking, MAX_PRODUCTS_PER_ROUND)
    if not promotions:
        logger.info("Nenhuma promoção válida encontrada nesta rodada.")
        return

    for item in promotions:
        url = item["url"]
        title = item["title"]
        image = item.get("image", "")
        price_original = item.get("price_original", "")
        price_deal = item.get("price_deal", "")
        discount = item.get("discount", 0)
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

        text = f"<b>{title}</b>\n\n💰 {price_deal}"
        if price_original and price_original != price_deal:
            text += f" (antes {price_original})"
        if discount:
            text += f" 🔻 {discount}% OFF"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta na Amazon", url=aff_url)]])

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
            logger.info("Produto postado: %s", title)
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")


# ---------------- Scheduler (JobQueue) ----------------
async def postar_ofertas_automaticamente(context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.bot)


async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.run_repeating(postar_ofertas_automaticamente, interval=120, first=5)
    await update.message.reply_text("🤖 Postagens automáticas ativadas a cada 2 minutos.")


async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.job_queue.stop()
    await update.message.reply_text("⛔ Postagens automáticas paradas.")


async def post_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await post_promotions(context.bot)
    await update.message.reply_text("📤 Postagem manual realizada!")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot inicializado! Use /start_posting para começar as postagens automáticas.")


# ---------------- Execução principal ----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado nas variáveis de ambiente.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # ✅ Garante que o JobQueue está ativo
    if not app.job_queue:
        jq = JobQueue()
        jq.set_application(app)
        jq.start()
        app.job_queue = jq

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_posting", start_posting))
    app.add_handler(CommandHandler("stop_posting", stop_posting))
    app.add_handler(CommandHandler("postnow", post_now))

    logger.info("🚀 Bot iniciado e rodando com JobQueue ativa...")
    app.run_polling()


if __name__ == "__main__":
    main()
