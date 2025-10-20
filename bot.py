import os
import re
import logging
import asyncio
from typing import List, Dict
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
from playwright.async_api import async_playwright
import aiohttp

# =============== CONFIG ===============
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "").strip()
SHORTENER_API = os.getenv("SHORTENER_API", "https://tinyurl.com/api-create.php?url=")
PORT = int(os.getenv("PORT", 8080))
RAILWAY_URL = os.getenv("RAILWAY_URL", "").rstrip("/")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

CATEGORIES_ENABLED = {
    "eletronicos": True,
    "eletrodomesticos": True,
    "ferramentas": True,
    "pecas_pc": True,
    "notebooks": True,
}

KEYWORDS = {
    "eletronicos": ["eletrôn", "smart", "tv", "monitor", "fone", "soundbar", "bluetooth"],
    "eletrodomesticos": ["geladeira", "microondas", "lava", "aspirador", "air fryer", "cafeteira"],
    "ferramentas": ["furadeira", "serra", "parafusadeira", "chave", "compressor", "multímetro"],
    "pecas_pc": ["ssd", "placa-mãe", "processador", "ryzen", "intel", "memória", "gpu", "rtx"],
    "notebooks": ["notebook", "laptop", "macbook", "chromebook"],
}

CATEGORY_REGEX = {
    cat: re.compile("|".join(re.escape(k) for k in kws), flags=re.I)
    for cat, kws in KEYWORDS.items()
}

# =============== FUNÇÕES AUXILIARES ===============

def titulo_bate_categoria(titulo: str) -> bool:
    for cat, ativo in CATEGORIES_ENABLED.items():
        if ativo and CATEGORY_REGEX[cat].search(titulo.lower()):
            return True
    return False

def anexar_afiliado(url: str) -> str:
    if not AFFILIATE_TAG:
        return url
    sep = "&" if "?" in url else "?"
    if "tag=" not in url:
        url += f"{sep}tag={AFFILIATE_TAG}"
    return url

async def encurtar_link(url: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SHORTENER_API}{url}") as resp:
                if resp.status == 200:
                    text = await resp.text()
                    if text.startswith("http"):
                        return text
    except:
        pass
    return url

async def buscar_ofertas_filtradas(limit: int = 6) -> List[Dict]:
    url = "https://www.amazon.com.br/gp/goldbox"
    resultados = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_selector("div.DealCard, div[data-testid='deal-card']", timeout=60000)

        cards = await page.query_selector_all("div.DealCard, div[data-testid='deal-card']")
        for card in cards:
            title_el = await card.query_selector("span.a-text-normal")
            price_el = await card.query_selector("span.a-price-whole")
            link_el = await card.query_selector("a.a-link-normal")

            if not title_el or not link_el:
                continue

            title = (await title_el.inner_text()).strip()
            if not titulo_bate_categoria(title):
                continue

            href = await link_el.get_attribute("href")
            if not href.startswith("http"):
                href = "https://www.amazon.com.br" + href

            href = await encurtar_link(anexar_afiliado(href))
            price = (await price_el.inner_text()).strip() if price_el else "Preço não informado"

            resultados.append({"titulo": title, "preco": price, "link": href})
            if len(resultados) >= limit:
                break

        await browser.close()
    return resultados

# =============== COMANDOS ===============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou o bot de ofertas da Amazon!\n"
        "🚀 Usando webhook no Railway.\n\n"
        "Comandos disponíveis:\n"
        "/start_posting - começar postagens automáticas\n"
        "/stop_posting - parar postagens"
    )

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    context.job_queue.run_repeating(postar_ofertas, interval=180, first=5, chat_id=chat_id, name=f"posting-{chat_id}")
    await update.message.reply_text("🚀 Comecei a postar ofertas automaticamente!")

async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(f"posting-{chat_id}")
    for j in jobs:
        j.schedule_removal()
    await update.message.reply_text("🛑 Postagens automáticas paradas.")

async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    ofertas = await buscar_ofertas_filtradas(limit=4)
    if not ofertas:
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Nenhuma oferta encontrada no momento.")
        return

    for o in ofertas:
        msg = f"📦 *{o['titulo']}*\n💰 {o['preco']}\n🔗 [Ver oferta]({o['link']})"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        await asyncio.sleep(2)

# =============== MAIN (WEBHOOK) ===============

async def handle_update(request):
    """Rota do webhook: recebe as mensagens do Telegram."""
    try:
        data = await request.json()
        update = Update.de_json(data, request.app["bot"])
        await request.app["application"].process_update(update)
        return web.Response(text="ok")
    except Exception as e:
        logging.error(f"Erro no webhook: {e}")
        return web.Response(status=500, text="error")

async def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))
    application.add_handler(CommandHandler("stop_posting", stop_posting))

    # Configura o webhook no Telegram
    webhook_path = f"/webhook/{BOT_TOKEN}"
    webhook_url = f"{RAILWAY_URL}{webhook_path}"
    await application.bot.set_webhook(url=webhook_url)
    logging.info(f"🌐 Webhook configurado em: {webhook_url}")

    # Servidor aiohttp para o Railway
    app = web.Application()
    app["bot"] = application.bot
    app["application"] = application
    app.router.add_post(webhook_path, handle_update)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logging.info(f"✅ Bot rodando com webhook na porta {PORT}")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
