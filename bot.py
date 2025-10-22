import os
import logging
import asyncio
import aiohttp
import feedparser
from random import choice
from telegram.ext import ApplicationBuilder, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio

# -------------------------------
# CONFIGURAÇÕES
# -------------------------------
TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))
BASE_URL = os.getenv("BASE_URL", "https://amazon-ofertas-api.up.railway.app")

# Feeds RSS de categorias da Amazon (BR)
AMAZON_FEEDS = {
    "smartphones": "https://www.amazon.com.br/gp/rss/bestsellers/electronics/16243842011",
    "notebooks": "https://www.amazon.com.br/gp/rss/bestsellers/computers/16364755011",
    "perifericos_gamer": "https://www.amazon.com.br/gp/rss/bestsellers/games/7842738011",
    "eletrodomesticos": "https://www.amazon.com.br/gp/rss/bestsellers/kitchen/17861999011",
    "ferramentas": "https://www.amazon.com.br/gp/rss/bestsellers/hi/17859841011",
}

# -------------------------------
# LOGS
# -------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------------------
# FUNÇÃO: BUSCAR OFERTA ALEATÓRIA
# -------------------------------
async def buscar_oferta():
    categoria, url = choice(list(AMAZON_FEEDS.items()))
    logger.info(f"🔍 Buscando ofertas RSS da categoria: {categoria}")

    try:
        feed = feedparser.parse(url)
        if not feed.entries:
            logger.warning(f"⚠️ Nenhuma oferta encontrada no feed {categoria}")
            return None

        oferta = choice(feed.entries)
        titulo = oferta.get("title", "Produto sem nome")
        link = oferta.get("link", "")
        descricao = oferta.get("summary", "Sem descrição")
        imagem = ""
        if "img" in descricao:
            # Tenta extrair a URL da imagem do HTML do RSS
            start = descricao.find("src=")
            if start != -1:
                imagem = descricao[start+5:descricao.find('"', start+5)]

        mensagem = (
            f"💥 *{titulo}*\n"
            f"🏷️ Categoria: {categoria.capitalize()}\n"
            f"💰 [Ver na Amazon]({link})"
        )

        logger.info(f"✅ Oferta obtida: {titulo}")
        return {"texto": mensagem, "imagem": imagem}

    except Exception as e:
        logger.error(f"❌ Erro ao buscar RSS: {e}")
        return None

# -------------------------------
# FUNÇÃO: POSTAR OFERTA
# -------------------------------
async def postar_oferta(context):
    chat_id = context.job.data
    logger.info(f"📦 Executando ciclo de postagem para chat_id={chat_id}")
    oferta = await buscar_oferta()

    if not oferta:
        await context.bot.send_message(chat_id, "⚠️ Nenhuma oferta disponível agora. Tentando novamente mais tarde.")
        return

    try:
        if oferta["imagem"]:
            await context.bot.send_photo(
                chat_id=chat_id,
                photo=oferta["imagem"],
                caption=oferta["texto"],
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(chat_id, oferta["texto"], parse_mode="Markdown")
        logger.info(f"📤 Oferta enviada para {chat_id}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar oferta: {e}")

# -------------------------------
# COMANDOS DO BOT
# -------------------------------
async def start(update, context):
    await update.message.reply_text("🤖 Olá! Eu envio automaticamente as melhores ofertas da Amazon Brasil.\nUse /iniciar para começar!")

async def start_posting(update, context):
    chat_id = update.effective_chat.id
    job_id = f"posting-{chat_id}"
    logger.info(f"🚀 Iniciando ciclo de postagens automáticas no chat {chat_id}")

    old_job = context.job_queue.get_jobs_by_name(job_id)
    if old_job:
        for job in old_job:
            job.schedule_removal()
            logger.info(f"🧹 Job antigo removido: {job_id}")

    job = context.job_queue.run_repeating(postar_oferta, interval=180, first=5, data=chat_id, name=job_id)
    await update.message.reply_text("✅ Envio automático de ofertas iniciado! 🛍️")

async def stop_posting(update, context):
    chat_id = update.effective_chat.id
    job_id = f"posting-{chat_id}"
    jobs = context.job_queue.get_jobs_by_name(job_id)
    if not jobs:
        await update.message.reply_text("⚠️ Nenhuma postagem ativa para parar.")
        return
    for job in jobs:
        job.schedule_removal()
    logger.info(f"🛑 Postagens paradas no chat {chat_id}")
    await update.message.reply_text("🛑 Envio automático de ofertas interrompido.")

# -------------------------------
# EXECUÇÃO PRINCIPAL
# -------------------------------
async def main():
    logger.info("🚀 Iniciando bot (modo webhook)...")

    application = ApplicationBuilder().token(TOKEN).build()

    scheduler = AsyncIOScheduler()
    scheduler.start()
    logger.info("✅ Scheduler iniciado")

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("iniciar", start_posting))
    application.add_handler(CommandHandler("parar", stop_posting))

    # Configuração do webhook
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{BASE_URL}/webhook/{TOKEN}")
    logger.info(f"🌐 Webhook configurado em: {BASE_URL}/webhook/{TOKEN}")

    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=f"webhook/{TOKEN}",
        webhook_url=f"{BASE_URL}/webhook/{TOKEN}",
    )

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
