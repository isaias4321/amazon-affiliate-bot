import os
import logging
import asyncio
import aiohttp
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from random import choice
import nest_asyncio

# -------------------------------
# CONFIGURAÇÕES
# -------------------------------
TOKEN = os.getenv("BOT_TOKEN")
VALUE_SERP_API_KEY = os.getenv("VALUE_SERP_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "seu-tag-afiliado")
PORT = int(os.getenv("PORT", 8080))
BASE_URL = os.getenv("BASE_URL", "https://amazon-ofertas-api.up.railway.app")

SEARCH_TERMS = [
    "smartphone Amazon",
    "notebook Amazon",
    "periféricos gamer Amazon",
    "eletrodomésticos Amazon",
    "ferramentas Amazon"
]

# -------------------------------
# LOGS
# -------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -------------------------------
# BUSCAR OFERTA
# -------------------------------
async def buscar_oferta():
    termo = choice(SEARCH_TERMS)
    url = (
        f"https://api.valueserp.com/search"
        f"?api_key={VALUE_SERP_API_KEY}"
        f"&q={termo}"
        f"&location=Brazil"
        f"&gl=br&hl=pt-br&engine=google_shopping"
    )

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()

    results = data.get("shopping_results", [])
    if not results:
        return None

    oferta = choice(results)
    titulo = oferta.get("title", "Produto sem nome")
    link = oferta.get("link", "")
    preco = oferta.get("price", {}).get("raw", "Preço indisponível")
    loja = oferta.get("source", "Amazon")
    imagem = oferta.get("thumbnail", "")

    mensagem = f"💥 *{titulo}*\n🏪 Loja: {loja}\n💰 Preço: {preco}\n🔗 [Ver na Amazon]({link})"
    return {"texto": mensagem, "imagem": imagem}

# -------------------------------
# POSTAR OFERTA
# -------------------------------
async def postar_oferta(context):
    chat_id = context.job.data
    oferta = await buscar_oferta()
    if not oferta:
        await context.bot.send_message(chat_id, "Nenhuma oferta encontrada no momento. 🔄")
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
    except Exception as e:
        logger.error(f"Erro ao enviar oferta: {e}")

# -------------------------------
# COMANDOS
# -------------------------------
async def start(update, context):
    logger.info(f"Mensagem recebida de {update.effective_chat.id}: {update.message.text}")
    await update.message.reply_text("🤖 Olá! Eu irei enviar ofertas automaticamente aqui a cada ciclo.")

async def start_posting(update, context):
    chat_id = update.effective_chat.id
    job_id = f"posting-{chat_id}"

    old_job = context.job_queue.get_jobs_by_name(job_id)
    if old_job:
        for job in old_job:
            job.schedule_removal()

    context.job_queue.run_repeating(postar_oferta, interval=180, first=5, data=chat_id, name=job_id)
    await update.message.reply_text("✅ Envio automático de ofertas iniciado!")

async def stop_posting(update, context):
    chat_id = update.effective_chat.id
    job_id = f"posting-{chat_id}"

    jobs = context.job_queue.get_jobs_by_name(job_id)
    if not jobs:
        await update.message.reply_text("⚠️ Nenhum envio ativo encontrado.")
        return

    for job in jobs:
        job.schedule_removal()
    await update.message.reply_text("🛑 Envio automático de ofertas parado.")

# -------------------------------
# PRINCIPAL
# -------------------------------
async def main():
    logger.info("🚀 Iniciando bot (webhook nativo PTB) ...")

    application = ApplicationBuilder().token(TOKEN).build()

    scheduler = AsyncIOScheduler()
    scheduler.start()
    logger.info("Scheduler started")

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("iniciar", start_posting))
    application.add_handler(CommandHandler("parar", stop_posting))

    # Configurar webhook corretamente
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{BASE_URL}/webhook/{TOKEN}")
    logger.info(f"🌐 Webhook configurado em: {BASE_URL}/webhook/{TOKEN}")

    # Rodar o webhook (corrigido)
    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=f"webhook/{TOKEN}",
        webhook_url=f"{BASE_URL}/webhook/{TOKEN}",
    )

# -------------------------------
# EXECUÇÃO SEGURA
# -------------------------------
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()

    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            loop.create_task(main())
            loop.run_forever()
        else:
            logger.warning("⚠️ Event loop já estava em execução.")
    except (KeyboardInterrupt, SystemExit):
        pass
