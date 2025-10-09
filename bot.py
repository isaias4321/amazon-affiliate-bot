#!/usr/bin/env python3
"""
bot.py — Amazon Affiliate Deals Bot (versão completa)
Mantém a lógica original (DB, scraping, scheduler, handlers) e adiciona:
 - filtrar apenas produtos com desconto nas categorias definidas
 - calcular e mostrar percentual de desconto ao lado do preço

Variáveis de ambiente:
 - BOT_TOKEN
 - GROUP_ID (ex: -4983279500)
 - AFFILIATE_TAG (ex: isaias06f-20)
 - INTERVAL_MIN (opcional, padrão 5)
"""

from __future__ import annotations
import os
import time
import logging
import sqlite3
import asyncio
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID", "-4983279500")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", "5"))
DB_PATH = os.getenv("DB_PATH", "offers.db")

# Página principal de ofertas (Goldbox)
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

# Limites / delays
MAX_PRODUCTS_PER_ROUND = 8
REQUEST_DELAY = 0.9  # seconds between product page requests (politeness)
REQUEST_TIMEOUT = 12

# Palavras-chaves para categorias (games + eletrônicos) — mantenha/amplie conforme quiser
CATEGORY_KEYWORDS = [
    "game", "games", "videogame", "console", "ps5", "xbox", "nintendo", "switch",
    "eletrônico", "eletronico", "eletrônicos", "eletronicos", "celular", "smartphone",
    "notebook", "monitor", "ssd", "hd", "fone", "headphone", "audio", "teclado", "mouse"
]

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------------- DATABASE ----------------
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
            discount_percent REAL,
            added_at TEXT
        )
        """
    )
    conn.commit()
    return conn

conn = init_db()
# usamos lock assíncrono para proteger operações do DB dentro de async funcs
db_lock = asyncio.Lock()


# ---------------- UTILITÁRIOS HTTP ----------------
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

def safe_get_text(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """Requisição HTTP bloqueante — chame via asyncio.to_thread para não travar loop."""
    try:
        r = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.debug("safe_get_text erro %s: %s", url, e)
        return None

def parse_price_str(price_str: str) -> Optional[float]:
    """Converte string de preço 'R$ 1.234,56' para float 1234.56, ou None se falhar."""
    if not price_str:
        return None
    s = price_str.strip()
    # remove sinais comuns
    s = s.replace("R$", "").replace("R", "").replace(" ", "")
    # remover pontos de milhar e ajustar vírgula
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


# ---------------- PARSER DE PÁGINA DE PRODUTO ----------------
def parse_product_page(html: str, url: str) -> Dict[str, Optional[str]]:
    """Extrai título, imagem, preço atual e preço original, breadcrumb (categorias)."""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    image = ""
    price_deal = ""
    price_original = ""
    breadcrumb = ""

    # Título
    title_tag = soup.find(id="productTitle") or soup.select_one("span#title")
    if title_tag:
        title = title_tag.get_text(strip=True)

    # Imagem preferencial
    img_tag = soup.find(id="landingImage") or soup.select_one("#imgTagWrapperId img") or soup.select_one("img[data-old-hires]")
    if img_tag and img_tag.get("src"):
        image = img_tag.get("src")

    # Preços — tentar vários padrões
    # priceblock_dealprice, priceblock_ourprice, priceblock_saleprice
    for pid in ("priceblock_dealprice", "priceblock_ourprice", "priceblock_saleprice"):
        p = soup.find(id=pid)
        if p and p.get_text(strip=True):
            price_deal = p.get_text(strip=True)
            break
    if not price_deal:
        # fallback: span.a-price > span.a-offscreen (padrão em muitos produtos)
        off = soup.select_one("span.a-price > span.a-offscreen")
        if off:
            price_deal = off.get_text(strip=True)

    # preço original (riscar)
    strike = soup.select_one("span.priceBlockStrikePriceString, span.a-text-strike")
    if strike:
        price_original = strike.get_text(strip=True)
    else:
        # em alguns layouts o preço original aparece como primeira <span.a-offscreen> diferente do atual
        # tentamos outra heurística: procurar a versão "saving" ou "list price"
        list_price = soup.find(text=lambda t: t and ("De R$" in t or "Preço antigo" in t))
        if list_price:
            price_original = list_price.strip()

    # breadcrumb/categories
    crumbs = soup.select("#wayfinding-breadcrumbs_container a")
    if crumbs:
        breadcrumb = " ".join([c.get_text(strip=True) for c in crumbs])

    return {
        "url": url,
        "title": title or "",
        "image": image or "",
        "price_deal": price_deal or "",
        "price_original": price_original or "",
        "breadcrumb": breadcrumb or "",
    }


# ---------------- FETCH PROMOTIONS (bloqueante) ----------------
def fetch_promotions_blocking(limit: int = MAX_PRODUCTS_PER_ROUND) -> List[Dict]:
    """
    Varredura:
    - entra na página GOLD BOX (gp/goldbox)
    - coleta links candidatos (/dp/ ou /gp/)
    - visita página de produto, extrai título, imagens e preços
    - filtra apenas produtos que pertençam às CATEGORIES_KEYWORDS
    - filtra apenas produtos com desconto real (price_original > price_deal)
    - calcula discount_percent e retorna lista
    """
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

        # normalizar URL sem querystring
        if href.startswith("/"):
            prod_url = "https://www.amazon.com.br" + href.split("?")[0]
        else:
            prod_url = href.split("?")[0]

        if prod_url in seen:
            continue
        seen.add(prod_url)

        # pequeno delay para não bombardear a Amazon
        time.sleep(REQUEST_DELAY)

        page_html = safe_get_text(prod_url)
        if not page_html:
            continue

        pdata = parse_product_page(page_html, prod_url)
        title = pdata.get("title", "")
        breadcrumb = pdata.get("breadcrumb", "")
        combined = (title + " " + breadcrumb).lower()

        # filtra por categorias (games + eletrônicos)
        if not any(kw in combined for kw in CATEGORY_KEYWORDS):
            continue

        # extrair preços e converter para float
        price_original_str = pdata.get("price_original", "")
        price_deal_str = pdata.get("price_deal", "")

        if not price_original_str or not price_deal_str:
            # se não tem ambos preços, ignorar (não é promoção explicitamente detectada)
            continue

        old_val = parse_price_str(price_original_str)
        new_val = parse_price_str(price_deal_str)
        if old_val is None or new_val is None:
            continue

        # garantir que exista desconto
        if old_val <= 0 or new_val >= old_val:
            continue

        # calcular percentual
        discount_percent = round(((old_val - new_val) / old_val) * 100, 0)
        # opcional: filtrar por desconto mínimo (ex.: 1% ou 5%). manter 1% por padrão, mas aqui vamos exigir >=5%
        if discount_percent < 5:
            continue

        promotions.append({
            "title": pdata.get("title", ""),
            "url": pdata.get("url", ""),
            "image": pdata.get("image", ""),
            "price_original": price_original_str,
            "price_deal": price_deal_str,
            "discount_percent": int(discount_percent),
        })

        if len(promotions) >= limit:
            break

    logger.info("fetch_promotions_blocking: %d produto(s) com desconto encontrados.", len(promotions))
    return promotions


# ---------------- AFFILIATE URL BUILDER ----------------
def build_affiliate_url(url: str) -> str:
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url


# ---------------- POSTING LOGIC (async) ----------------
async def post_promotions(application_bot: Bot):
    # executa scraping em thread para não bloquear o loop
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

        # evitar repostagem: verificar DB
        async with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM offers WHERE url=?", (url,))
            if cur.fetchone():
                logger.debug("Ignorando oferta já postada: %s", url)
                continue
            cur.execute(
                "INSERT INTO offers (url, title, image, price_original, price_deal, discount_percent, added_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                (url, title, image, price_original, price_deal, discount_percent),
            )
            conn.commit()

        # montar texto com desconto ao lado do preço
        text = (
            f"<b>{title}</b>\n\n"
            f"💰 <b>{price_deal}</b> (antes {price_original})\n"
            f"📉 <b>-{discount_percent}% OFF</b>"
        )
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Ver oferta na Amazon", url=aff_url)]])

        try:
            if image:
                # enviar foto com legenda
                await application_bot.send_photo(chat_id=GROUP_ID, photo=image, caption=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            else:
                await application_bot.send_message(chat_id=GROUP_ID, text=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            logger.info("Produto postado: %s", title)
        except Exception as e:
            logger.exception("Erro ao enviar produto para o grupo: %s", e)


# ---------------- SCHEDULER (async-safe) ----------------
_SCHEDULER_TASK_KEY = "amazon_scheduler_task"

async def scheduler_loop(application):
    logger.info("Scheduler iniciado (intervalo %d minutos).", INTERVAL_MIN)
    try:
        while True:
            try:
                await post_promotions(application.bot)
            except Exception as e:
                logger.exception("Erro na rodada de postagens: %s", e)
            await asyncio.sleep(INTERVAL_MIN * 60)
    except asyncio.CancelledError:
        logger.info("Scheduler cancelado.")
        raise

async def start_scheduler(application) -> str:
    if _SCHEDULER_TASK_KEY in application.bot_data:
        logger.info("Scheduler já estava rodando.")
        return "already_running"
    task = asyncio.create_task(scheduler_loop(application), name="amazon_scheduler")
    application.bot_data[_SCHEDULER_TASK_KEY] = task
    logger.info("Scheduler criado.")
    return "started"

async def stop_scheduler(application) -> bool:
    task = application.bot_data.get(_SCHEDULER_TASK_KEY)
    if not task:
        return False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    application.bot_data.pop(_SCHEDULER_TASK_KEY, None)
    logger.info("Scheduler parado.")
    return True


# ---------------- TELEGRAM HANDLERS ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Bot ativo. Use /start_posting para ativar postagens automáticas de ofertas (games & eletrônicos)."
    )

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


# ---------------- MAIN ----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não configurado! Defina a variável de ambiente BOT_TOKEN.")
    logger.info("Inicializando aplicação do bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
    app.add_handler(CommandHandler("postnow", cmd_postnow))

    logger.info("Iniciando polling do bot...")
    # stop_signals=None evita conflitos em alguns ambientes gerenciados
    app.run_polling(stop_signals=None)


if __name__ == "__main__":
    main()
