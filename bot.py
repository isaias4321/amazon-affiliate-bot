import os
import asyncio
import logging
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from playwright.async_api import async_playwright

# Configuração do log
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# === CONFIGURAÇÕES DO BOT ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
AFFILIATE_TAG = os.getenv("AMAZON_TAG", "SEU_ID_AFILIADO_AQUI")  # 👈 troque pelo seu ID
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Ex: https://seu-projeto.up.railway.app

scheduler = AsyncIOScheduler()
posting_jobs = {}

# === FASTAPI APP ===
webapp = FastAPI()

# === FUNÇÃO PARA BUSCAR OFERTAS ===
async def buscar_ofertas_filtradas(limit=6):
    categorias = [
        "eletrônicos", "eletrodomésticos", "ferramentas",
        "peças de computadores", "notebooks"
    ]
    categoria = random.choice(categorias)
    url = f"https://www.amazon.com.br/s?k={categoria.replace(' ', '+')}"

    logging.info(f"🔎 Buscando ofertas na categoria: {categoria}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=90000)
        await asyncio.sleep(5)

        # rola a página pra carregar resultados
        for _ in range(3):
            await page.mouse.wheel(0, 3000)
            await asyncio.sleep(2)

        produtos = await page.query_selector_all("div.s-result-item")

        resultados = []
        for produto in produtos[:limit]:
            titulo = await produto.query_selector("h2 a span")
            link = await produto.query_selector("h2 a")

            if titulo and link:
                nome = (await titulo.inner_text()).strip()
                url_produto = (await link.get_attribute("href")).strip()

                if url_produto.startswith("/"):
                    url_produto = "https://www.amazon.com.br" + url_produto
                if "tag=" not in url_produto:
                    separador = "&" if "?" in url_produto else "?"
                    url_produto += f"{separador}tag={AFFILIATE_TAG}"

                resultados.append((nome, url_produto))

        await browser.close()
        logging.info(f"✅ {len(resultados)} produtos encontrados em {categoria}")
        return resultados

# === FUNÇÃO DE POSTAGEM ===
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    ofertas = await buscar_ofertas_filtradas(limit=4)

    if not ofertas:
        await context.bot.send_message(chat_id=chat_id, text="😕 Nenhuma oferta encontrada no momento.")
        return

    for nome, link in ofertas:
        msg = f"🛒 *{nome}*\n👉 [Ver na Amazon]({link})"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        await asyncio.sleep(5)

# === COMANDOS DO BOT ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Use /start_posting para começar a receber ofertas e /stop_posting para parar.")

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in posting_jobs:
        await update.message.reply_text("✅ As postagens já estão ativas!")
        return

    job = scheduler.add_job(postar_ofertas, "interval", minutes=3, args=[context], id=f"posting-{chat_id}")
    job.chat_id = chat_id
    posting_jobs[chat_id] = job
    await update.message.reply_text("🚀 Começando a postar ofertas da Amazon a cada 3 minutos!")

async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    job = posting_jobs.pop(chat_id, None)

    if job:
        job.remove()
        await update.message.reply_text("🛑 Postagens automáticas pausadas.")
    else:
        await update.message.reply_text("ℹ️ Não há postagens ativas para este chat.")

# === CONFIGURAÇÃO DO FASTAPI WEBHOOK ===
@webapp.post("/webhook/{token}")
async def webhook(request: Request, token: str):
    if token != BOT_TOKEN:
        return {"status": "unauthorized"}

    try:
        data = await request.json()
        await app.update_queue.put(data)
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Erro no webhook: {e}")
        return {"status": "error", "detail": str(e)}

# === FUNÇÃO PRINCIPAL ===
async def main():
    global app
    logging.info("🚀 Iniciando bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers de comando
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_posting", start_posting))
    app.add_handler(CommandHandler("stop_posting", stop_posting))

    scheduler.start()

    # Configuração do webhook
    if WEBHOOK_URL:
        webhook_path = f"/webhook/{BOT_TOKEN}"
        webhook_full_url = f"{WEBHOOK_URL}{webhook_path}"

        await app.bot.delete_webhook()
        await app.bot.set_webhook(webhook_full_url)
        logging.info(f"🌐 Webhook configurado em: {webhook_full_url}")

        # Inicia FastAPI com Uvicorn
        import uvicorn
        uvicorn.run(webapp, host="0.0.0.0", port=PORT)
    else:
        logging.info("🤖 Rodando em modo polling local")
        await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
