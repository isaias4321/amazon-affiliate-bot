import os
import asyncio
import logging
import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import aiohttp
from bs4 import BeautifulSoup

# ==============================
# CONFIGURAÇÕES GERAIS
# ==============================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
VALUE_SERP_API_KEY = os.getenv("VALUE_SERP_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "seuCodigoAfiliado")
BASE_URL = os.getenv("BASE_URL", "https://seuprojeto.up.railway.app")
PORT = int(os.getenv("PORT", 8080))

scheduler = AsyncIOScheduler()


# ==============================
# FUNÇÃO DE BUSCA DE OFERTAS
# ==============================
async def buscar_oferta():
    categorias = [
        "smartphone Amazon",
        "notebook Amazon",
        "periféricos gamer Amazon",
        "eletrodomésticos Amazon",
        "ferramentas Amazon"
    ]
    termo = random.choice(categorias)
    logging.info(f"🔎 Buscando oferta: {termo}")

    url = f"https://api.valueserp.com/search"
    params = {
        "api_key": VALUE_SERP_API_KEY,
        "q": termo,
        "gl": "br",
        "hl": "pt-br",
        "google_domain": "google.com.br",
        "output": "json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()

    results = data.get("organic_results", [])
    if not results:
        logging.warning("⚠️ Nenhum resultado encontrado.")
        return None

    item = random.choice(results[:5])  # Pega até os 5 primeiros
    title = item.get("title")
    link = item.get("link")

    if not title or not link:
        return None

    # Formata link afiliado
    if "amazon" in link:
        if "tag=" not in link:
            sep = "&" if "?" in link else "?"
            link = f"{link}{sep}tag={AFFILIATE_TAG}"

    return {"titulo": title, "link": link}


# ==============================
# FUNÇÃO DE POSTAGEM AUTOMÁTICA
# ==============================
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data.get("chat_id")
    oferta = await buscar_oferta()

    if not oferta:
        await context.bot.send_message(chat_id, "❌ Nenhuma oferta encontrada no momento.")
        return

    mensagem = f"🔥 *Oferta do momento!*\n\n📦 {oferta['titulo']}\n\n👉 [Ver na Amazon]({oferta['link']})"
    await context.bot.send_message(chat_id, mensagem, parse_mode="Markdown", disable_web_page_preview=False)
    logging.info(f"✅ Oferta enviada para o grupo {chat_id}")


# ==============================
# COMANDOS DO BOT
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Sou seu bot de ofertas da Amazon.\nUse /start_posting para ativar as postagens automáticas.")


async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if any(job.id == f"posting-{chat_id}" for job in scheduler.get_jobs()):
        await update.message.reply_text("⚙️ As postagens automáticas já estão ativas neste chat.")
        return

    scheduler.add_job(
        postar_oferta,
        "interval",
        minutes=3,
        id=f"posting-{chat_id}",
        data={"chat_id": chat_id},
    )

    await update.message.reply_text("✅ Postagens automáticas ativadas! Enviarei uma nova oferta a cada 3 minutos.")
    logging.info(f"🟢 Agendado job de postagens para {chat_id}")


async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    job = scheduler.get_job(f"posting-{chat_id}")

    if job:
        job.remove()
        await update.message.reply_text("🛑 Postagens automáticas desativadas neste chat.")
        logging.info(f"🔴 Postagens paradas para {chat_id}")
    else:
        await update.message.reply_text("⚠️ Não havia postagens automáticas ativas neste chat.")


# ==============================
# FUNÇÃO PRINCIPAL (WEBHOOK PTB)
# ==============================
async def main():
    logging.info("🚀 Iniciando bot (webhook nativo PTB) ...")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))
    application.add_handler(CommandHandler("stop_posting", stop_posting))

    # Inicia agendador
    scheduler.start()

    # Webhook
    webhook_url = f"{BASE_URL}/webhook/{BOT_TOKEN}"
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=webhook_url)

    logging.info(f"🌐 Webhook configurado em: {webhook_url}")

    # Roda o webhook nativo (sem precisar de Uvicorn)
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=webhook_url,
    )


if __name__ == "__main__":
    asyncio.run(main())
