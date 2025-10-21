import os
import asyncio
import logging
import random
from typing import Dict, List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
import uvicorn
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from amazon_scraper import buscar_ofertas, buscar_ofertas_por_categoria

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
def _aplicar_tag_afiliado(url: str) -> str:
    if not AFFILIATE_TAG:
        return url

    if "tag=" in url:
        return url

    separador = "&" if "?" in url else "?"
    return f"{url}{separador}tag={AFFILIATE_TAG}"


async def buscar_ofertas_filtradas(limit: int = 6) -> List[Dict[str, str]]:
    categorias = [
        "eletrônicos", "eletrodomésticos", "ferramentas",
        "peças de computadores", "notebooks"
    ]
    categoria = random.choice(categorias)

    logging.info(f"🔎 Buscando ofertas na categoria: {categoria}")

    produtos = await buscar_ofertas_por_categoria(categoria, limit=limit * 3)

    if not produtos:
        logging.info(
            f"⚠️ Nenhum produto encontrado na categoria {categoria}. Tentando Goldbox."
        )
        produtos = await buscar_ofertas(limit=limit * 3)

    if not produtos:
        logging.info("⚠️ Nenhuma oferta encontrada nem na busca nem no Goldbox")
        return []

    resultados: List[Dict[str, str]] = []
    for produto in produtos:
        link = _aplicar_tag_afiliado(produto["link"])

        resultados.append(
            {
                "titulo": produto["titulo"],
                "preco": produto.get("preco", "Ver preço"),
                "link": link,
                "imagem": produto.get("imagem"),
            }
        )

        if len(resultados) >= limit:
            break

    logging.info(f"✅ {len(resultados)} produtos encontrados em {categoria}")
    return resultados

# ===== POSTAGEM AUTOMÁTICA =====
async def postar_ofertas(chat_id: int):
    try:
        ofertas = await buscar_ofertas_filtradas(limit=4)

        if not ofertas:
            await app.bot.send_message(chat_id=chat_id, text="😕 Nenhuma oferta encontrada no momento.")
            return

        await app.bot.send_message(chat_id=chat_id, text="🔄 Buscando novas ofertas...")

        for oferta in ofertas:
            preco = oferta.get("preco", "Ver preço")
            msg = (
                f"🛒 *{oferta['titulo']}*\n"
                f"💰 {preco}\n"
                f"👉 [Ver na Amazon]({oferta['link']})"
            )
            await app.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            logging.info("📤 Enviado: %s", oferta["titulo"])
            await asyncio.sleep(5)

    except Exception as e:
        logging.error(f"Erro ao postar ofertas: {e}")

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
