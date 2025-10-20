import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from playwright.async_api import async_playwright

# === CONFIGURAÇÃO DE LOG ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === VARIÁVEIS DE AMBIENTE ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("BOT_TOKEN e GROUP_ID precisam estar definidos no .env")

URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

# === FUNÇÃO PARA BUSCAR PROMOÇÕES ===
async def fetch_promotions_playwright():
    logging.info("🕵️ Acessando Amazon Goldbox com Playwright...")
    promotions = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(URL_AMAZON_GOLDBOX, timeout=60000)
            await page.wait_for_selector('div[data-asin]', timeout=20000)
            
            items = await page.query_selector_all('div[data-asin]')
            for item in items[:10]:  # limita para não sobrecarregar
                asin = await item.get_attribute('data-asin')
                if not asin:
                    continue
                title_el = await item.query_selector('span.a-text-normal')
                price_el = await item.query_selector('span.a-price-whole')
                link_el = await item.query_selector('a.a-link-normal')

                title = await title_el.inner_text() if title_el else None
                price = await price_el.inner_text() if price_el else None
                link = await link_el.get_attribute('href') if link_el else None

                if title and link:
                    promotions.append({
                        "title": title.strip(),
                        "price": price.strip() if price else "N/A",
                        "url": f"https://www.amazon.com.br{link}"
                    })

            await browser.close()
            logging.info(f"✅ {len(promotions)} promoções encontradas.")
    except Exception as e:
        logging.error(f"❌ Erro ao buscar promoções: {e}")
    return promotions

# === FUNÇÃO PARA POSTAR AS OFERTAS ===
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    logging.info("🔄 Buscando promoções...")
    promotions = await fetch_promotions_playwright()
    if not promotions:
        logging.info("⚠️ Nenhuma promoção válida encontrada.")
        return

    for promo in promotions[:5]:
        msg = f"🔥 *{promo['title']}*\n💰 Preço: R${promo['price']}\n🔗 [Ver na Amazon]({promo['url']})"
        try:
            await context.bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem: {e}")

# === COMANDO /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Olá! Eu sou o bot de ofertas da Amazon.\n"
                                    "Vou enviar automaticamente as melhores promoções aqui!")

# === FUNÇÃO PRINCIPAL ===
async def main():
    logging.info("🚀 Iniciando bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Registrar comando /start
    app.add_handler(CommandHandler("start", start))

    # Agendar job de promoções a cada 60 minutos
    app.job_queue.run_repeating(postar_ofertas, interval=3600, first=5)

    logging.info("✅ Bot iniciado e aguardando mensagens...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())


import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from telegram import Update
from telegram.ext import ContextTypes
import logging
import os

# === CONFIGURAÇÃO DO BOT ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === HANDLERS DE EXEMPLO ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Sou seu bot e estou pronto para te ajudar!")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Envie uma mensagem e eu irei responder!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    await update.message.reply_text(f"Você disse: {texto}")

# === FUNÇÃO PRINCIPAL ===
async def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    # Adiciona comandos e handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logging.info("✅ Bot iniciado e aguardando mensagens...")
    await app.run_polling()

# === CORREÇÃO DO LOOP ASSÍNCRONO ===
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        # Corrige ambiente onde o loop já está ativo (Render/Docker)
        if "already running" in str(e):
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise
