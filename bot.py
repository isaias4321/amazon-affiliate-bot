import os
import asyncio
import logging
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from playwright.async_api import async_playwright
import uvicorn

# ===== CONFIGURAÇÕES =====
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN")
AFFILIATE_TAG = os.getenv("AMAZON_TAG", "SEU_ID_AFILIADO_AQUI")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Exemplo: https://seuapp.up.railway.app

webapp = FastAPI()
scheduler = AsyncIOScheduler()
posting_jobs = {}

# ===== FUNÇÃO PARA BUSCAR OFERTAS =====
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

        for _ in range(3):  # scroll para carregar mais resultados
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

# ===== POSTAGEM AUTOMÁTICA =====
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.args[0]  # obtém o chat_id passado no job
    ofertas = await buscar_ofertas_filtradas(limit=4)

    if not ofertas:
        await context.bot.send_message(chat_id=chat_id, text="😕 Nenhuma oferta encontrada no momento.")
        return

    await context.bot.send_message(chat_id=chat_id, text="🔄 Buscando novas ofertas...")

    for nome, link in ofertas:
        msg = f"🛒 *{nome}*\n👉 [Ver na Amazon]({link})"
        await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
        logging.info(f"📤 Enviado: {nome} → {link}")
        await asyncio.sleep(5)

# ===== COMANDOS DO BOT =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Use /start_posting para começar e /stop_posting para parar.")

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    job_id = f"posting-{chat_id}"

    existing_job = scheduler.get_job(job_id)
    if existing_job:
        scheduler.remove_job(job_id)
        logging.info(f"🧹 Job antigo removido ({job_id})")

    job = scheduler.add_job(postar_ofertas, "interval", minutes=3, args=[chat_id], id=job_id)
    posting_jobs[chat_id] = job

    await update.message.reply_text("🚀 Postagens automáticas iniciadas!")
    logging.info(f"✅ Novo job de postagem criado para o chat {chat_id}")

async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    job_id = f"posting-{chat_id}"

    existing_job = scheduler.get_job(job_id)
    if existing_job:
        scheduler.remove_job(job_id)
        posting_jobs.pop(chat_id, None)
        await update.message.reply_text("🛑 Postagens automáticas pausadas.")
        logging.info(f"🧩 Job removido ({job_id})")
    else:
        await update.message.reply_text("ℹ️ Nenhuma postagem ativa no momento.")

# ===== WEBHOOK FASTAPI =====
@webapp.post("/webhook/{token}")
async def webhook(request: Request, token: str):
    if token != BOT_TOKEN:
        return {"status": "unauthorized"}

    try:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        logging.error(f"Erro no webhook: {e}")
        return {"status": "error", "detail": str(e)}

# ===== INICIALIZAÇÃO =====
async def main():
    global app
    logging.info("🚀 Iniciando bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_posting", start_posting))
    app.add_handler(CommandHandler("stop_posting", stop_posting))

    scheduler.start()

    await app.initialize()
    await app.start()

    if WEBHOOK_URL:
        webhook_path = f"/webhook/{BOT_TOKEN}"
        webhook_full_url = f"{WEBHOOK_URL}{webhook_path}"

        await app.bot.delete_webhook()
        await app.bot.set_webhook(webhook_full_url)
        logging.info(f"🌐 Webhook configurado em: {webhook_full_url}")

        config = uvicorn.Config(webapp, host="0.0.0.0", port=PORT, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

        await app.stop()
        await app.shutdown()
    else:
        logging.info("🤖 Rodando em modo polling local...")
        await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
