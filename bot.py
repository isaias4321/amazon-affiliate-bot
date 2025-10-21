import os
import asyncio
import logging
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from playwright.async_api import async_playwright

# --------------------------
# 🔧 CONFIGURAÇÕES INICIAIS
# --------------------------
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = f"https://{os.getenv('RAILWAY_STATIC_URL')}/webhook/{BOT_TOKEN}"

app = Application.builder().token(BOT_TOKEN).build()
scheduler = AsyncIOScheduler()
webapp = FastAPI()

# --------------------------------
# 🔍 BUSCAR OFERTAS NA AMAZON
# --------------------------------
async def buscar_ofertas_filtradas(limit=4):
    categorias = [
        "eletronicos", "eletrodomesticos",
        "ferramentas", "pecas-de-computador", "notebooks"
    ]

    ofertas = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            for categoria in categorias:
                url = f"https://www.amazon.com.br/s?k={categoria}&s=featured-rank"
                logging.info(f"🔎 Buscando ofertas na categoria: {categoria}")
                await page.goto(url, timeout=90000)
                await page.wait_for_selector("div.s-main-slot", timeout=60000)
                await asyncio.sleep(3)

                produtos = await page.query_selector_all("div.s-result-item[data-asin]")
                logging.info(f"✅ {len(produtos)} produtos encontrados em {categoria}")

                for produto in produtos[:limit]:
                    nome = await produto.inner_text()
                    asin = await produto.get_attribute("data-asin")
                    if asin:
                        link = f"https://www.amazon.com.br/dp/{asin}?tag=seuIDAfiliado-20"
                        ofertas.append((nome[:120], link))

            await browser.close()

    except Exception as e:
        logging.error(f"❌ Erro ao buscar ofertas: {e}")

    return ofertas


# --------------------------------
# 🤖 FUNÇÃO DE POSTAGEM
# --------------------------------
async def postar_ofertas(chat_id: int):
    try:
        logging.info(f"🚀 Iniciando ciclo de postagem para o chat {chat_id}")
        ofertas = await buscar_ofertas_filtradas(limit=4)

        if not ofertas or len(ofertas) == 0:
            logging.warning("⚠️ Nenhuma oferta encontrada.")
            await app.bot.send_message(chat_id=chat_id, text="😕 Nenhuma oferta encontrada no momento.")
            return

        await app.bot.send_message(chat_id=chat_id, text=f"🔄 {len(ofertas)} novas ofertas encontradas! Publicando...")

        for nome, link in ofertas:
            msg = f"🛒 *{nome}*\n👉 [Ver na Amazon]({link})"
            await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            logging.info(f"📤 Enviado: {nome} → {link}")
            await asyncio.sleep(5)

        logging.info(f"✅ Ciclo de postagem finalizado para o chat {chat_id}")

    except Exception as e:
        logging.error(f"❌ Erro ao postar ofertas: {e}")
        await app.bot.send_message(chat_id=chat_id, text=f"❌ Erro ao buscar ofertas: {e}")


# --------------------------------
# ⚙️ COMANDOS DO TELEGRAM
# --------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Sou seu bot de ofertas da Amazon. Use /start_posting para começar as postagens automáticas.")

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    existing_job = scheduler.get_job(f"posting-{chat_id}")

    if existing_job:
        await update.message.reply_text("⚠️ As postagens já estão ativas neste chat.")
        return

    scheduler.add_job(postar_ofertas, "interval", minutes=3, args=[chat_id], id=f"posting-{chat_id}")
    await update.message.reply_text("✅ Postagens automáticas iniciadas! Vou enviar novas ofertas a cada 3 minutos.")
    logging.info(f"✅ Novo job de postagem criado para o chat {chat_id}")

async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    job = scheduler.get_job(f"posting-{chat_id}")

    if job:
        scheduler.remove_job(f"posting-{chat_id}")
        await update.message.reply_text("🛑 Postagens automáticas interrompidas.")
        logging.info(f"🛑 Job removido para o chat {chat_id}")
    else:
        await update.message.reply_text("⚠️ Nenhum job ativo para este chat.")

# --------------------------------
# 🌐 CONFIGURAÇÃO DO WEBHOOK
# --------------------------------
@webapp.post(f"/webhook/{BOT_TOKEN}")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
    except Exception as e:
        logging.error(f"Erro no webhook: {e}")
    return {"status": "ok"}

# --------------------------------
# 🚀 INICIALIZAÇÃO DO BOT
# --------------------------------
async def main():
    logging.info("🚀 Iniciando bot...")
    scheduler.start()

    await app.bot.delete_webhook()
    await app.bot.set_webhook(WEBHOOK_URL)
    logging.info(f"🌐 Webhook configurado em: {WEBHOOK_URL}")

    import uvicorn
    uvicorn.run(webapp, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    asyncio.run(main())
