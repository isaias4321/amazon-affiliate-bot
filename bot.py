#!/usr/bin/env python3
"""
bot.py — Telegram affiliate deals bot (webhook + scheduler)
- Webhook (aiohttp) para evitar conflitos de polling
- Scheduler assíncrono que posta ofertas a cada INTERVAL_MIN minutos (exato)
- Filtra apenas produtos com desconto nas categorias desejadas
- Mostra % OFF e adiciona tag de afiliado automaticamente
- Banco SQLite para evitar repostagens

Configure no Railway:
  BOT_TOKEN  -> token do BotFather
  (opcional) AFFILIATE_TAG -> isaias06f-20
  (opcional) INTERVAL_MIN -> 5
  PORT -> Railway fornece automaticamente (o código usa PORT ou 8080)
  WEBHOOK_BASE_URL -> URL pública do seu projeto (ex: https://meu-bot.up.railway.app)
Se preferir usar as constantes fixas, o código já vem com os valores que você passou.
"""

from __future__ import annotations
import os
import time
import asyncio
import logging
import sqlite3
import re
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
from aiohttp import web
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------------- CONFIGURAÇÕES ----------------
# Você informou: chat_id -4983279500 e uma URL Railway.
# Se preferir, substitua os valores abaixo por os.getenv(...) no Railway.
BOT_TOKEN = os.getenv("BOT_TOKEN")  # obrigatória nas variáveis do Railway
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", "5"))
PORT = int(os.getenv("PORT", "8080"))
# WEBHOOK_BASE_URL deve ser a URL pública que aponta para seu serviço Railway (sem /webhook)
# Você forneceu um link do painel; se não for o público use a URL pública que aparece no "Live" do Railway.
WEBHOOK_BASE_URL = os.getenv(
    "WEBHOOK_BASE_URL",
    "https://railway.com/project/5dddd7b1-5efb-47a2-9bc9-7731445131d6/service/8b4d56a4-8ef6-49dc-b5ca-7a150a9663bd"
)
# Chat id onde postar (você passou -4983279500)
GROUP_ID = os.getenv("GROUP_ID", "-4983279500")

# Amazon Goldbox (ofertas)
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

# Limites e politeness
MAX_PRODUCTS_PER_ROUND = 6
REQUEST_DELAY = 0.9  # segundos entre requisições de produto (educado)
REQUEST_TIMEOUT = 12

# Palavras-chave para filtrar games + eletrônicos
CATEGORY_KEYWORDS = [
    "game", "games", "videogame", "console", "ps5", "ps4", "xbox", "nintendo", "switch",
    "eletrônico", "eletronico", "eletrônicos", "eletronicos", "celular", "notebook",
    "fone", "headphone", "audio", "tv", "smartphone", "tablet", "monitor", "ssd", "hd", "controle",
]

# ---------------- LOGGING ----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("amazon-deals-bot")

# ---------------- BANCO (SQLite) ----------------
DB_PATH = os.getenv("DB_PATH", "offers.db")
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = conn.cursor()
cur.execute('''
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE,
    title TEXT,
    image TEXT,
    price_original TEXT,
    price_deal TEXT,
    discount_percent INTEGER,
    added_at TEXT DEFAULT (datetime('now'))
)
''')
conn.commit()
db_lock = asyncio.Lock()

# ---------------- HELPERS HTTP / PARSE ----------------
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def safe_get_text_sync(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """Versão síncrona para baixar HTML (usada em threads)."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.debug("Erro HTTP (sync) %s: %s", url, e)
        return None


def parse_price_str(price_str: str) -> Optional[float]:
    """Converte 'R$ 1.234,56' para float 1234.56. Retorna None se falhar."""
    if not price_str:
        return None
    s = price_str.strip()
    s = s.replace("R$", "").replace("R", "").replace(".", "").replace(" ", "").replace(",", ".")
    try:
        return float(re.findall(r"\d+(\.\d+)?", s)[0])
    except Exception:
        try:
            return float(s)
        except Exception:
            return None


def parse_product_page(html: str, url: str) -> Dict:
    """Extrai título, imagem, preço atual, preço original e breadcrumb da página do produto."""
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find(id="productTitle") or soup.select_one(".a-size-large.product-title-word-break")
    title = title_tag.get_text(strip=True) if title_tag else ""

    # imagem
    img_tag = soup.find(id="landingImage") or soup.select_one("#imgTagWrapperId img") or soup.select_one("img[data-old-hires]")
    image = ""
    if img_tag:
        image = img_tag.get("src") or img_tag.get("data-old-hires") or ""

    # preço (várias possibilidades)
    price_deal = ""
    for pid in ("priceblock_dealprice", "priceblock_ourprice", "priceblock_saleprice"):
        p = soup.find(id=pid)
        if p and p.get_text(strip=True):
            price_deal = p.get_text(strip=True)
            break
    if not price_deal:
        p = soup.select_one("span.a-price > span.a-offscreen")
        if p:
            price_deal = p.get_text(strip=True)

    # preço original (strike)
    price_original = ""
    strike = soup.select_one("span.priceBlockStrikePriceString, span.a-text-strike")
    if strike:
        price_original = strike.get_text(strip=True)
    else:
        # fallback: verificar se existe "De R$"
        possible = soup.select_one("span.a-size-base.a-color-secondary")
        if possible and "De R$" in possible.get_text():
            price_original = possible.get_text(strip=True)

    # breadcrumb
    breadcrumb_nodes = soup.select("#wayfinding-breadcrumbs_container a")
    breadcrumb = " ".join([n.get_text(strip=True) for n in breadcrumb_nodes]) if breadcrumb_nodes else ""

    return {
        "title": title,
        "image": image,
        "price_deal": price_deal,
        "price_original": price_original,
        "breadcrumb": breadcrumb,
        "url": url,
    }


# ---------------- RASPAGEM PRINCIPAL (blocking) ----------------
def fetch_promotions_blocking(limit: int = MAX_PRODUCTS_PER_ROUND) -> List[Dict]:
    """
    1) Acessa Amazon Goldbox
    2) Coleta links candidatos (/dp/ e /gp/)
    3) Visita cada produto (com delay educado)
    4) Filtra apenas categorias desejadas
    5) Mantém só produtos com desconto (price_original > price_deal)
    """
    html = safe_get_text_sync(URL_AMAZON_GOLDBOX)
    if not html:
        logger.warning("Não foi possível acessar a página de ofertas da Amazon.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select("a[href*='/dp/'], a[href*='/gp/']")
    seen = set()
    promotions = []

    # varrer anchors (em ordem encontrada)
    for a in anchors:
        href = a.get("href")
        if not href:
            continue

        # normalizar URL
        if href.startswith("/"):
            prod_url = "https://www.amazon.com.br" + href.split("?")[0]
        else:
            prod_url = href.split("?")[0]

        if prod_url in seen:
            continue
        seen.add(prod_url)

        # politeness
        time.sleep(REQUEST_DELAY)

        page_html = safe_get_text_sync(prod_url)
        if not page_html:
            continue

        pdata = parse_product_page(page_html, prod_url)

        # validar preços
        price_original_str = pdata.get("price_original") or ""
        price_deal_str = pdata.get("price_deal") or ""
        if not price_original_str or not price_deal_str:
            continue

        old_val = parse_price_str(price_original_str)
        new_val = parse_price_str(price_deal_str)
        if old_val is None or new_val is None:
            continue

        if new_val >= old_val:
            continue  # sem desconto

        discount_percent = round(((old_val - new_val) / old_val) * 100)
        # exigir desconto mínimo (>=5%)
        if discount_percent < 5:
            continue

        # filtrar por categoria (titulo + breadcrumb)
        combined = (pdata.get("title", "") + " " + pdata.get("breadcrumb", "")).lower()
        if not any(kw in combined for kw in CATEGORY_KEYWORDS):
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

    logger.info("fetch_promotions_blocking: %d produtos encontrados com desconto", len(promotions))
    return promotions


def build_affiliate_url(url: str) -> str:
    if "amazon." in url and "tag=" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}tag={AFFILIATE_TAG}"
    return url


# ---------------- POSTAGEM (async) ----------------
async def post_promotions(bot: Bot):
    # executa a raspagem em thread
    promotions = await asyncio.to_thread(fetch_promotions_blocking, MAX_PRODUCTS_PER_ROUND)
    if not promotions:
        logger.info("Nenhuma promoção encontrada nesta rodada.")
        return 0

    posted = 0
    for item in promotions:
        url = item["url"]
        title = item["title"]
        image = item.get("image", "")
        price_original = item.get("price_original", "")
        price_deal = item.get("price_deal", "")
        discount_percent = item.get("discount_percent", 0)
        aff_url = build_affiliate_url(url)

        # evitar repostagem
        async with db_lock:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM offers WHERE url=?", (url,))
            if cur.fetchone():
                logger.debug("Já postado (ignorando): %s", url)
                continue
            cur.execute(
                "INSERT INTO offers (url, title, image, price_original, price_deal, discount_percent) VALUES (?, ?, ?, ?, ?, ?)",
                (url, title, image, price_original, price_deal, discount_percent),
            )
            conn.commit()

        # montar texto: preço + desconto ao lado
        text = f"<b>{title}</b>\n\n💰 {price_deal}"
        if price_original and price_original != price_deal:
            text += f" (antes {price_original})"
        if discount_percent:
            text += f"  🔥 -{discount_percent}% OFF"

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Ver oferta na Amazon", url=aff_url)]])

        try:
            if image:
                await bot.send_photo(chat_id=GROUP_ID, photo=image, caption=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            else:
                await bot.send_message(chat_id=GROUP_ID, text=text, parse_mode=ParseMode.HTML, reply_markup=keyboard)
            posted += 1
            logger.info("Oferta postada: %s", title)
            # breve pausa entre envios para evitar rate limits
            await asyncio.sleep(1.0)
        except Exception as e:
            logger.exception("Erro ao enviar oferta: %s", e)

    # mensagem final informando próxima rodada no grupo
    try:
        await bot.send_message(chat_id=GROUP_ID, text=f"🕒 Próxima rodada em {INTERVAL_MIN} minutos!", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.debug("Falha ao enviar aviso de próxima rodada: %s", e)

    logger.info("Postagens desta rodada: %d", posted)
    return posted


# ---------------- SCHEDULER (async-safe, intervalo exato) ----------------
_SCHEDULER_TASK_KEY = "amazon_scheduler_task"


async def scheduler_loop(application):
    logger.info("Scheduler iniciado (intervalo exato %d minutos).", INTERVAL_MIN)
    try:
        while True:
            start_time = time.time()
            try:
                await post_promotions(application.bot)
            except Exception as e:
                logger.exception("Erro na rodada de postagens: %s", e)
            # tempo gasto na rodada
            elapsed = time.time() - start_time
            delay = max(0, INTERVAL_MIN * 60 - elapsed)
            # log amigável do tempo restante
            mins = int(delay) // 60
            secs = int(delay) % 60
            logger.info("💤 Próxima rodada em %02d:%02d (MM:SS)", mins, secs)
            await asyncio.sleep(delay)
    except asyncio.CancelledError:
        logger.info("Scheduler cancelado.")
        raise


async def start_scheduler(application) -> str:
    if _SCHEDULER_TASK_KEY in application.bot_data:
        logger.info("Scheduler já rodando.")
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


# ---------------- TELEGRAM COMMANDS ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot ativo. Use /start_posting para ligar postagens automáticas.")


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
    await update.message.reply_text("📤 Post manual finalizado.")


# ---------------- AIOHTTP WEBHOOK SERVER ----------------
# Endpoint /webhook será usado pelo Telegram para entregar updates
async def handle_webhook(request: web.Request) -> web.Response:
    """
    Recebe payload JSON do Telegram e processa a update com a Application.
    O objeto Application está guardado em request.app['telegram_application'] (set no main).
    """
    app: "telegram.ext.Application" = request.app["telegram_application"]
    try:
        data = await request.json()
    except Exception:
        return web.Response(status=400, text="invalid")
    try:
        update = Update.de_json(data, bot=app.bot)
        # agendar processamento dentro do loop da Application
        await app.process_update(update)
    except Exception as e:
        logger.exception("Erro ao processar update via webhook: %s", e)
        # não falhar o endpoint para que Telegram não considere erro persistente
    return web.Response(text="OK")


# ---------------- START / SHUTDOWN ----------------
async def start_webserver_and_set_webhook(application):
    """
    Inicia o servidor aiohttp e registra o webhook no Telegram.
    Coloca a instância da Application em request.app so handler consiga usar.
    """
    # Rota webhook (path /webhook)
    routes = web.RouteTableDef()

    @routes.post("/webhook")
    async def _webhook(request):
        return await handle_webhook(request)

    web_app = web.Application()
    web_app.add_routes(routes)
    # disponibilizar application dentro do web app (para handle_webhook)
    web_app["telegram_application"] = application

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info("Servidor webhook iniciado no porto %s", PORT)

    # configurar webhook no Telegram
    webhook_url = WEBHOOK_BASE_URL.rstrip("/") + "/webhook"
    try:
        await application.bot.set_webhook(webhook_url)
        logger.info("Webhook configurado: %s", webhook_url)
    except Exception as e:
        logger.exception("Falha ao configurar webhook: %s", e)
        raise

    return runner  # para shutdown se desejado


# ---------------- MAIN (async) ----------------
async def async_main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN não definido nas variáveis de ambiente.")
    logger.info("Inicializando Application (webhook mode)...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers de comando
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("start_posting", cmd_start_posting))
    application.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
    application.add_handler(CommandHandler("postnow", cmd_postnow))

    # start scheduler automaticamente após a Application estar pronta
    async def _on_startup(app_):
        await start_scheduler(app_)
        logger.info("Scheduler iniciado automaticamente no startup.")

    application.post_init = _on_startup

    # inicializar bot (necessário para set_webhook)
    await application.initialize()
    await application.start()  # start the application (connectors etc.)
    # start webhook server and register webhook
    runner = await start_webserver_and_set_webhook(application)

    logger.info("Aplicação pronta. Webhook ativo e scheduler rodando.")
    # manter rodando até sinal de término
    try:
        await asyncio.Event().wait()
    finally:
        # shutdown ordenado
        logger.info("Shutting down: removendo webhook e parando servidor.")
        try:
            await application.bot.delete_webhook()
        except Exception:
            pass
        await application.stop()
        await application.shutdown()
        await runner.cleanup()


def main():
    try:
        asyncio.run(async_main())
    except Exception as e:
        logger.exception("Erro fatal no bot: %s", e)


if __name__ == "__main__":
    main()
