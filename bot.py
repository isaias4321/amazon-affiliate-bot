import os
import random
import asyncio
import logging
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import Application, CommandHandler

# 🔧 Configurações
TOKEN = os.getenv("BOT_TOKEN", "SEU_TOKEN_AQUI")
VALUE_SERP_API = os.getenv("VALUE_SERP_API", "0646FC6961A84884A0657B9DF6D85C89")

CATEGORIAS = [
    "smartphone site:amazon.com.br",
    "notebook site:amazon.com.br",
    "periféricos gamer site:amazon.com.br",
    "eletrodoméstico site:amazon.com.br",
    "ferramentas site:amazon.com.br"
]

INTERVALO_MINUTOS = 2  # intervalo de 2 minutos
scheduler = AsyncIOScheduler()

# 🎯 Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 🔍 Busca real de ofertas
async def buscar_oferta():
    categoria = random.choice(CATEGORIAS)
    url = f"https://api.valueserp.com/search?api_key={VALUE_SERP_API}&q={categoria}&gl=br&hl=pt-br&output=json"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status != 200:
                logger.error(f"❌ Erro {response.status} na API ValueSERP.")
                return None
            data = await response.json()

    resultados = data.get("organic_results", [])
    if not resultados:
        logger.warning(f"⚠️ Nenhuma oferta encontrada para {categoria}")
        return None

    oferta = random.choice(resultados[:5])
    titulo = oferta.get("title", "Oferta sem título")
    link = oferta.get("link", "")
    imagem = oferta.get("thumbnail", None)

    preco = None
    snippet = oferta.get("snippet", "")
    if "R$" in snippet:
        preco = snippet.split("R$")[-1].split()[0]

    return {
        "titulo": titulo,
        "link": link,
        "preco": f"💸 R$ {preco}" if preco else "💸 Preço não disponível",
        "imagem": imagem
    }

# 📢 Postar oferta
async def postar_oferta(context):
    chat_id = context.job.chat_id
    oferta = await buscar_oferta()

    if not oferta:
        await context.bot.send_message(chat_id, "⚠️ Nenhuma oferta encontrada no momento.")
        return

    mensagem = f"🔥 *{oferta['titulo']}*\n{oferta['preco']}\n🛒 [Ver na Amazon]({oferta['link']})"
    if oferta["imagem"]:
        await context.bot.send_photo(chat_id, photo=oferta["imagem"], caption=mensagem, parse_mode="Markdown")
    else:
        await context.bot.send_message(chat_id, mensagem, parse_mode="Markdown")

    logger.info(f"✅ Oferta postada no chat {chat_id}: {oferta['titulo']}")

# ▶️ Iniciar postagens
async def start_posting(update, context):
    chat_id = update.effective_chat.id
    existing_job = scheduler.get_job(f"posting-{chat_id}")
    if existing_job:
        existing_job.remove()

    scheduler.add_job(postar_oferta, "interval", minutes=INTERVALO_MINUTOS, args=[context], id=f"posting-{chat_id}")
    scheduler.get_job(f"posting-{chat_id}").chat_id = chat_id

    await update.message.reply_text("✅ Postagens automáticas iniciadas! 1 oferta a cada 2 minutos.")
    logger.info(f"🚀 Ciclo de postagens iniciado para chat {chat_id}")

# ⏹ Parar postagens
async def stop_posting(update, context):
    chat_id = update.effective_chat.id
    job = scheduler.get_job(f"posting-{chat_id}")
    if job:
        job.remove()
        await update.message.reply_text("🛑 Postagens automáticas paradas.")
        logger.info(f"⛔ Postagens paradas para chat {chat_id}")
    else:
        await update.message.reply_text("⚠️ Nenhum ciclo de postagem ativo neste chat.")

# 🚀 Função principal
async def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("startposting", start_posting))
    application.add_handler(CommandHandler("stopposting", stop_posting))

    scheduler.start()
    logger.info("🤖 Bot iniciado!")

    # 🧠 Tenta webhook, se falhar usa polling automaticamente
    try:
        await application.run_webhook(
            listen="0.0.0.0",
            port=int(os.getenv("PORT", "8080")),
            url_path=TOKEN,
            webhook_url=f"https://amazon-ofertas-api.up.railway.app/webhook/{TOKEN}"
        )
    except Exception as e:
        logger.warning(f"⚠️ Webhook falhou ({e}), mudando para polling...")
        await application.run_polling()

# 🔄 Evita erro de loop no Railway
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
