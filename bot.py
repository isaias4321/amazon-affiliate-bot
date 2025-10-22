import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    AIORateLimiter,
)

# =========================
# CONFIGURAÇÕES DO BOT
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()  # ex: https://seu-dominio.com/webhook/<token>
PORT = int(os.getenv("PORT", "8080"))
LISTEN_ADDR = "0.0.0.0"

# Chat para postagens (único, conforme sua escolha)
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "-1003140787649"))

# Frequência: 1 oferta a cada 2 minutos
POST_INTERVAL_MINUTES = 2

# Categorias-alvo (palavras-chave)
CATEGORIES = [
    "smartphone",
    "notebook",
    "periféricos gamer",
    "eletrodomésticos",
    "ferramentas",
]

# Sua etiqueta (rótulo) de afiliado no Mercado Livre (use a que aparece no painel, ex.: im20250701092308)
MELI_AFFIL_LABEL = os.getenv("MELI_AFFIL_LABEL", "im20250701092308")

# Shopee: endpoints públicos (busca + flash sale)
SHOPEE_SEARCH_URL = "https://shopee.com.br/api/v4/search/search_items"
SHOPEE_FLASH_URL = "https://shopee.com.br/api/v4/flash_sale/flash_sale_batch_get_items"

# User-agent e headers p/ reduzir bloqueio
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://shopee.com.br/",
}


# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("ofertas-bot")


# =========================
# UTILS
# =========================

def format_currency_br(value: float) -> str:
    try:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"R$ {value:.2f}"

def pct_discount(original: float, price: float) -> Optional[int]:
    try:
        if original and original > price:
            return int(round((1 - (price / original)) * 100))
    except Exception:
        pass
    return None

def make_meli_affiliate(product_url: str) -> str:
    """
    Tenta envolver o link do produto com a etiqueta /sec/ do Mercado Livre.
    Muitos parceiros conseguem usar: https://mercadolivre.com/sec/<ETIQUETA>?url=<encoded>
    Se o seu painel exigir outro padrão, ajuste aqui.
    """
    from urllib.parse import quote
    encoded = quote(product_url, safe="")
    return f"https://mercadolivre.com/sec/{MELI_AFFIL_LABEL}?url={encoded}"

def make_shopee_affiliate(product_url: str) -> str:
    """
    Placeholder: hoje a Shopee não expõe um encurtador de afiliado programável público e estável.
    Envia o link direto. Quando você tiver um encurtador que aceite ?url= (ou similar),
    ajuste aqui de forma análoga ao MELI.
    """
    return product_url


# =========================
# BUSCA DE OFERTAS: SHOPEE
# =========================

async def fetch_shopee_flash(session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Busca itens de Flash Sale da Shopee (quando disponível)."""
    params = {"limit": 20, "need_personalize": 1, "with_dp_items": 1}
    try:
        async with session.get(SHOPEE_FLASH_URL, params=params, headers=DEFAULT_HEADERS, timeout=20) as r:
            if r.status != 200:
                log.warning("Shopee FlashSale HTTP %s", r.status)
                return []
            data = await r.json()
            items = []
            for batch in data.get("data", {}).get("items", []):
                for it in batch.get("items", []):
                    items.append(it)
            return items
    except Exception as e:
        log.warning("Shopee FlashSale falhou: %s", e)
        return []

async def fetch_shopee_search(session: aiohttp.ClientSession, keyword: str) -> List[Dict[str, Any]]:
    """Busca itens por palavra-chave na Shopee (ordenando por popularidade)."""
    params = {
        "by": "pop",
        "keyword": keyword,
        "limit": 30,
        "newest": 0,
        "order": "desc",
        "page_type": "search",
        "scenario": "PAGE_GLOBAL_SEARCH",
        "version": 2,
    }
    try:
        async with session.get(SHOPEE_SEARCH_URL, params=params, headers=DEFAULT_HEADERS, timeout=20) as r:
            if r.status != 200:
                log.warning("Shopee Search HTTP %s (%s)", r.status, keyword)
                return []
            data = await r.json()
            return data.get("items", [])
    except Exception as e:
        log.warning("Shopee Search falhou (%s): %s", keyword, e)
        return []

def normalize_shopee_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Converte o item da Shopee para um dicionário padrão de oferta."""
    try:
        # Estrutura difere entre flash_sale e search; lidamos com ambos
        if "item_basic" in item:  # search
            ib = item["item_basic"]
            shopid = ib["shopid"]; itemid = ib["itemid"]
            title = ib.get("name", "").strip()
            price = ib.get("price", 0) / 100000  # Shopee multiplica por 100000
            price_before = ib.get("price_before_discount", 0) / 100000 if ib.get("price_before_discount") else 0
            image = ib.get("image")
        else:  # flash_sale
            shopid = item["shopid"]; itemid = item["itemid"]
            title = item.get("name", "").strip()
            price = item.get("price", 0) / 100000
            price_before = item.get("price_before_discount", 0) / 100000
            image = item.get("image")

        url = f"https://shopee.com.br/product/{shopid}/{itemid}"
        img = f"https://cf.shopee.com.br/file/{image}" if image else None
        off = pct_discount(price_before, price) if price_before else None

        return {
            "title": title,
            "price": price,
            "original": price_before or None,
            "discount_pct": off,
            "url": make_shopee_affiliate(url),
            "image": img,
            "source": "Shopee",
        }
    except Exception as e:
        log.debug("normalize_shopee_item erro: %s", e)
        return None


# =========================
# BUSCA DE OFERTAS: MERCADO LIVRE
# =========================

ML_SEARCH_URL = "https://api.mercadolibre.com/sites/MLB/search"

async def fetch_meli_search(session: aiohttp.ClientSession, keyword: str) -> List[Dict[str, Any]]:
    params = {"q": keyword, "limit": 30, "sort": "relevance"}
    try:
        async with session.get(ML_SEARCH_URL, params=params, timeout=20) as r:
            if r.status != 200:
                log.warning("MELI Search HTTP %s (%s)", r.status, keyword)
                return []
            data = await r.json()
            return data.get("results", [])
    except Exception as e:
        log.warning("MELI Search falhou (%s): %s", keyword, e)
        return []

def normalize_meli_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        title = item.get("title", "").strip()
        price = float(item.get("price", 0))
        original = None
        # o campo "original_price" aparece quando há desconto
        if item.get("original_price"):
            original = float(item["original_price"])
        off = pct_discount(original, price) if original else None

        permalink = item.get("permalink")
        img = None
        if item.get("thumbnail"):
            img = item["thumbnail"].replace("I.jpg", "O.jpg")  # maior
        aff = make_meli_affiliate(permalink) if permalink else None

        return {
            "title": title,
            "price": price,
            "original": original,
            "discount_pct": off,
            "url": aff or permalink,
            "image": img,
            "source": "Mercado Livre",
        }
    except Exception as e:
        log.debug("normalize_meli_item erro: %s", e)
        return None


# =========================
# POSTAGEM
# =========================

async def pick_offer(session: aiohttp.ClientSession, source_toggle: str, categories: List[str]) -> Optional[Dict[str, Any]]:
    """
    source_toggle: 'shopee' ou 'meli'
    Tenta cada categoria até achar uma oferta válida.
    """
    if source_toggle == "shopee":
        # 1) tenta Flash Sale
        items = await fetch_shopee_flash(session)
        for it in items:
            offer = normalize_shopee_item(it)
            if offer:
                return offer
        # 2) busca por categoria
        for kw in categories:
            raw = await fetch_shopee_search(session, kw)
            for it in raw:
                offer = normalize_shopee_item(it)
                if offer:
                    return offer
        return None

    # meli
    for kw in categories:
        raw = await fetch_meli_search(session, kw)
        for it in raw:
            offer = normalize_meli_item(it)
            if offer:
                return offer
    return None


async def post_offer(context: ContextTypes.DEFAULT_TYPE, offer: Dict[str, Any]) -> None:
    title = offer["title"]
    price = format_currency_br(offer["price"])
    original = offer.get("original")
    off = offer.get("discount_pct")
    url = offer["url"]
    src = offer["source"]
    img = offer.get("image")

    lines = [f"*{title}*"]
    if off:
        lines.append(f"💸 *{price}*  _(−{off}% vs. preço de referência)_")
    else:
        lines.append(f"💸 *{price}*")
    if original:
        lines.append(f"~~{format_currency_br(original)}~~")
    lines.append(f"🛍️ {src}")

    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Ver oferta 🔗", url=url)]]
    )

    try:
        if img:
            await context.bot.send_photo(
                chat_id=TARGET_CHAT_ID,
                photo=img,
                caption=text,
                reply_markup=kb,
                parse_mode="Markdown",
            )
        else:
            await context.bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=text,
                reply_markup=kb,
                parse_mode="Markdown",
            )
    except Exception as e:
        log.error("Falha ao enviar mensagem: %s", e)


# =========================
# JOB: alternância Shopee ↔ MELI
# =========================

async def posting_job(context: ContextTypes.DEFAULT_TYPE):
    # alterna em memória (context.application.chat_data não existe aqui; usamos bot_data)
    toggle = context.bot_data.get("toggle_source", "shopee")
    next_toggle = "meli" if toggle == "shopee" else "shopee"
    context.bot_data["toggle_source"] = next_toggle

    async with aiohttp.ClientSession() as session:
        log.info("🔎 Buscando oferta (%s)...", toggle.upper())
        offer = await pick_offer(session, toggle, CATEGORIES)
        if not offer:
            # se não achou nessa fonte, tenta a outra imediatamente
            log.info("Nenhuma oferta em %s. Tentando %s...", toggle, next_toggle)
            offer = await pick_offer(session, next_toggle, CATEGORIES)

        if offer:
            await post_offer(context, offer)
        else:
            log.warning("❌ Nenhuma oferta encontrada em nenhuma fonte no ciclo.")


# =========================
# COMANDOS
# =========================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! Use /start_posting para começar a postar ofertas e /stop_posting para parar.\n"
        "Categorias: " + ", ".join(CATEGORIES)
    )

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # evita jobs duplicados
    job_id = f"posting-{TARGET_CHAT_ID}"
    existing = context.job_queue.get_jobs_by_name(job_id)
    for j in existing:
        j.schedule_removal()

    context.bot_data["toggle_source"] = "shopee"  # começa pela Shopee
    context.job_queue.run_repeating(
        posting_job,
        interval=POST_INTERVAL_MINUTES * 60,
        first=5,  # primeira execução em 5s
        name=job_id,
    )
    await update.message.reply_text("✅ Postagens automáticas iniciadas (1 oferta a cada 2 minutos).")

async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    job_id = f"posting-{TARGET_CHAT_ID}"
    existing = context.job_queue.get_jobs_by_name(job_id)
    if not existing:
        await update.message.reply_text("ℹ️ Não havia postagens ativas.")
        return
    for j in existing:
        j.schedule_removal()
    await update.message.reply_text("🛑 Postagens automáticas paradas.")


# =========================
# MAIN (webhook nativo PTB)
# =========================

async def main():
    if not BOT_TOKEN:
        log.error("BOT_TOKEN não definido.")
        return

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .rate_limiter(AIORateLimiter())
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("start_posting", cmd_start_posting))
    application.add_handler(CommandHandler("stop_posting", cmd_stop_posting))

    # Webhook nativo do PTB — NÃO fecha o event loop manualmente
    if WEBHOOK_URL:
        log.info("🚀 Subindo via webhook: %s", WEBHOOK_URL)
        # Remove o webhook anterior e configura o atual
        await application.bot.delete_webhook(drop_pending_updates=True)
        await application.bot.set_webhook(url=WEBHOOK_URL, allowed_updates=None)

        # Importante: run_webhook cuida do loop; não chame asyncio.run dentro dele
        await application.run_webhook(
            listen=LISTEN_ADDR,
            port=PORT,
            webhook_url=WEBHOOK_URL,
        )
    else:
        log.info("▶️ Sem WEBHOOK_URL — executando via polling.")
        await application.run_polling(allowed_updates=None, close_loop=False)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
