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
# TESTE AUTOMÁTICO DA API VALUE SERP
# -------------------------------
async def testar_valueserp():
    termo = "notebook Amazon"
    url = (
        f"https://api.valueserp.com/search"
        f"?api_key={VALUE_SERP_API_KEY}"
        f"&q={termo}"
        f"&location=Brazil"
        f"&gl=br&hl=pt-br&engine=google_shopping"
    )

    logger.info("🧪 Testando API ValueSERP...")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.error(f"❌ Erro HTTP {resp.status} na ValueSERP. Verifique a chave API.")
                return False
            data = await resp.json()

    results = data.get("shopping_results", [])
    if not results:
        logger.error("⚠️ Nenhum resultado retornado pela ValueSERP. Pode ser limite de créditos ou APIKey inválida.")
        return False

    sample = results[0]
    titulo = sample.get("title", "Sem título")
    preco = sample.get("price", {}).get("raw", "Sem preço")
    logger.info(f"✅ Teste ValueSERP OK → Exemplo: {titulo} | {preco}")
    return True

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

    logger.info(f"🔍 Buscando ofertas: {termo}")
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.error(f"❌ Erro na API ValueSERP: {resp.status}")
                return None
            data = await resp.json()

    results = data.get("shopping_results", [])
    if not results:
        logger.warning("⚠️ Nenhuma oferta encontrada.")
        return None

    oferta = choice(results)
    titulo = oferta.get("title", "Produto sem nome")
    link = oferta.get("link", "")
    preco = oferta.get("price", {}).get("raw", "Preço indisponível")
    loja = oferta.get("source", "Amazon")
    imagem = oferta.get("thumbnail", "")

    logger.info(f"✅ Oferta encontrada: {titulo} | {preco}")
    mensagem = f"💥 *{titulo}*\n🏪 Loja: {loja}\n💰 Preço: {preco}\n🔗 [Ver na Amazon]({link})"
    return {"texto": mensagem, "imagem": imagem}

# -------------------------------
# POSTAR OFERTA
# -------------------------------
async def postar_oferta(context):
    chat_id = context.job.data
    logger.info(f"📦 Executando ciclo de postagem para chat_id={chat_id}")
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
        logger.info(f"📤 Oferta enviada para {chat_id}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar oferta: {e}")

# -------------------------------
# COMANDOS
# -------------------------------
async def start(update, context):
    logger.info(f"Mensagem recebida de {update.effective_chat.id}: {update.message.text}")
    await update.message.reply_text("🤖 Olá! Eu irei enviar ofertas automaticamente aqui a cada ciclo.")

async def start_posting(update, context):
    chat_id = update.effective_chat.id
    job_id = f"posting-{chat_id}"

    logger.info(f"🚀 Comando /iniciar recebido de {chat_id}")

    old_job = context.job_queue.get_jobs_by_name(job_id)
    if old_job:
        for job in old_job:
            job.schedule_removal()
            logger.info(f"🧹 Job antigo removido ({job_id})")

    job = context.job_queue.run_repeating(
        postar_oferta, interval=180, first=5, data=chat_id, name=job_id
    )

    logger.info(f"✅ Novo job de postagem criado: {job_id}")
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
    logger.info(f"🛑 Job de postagem removido: {job_id}")
    await update.message.reply_text("🛑 Envio automático de ofertas parado.")

# -------------------------------
# PRINCIPAL
# -------------------------------
async def main():
    logger.info("🚀 Iniciando bot (webhook nativo PTB) ...")

    # Testar API antes de iniciar o bot
    api_ok = await testar_valueserp()
    if not api_ok:
        logger.error("🚫 A ValueSERP API não está funcional. O bot não irá postar ofertas.")
        # Mesmo assim inicia o bot para responder comandos
    else:
        logger.info("✅ ValueSERP testada com sucesso!")

    application = ApplicationBuilder().token(TOKEN).build()

    scheduler = AsyncIOScheduler()
    scheduler.start()
    logger.info("✅ Scheduler iniciado")

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("iniciar", start_posting))
    application.add_handler(CommandHandler("parar", stop_posting))

    # Configurar webhook
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{BASE_URL}/webhook/{TOKEN}")
    logger.info(f"🌐 Webhook configurado em: {BASE_URL}/webhook/{TOKEN}")

    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=f"webhook/{TOKEN}",
        webhook_url=f"{BASE_URL}/webhook/{TOKEN}",
    )

# -------------------------------
# EXECUÇÃO
# -------------------------------
if __name__ == "__main__":
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()

    try:
        loop.create_task(main())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Bot finalizado manualmente.")
