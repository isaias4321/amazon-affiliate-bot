import os
import re
import random
import asyncio
import logging
from typing import Optional, Dict, Any, List

import aiohttp
from telegram import Update, InputMediaPhoto
from telegram.constants import ParseMode
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, ContextTypes
)

# ===================== CONFIG =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
VALUE_SERP_API_KEY = os.getenv("VALUE_SERP_API_KEY", "")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "")  # ex.: seu-20
BASE_URL = os.getenv("BASE_URL", "").rstrip("/")  # ex.: https://seuapp.up.railway.app
PORT = int(os.getenv("PORT", "8080"))

# 1 oferta por ciclo / 3 minutos (ajuste se quiser)
CYCLE_MINUTES = int(os.getenv("CYCLE_MINUTES", "3"))

# categorias fixas pedidas
CATEGORIES = [
    "smartphone Amazon",
    "notebook Amazon",
    "periféricos gamer Amazon",
    "eletrodomésticos Amazon",
    "ferramentas Amazon",
]

# regex pra link amazon /dp/ ou /gp/
AMAZON_LINK_RE = re.compile(r"https?://(?:www\.)?amazon\.com\.br/(?:gp/[^/?#]+|dp/[^/?#]+)[^\s]*", re.IGNORECASE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("dealbot")

# memória simples em runtime
JOBS: Dict[int, str] = {}         # chat_id -> job name
CATEGORY_IDX: Dict[int, int] = {} # chat_id -> qual categoria usar no próximo ciclo


# ===================== HELPERS =====================

def add_affiliate_tag(url: str, tag: str) -> str:
    """Adiciona ?tag= ou &tag= ao link amazon, se não existir."""
    if not tag:
        return url
    if "tag=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}tag={tag}"

def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def br_price_to_float(p: str) -> Optional[float]:
    """Converte 'R$ 1.234,56' -> 1234.56"""
    if not p:
        return None
    txt = p.replace("R$", "").replace(" ", "")
    txt = txt.replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except:
        return None

def build_caption(title: str, price: Optional[str], discount: Optional[str]) -> str:
    parts = [f"*{title}*"]
    if price:
        parts.append(f"💰 Preço: *{price}*")
    if discount:
        parts.append(f"🔻 Desconto: *{discount}*")
    return "\n".join(parts)

async def valueserp_shopping_search(session: aiohttp.ClientSession, query: str) -> Dict[str, Any]:
    """
    Usa o engine Google Shopping do ValueSERP para trazer resultados com preço/imagem.
    Filtra por amazon.com.br no servidor (usando restrições no q e depois no parse).
    """
    params = {
        "api_key": VALUE_SERP_API_KEY,
        "engine": "google_shopping",
        "google_domain": "google.com.br",
        "gl": "br",
        "hl": "pt-br",
        "q": f"{query} site:amazon.com.br",
        "num": 10
    }
    url = "https://api.valueserp.com/search"
    async with session.get(url, params=params, timeout=30) as resp:
        if resp.status != 200:
            raise RuntimeError(f"ValueSERP HTTP {resp.status}")
        return await resp.json()

def pick_amazon_item(shopping_json: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    items: List[Dict[str, Any]] = shopping_json.get("shopping_results", []) or []
    # prioriza fonte amazon e que tenha preço
    amazon_like = [x for x in items if "amazon.com.br" in (x.get("source", "") or "").lower()]
    use_list = amazon_like or items
    if not use_list:
        return None
    # tenta pegar algo com imagem e preço
    use_list = [x for x in use_list if x.get("price")]
    if not use_list:
        return None
    # escolhe um qualquer (poderíamos randomizar)
    return random.choice(use_list)

def extract_price_and_discount(item: Dict[str, Any]) -> (Optional[str], Optional[str]):
    # ValueSERP shopping geralmente traz 'price' (string), 'extracted_price' (float) e às vezes 'extracted_previous_price'
    price_str = item.get("price")
    discount_str = None

    extracted_price = item.get("extracted_price")
    prev = item.get("extracted_previous_price")
    if extracted_price and prev and prev > extracted_price:
        # calcula % off
        off = int(round(100 * (prev - extracted_price) / prev))
        discount_str = f"-{off}%"

    return price_str, discount_str

def ensure_amazon_link(item: Dict[str, Any]) -> Optional[str]:
    # shopping result costuma ter 'link' final (às vezes é tracking do Google)
    link = item.get("link") or ""
    m = AMAZON_LINK_RE.search(link)
    if m:
        return m.group(0)
    # fallback: se não achou, retorna o link mesmo assim (às vezes já é direto)
    return link or None


# ===================== TELEGRAM HANDLERS =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Use:\n"
        "/start_posting – começar a postar 1 oferta a cada ciclo\n"
        "/stop_posting – parar de postar\n"
        "/status – ver status do job atual\n\n"
        f"Categorias: {', '.join(CATEGORIES)}\n"
        f"Ciclo: {CYCLE_MINUTES} min\n"
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    job_name = JOBS.get(chat_id)
    idx = CATEGORY_IDX.get(chat_id, 0)
    if job_name:
        await update.message.reply_text(
            f"✅ Postando a cada {CYCLE_MINUTES} min.\n"
            f"Próxima categoria: {CATEGORIES[idx % len(CATEGORIES)]}\n"
            f"Job: {job_name}"
        )
    else:
        await update.message.reply_text("⏸️ Nenhum job ativo neste chat. Use /start_posting")

async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    job_name = JOBS.pop(chat_id, None)
    if job_name:
        context.application.job_queue.get_jobs_by_name(job_name)
        for j in context.application.job_queue.get_jobs_by_name(job_name):
            j.schedule_removal()
        await update.message.reply_text("🛑 Job parado.")
    else:
        await update.message.reply_text("⚠️ Não havia job ativo.")

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not VALUE_SERP_API_KEY:
        await update.message.reply_text("❌ Configure VALUE_SERP_API_KEY para buscar ofertas.")
        return

    chat_id = update.effective_chat.id
    # se já existe, apaga
    old_name = JOBS.get(chat_id)
    if old_name:
        for j in context.application.job_queue.get_jobs_by_name(old_name):
            j.schedule_removal()

    # reseta o índice de categoria se nunca usado
    CATEGORY_IDX.setdefault(chat_id, 0)

    job_name = f"posting-{chat_id}"
    context.application.job_queue.run_repeating(
        callback=postar_oferta_uma_unidade,
        interval=CYCLE_MINUTES * 60,
        first=5,  # primeiro disparo em 5s
        name=job_name,
        data={"chat_id": chat_id},
    )
    JOBS[chat_id] = job_name
    await update.message.reply_text(
        f"✅ Começando a postar 1 oferta a cada {CYCLE_MINUTES} min.\n"
        f"Categorias em rotação: {', '.join(CATEGORIES)}"
    )

async def postar_oferta_uma_unidade(context: ContextTypes.DEFAULT_TYPE):
    """JobQueue callback: posta exatamente 1 oferta por ciclo."""
    data = context.job.data or {}
    chat_id: int = data.get("chat_id")
    if not chat_id:
        logger.error("Job sem chat_id no data.")
        return

    idx = CATEGORY_IDX.get(chat_id, 0)
    query = CATEGORIES[idx % len(CATEGORIES)]
    CATEGORY_IDX[chat_id] = (idx + 1) % len(CATEGORIES)

    try:
        async with aiohttp.ClientSession() as session:
            js = await valueserp_shopping_search(session, query)
            item = pick_amazon_item(js)
            if not item:
                await context.bot.send_message(chat_id, text=f"⚠️ Não achei ofertas para: {query}")
                return

            title = clean_text(item.get("title"))
            price_str, discount_str = extract_price_and_discount(item)
            link = ensure_amazon_link(item)
            if not link:
                await context.bot.send_message(chat_id, text=f"⚠️ Sem link válido para: {title}")
                return

            link = add_affiliate_tag(link, AFFILIATE_TAG)

            # imagem
            img = item.get("thumbnail") or item.get("image")
            caption = build_caption(title, price_str, discount_str) + f"\n\n➡️ {link}"

            if img:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=img,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                # sem imagem, manda só texto
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=caption,
                    parse_mode=ParseMode.MARKDOWN
                )

            logger.info(f"Oferta enviada ao chat {chat_id}: {title}")

    except Exception as e:
        logger.exception("Falha ao buscar/postar oferta: %s", e)
        await context.bot.send_message(chat_id, text=f"❌ Erro ao buscar oferta: {e}")

# ===================== WEBHOOK (Railway) =====================

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("Defina BOT_TOKEN")
    if not BASE_URL:
        raise RuntimeError("Defina BASE_URL (ex.: https://seuapp.up.railway.app)")

    application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    # comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_cmd))
    application.add_handler(CommandHandler("start_posting", start_posting))
    application.add_handler(CommandHandler("stop_posting", stop_posting))

    # IMPORTANTE: use o servidor de webhook nativo do PTB (sem uvicorn)
    # Ele inicializa, seta webhook e escuta a porta do Railway.
    webhook_path = f"/webhook/{BOT_TOKEN}"
    webhook_url = f"{BASE_URL}{webhook_path}"

    logger.info("🚀 Iniciando bot (webhook nativo PTB) ...")
    await application.initialize()
    await application.bot.delete_webhook(drop_pending_updates=True)
    await application.start()

    # seta webhook apontando pro Railway
    await application.bot.set_webhook(url=webhook_url)

    logger.info(f"🌐 Webhook configurado em: {webhook_url}")
    # inicia o servidor HTTP interno do PTB (aiohttp) e mantém rodando
    await application.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,
    )

    # bloqueia até CTRL+C / container stop
    await application.updater.wait_until_closed()

if __name__ == "__main__":
    # executa a main async sem conflitar com outros loops
    asyncio.run(main())
