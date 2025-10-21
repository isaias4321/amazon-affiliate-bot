import os
import asyncio
import logging
import random
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, Request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import uvicorn

# ==============================
# CONFIGURAÇÕES
# ==============================
TOKEN = os.getenv("BOT_TOKEN")  # Token do BotFather
PORT = int(os.getenv("PORT", 8080))
AFILIADO_TAG = "seunome-20"  # Coloque sua tag de afiliado Amazon aqui!

# Configuração de logs
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializações principais
app = Application.builder().token(TOKEN).build()
scheduler = AsyncIOScheduler()
webapp = FastAPI()

# ==============================
# CATEGORIAS AMAZON
# ==============================
CATEGORIAS = {
    "eletronicos": "https://www.amazon.com.br/s?i=electronics",
    "eletrodomesticos": "https://www.amazon.com.br/s?i=appliances",
    "ferramentas": "https://www.amazon.com.br/s?i=tools",
    "informatica": "https://www.amazon.com.br/s?i=computers"
}


# ==============================
# FUNÇÃO PARA BUSCAR OFERTAS
# ==============================
def buscar_ofertas_amazon(limit=5):
    categoria = random.choice(list(CATEGORIAS.keys()))
    url = CATEGORIAS[categoria]
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(response.text, "html.parser")

        produtos = []
        for item in soup.select("div.s-main-slot div[data-asin]")[:limit]:
            asin = item.get("data-asin")
            titulo_tag = item.select_one("h2 a span")
            preco_tag = item.select_one("span.a-price-whole")

            if asin and titulo_tag and preco_tag:
                produtos.append({
                    "titulo": titulo_tag.text.strip(),
                    "preco": f"R$ {preco_tag.text.strip()}",
                    "url": f"https://www.amazon.com.br/dp/{asin}?tag={AFILIADO_TAG}"
                })
        return produtos

    except Exception as e:
        logger.error(f"Erro ao buscar ofertas: {e}")
        return []


# ==============================
# FUNÇÕES DO BOT
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou o bot de ofertas da Amazon.\n\n"
        "Comandos disponíveis:\n"
        "• /start_posting → começar postagens automáticas\n"
        "• /stop_posting → parar postagens automáticas\n"
    )


async def postar_ofertas(chat_id: str):
    """Função que envia ofertas automaticamente."""
    logger.info(f"🛍️ Buscando novas ofertas para {chat_id}...")

    ofertas = buscar_ofertas_amazon(limit=4)
    if not ofertas:
        try:
            await app.bot.send_message(chat_id, "⚠️ Nenhuma oferta encontrada no momento.")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
        return

    for oferta in ofertas:
        msg = f"🔥 *{oferta['titulo']}*\n💰 {oferta['preco']}\n👉 [Ver na Amazon]({oferta['url']})"
        try:
            await app.bot.send_message(chat_id, msg, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {chat_id}: {e}")


async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia postagens automáticas."""
    chat_id = str(update.effective_chat.id)

    existing_job = scheduler.get_job(f"posting-{chat_id}")
    if existing_job:
        await update.message.reply_text("⚠️ Já estou postando ofertas aqui!")
        return

    scheduler.add_job(
        postar_ofertas,
        trigger="interval",
        minutes=3,
        id=f"posting-{chat_id}",
        args=[chat_id],
        replace_existing=True,
    )

    await update.message.reply_text("✅ Postagens automáticas iniciadas! 🔥")
    logger.info(f"✅ Novo job de postagem criado para o chat {chat_id}")


async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Para as postagens automáticas."""
    chat_id = str(update.effective_chat.id)
    job = scheduler.get_job(f"posting-{chat_id}")
    if job:
        scheduler.remove_job(job.id)
        await update.message.reply_text("🛑 Postagens automáticas paradas!")
        logger.info(f"🛑 Postagens paradas para {chat_id}")
    else:
        await update.message.reply_text("⚠️ Nenhuma postagem ativa para parar.")


# ==============================
# WEBHOOK (para Railway)
# ==============================
@webapp.post("/webhook/{token}")
async def webhook(request: Request, token: str):
    if token != TOKEN:
        return {"error": "Token inválido"}

    data = await request.json()
    update = Update.de_json(data, app.bot)
    try:
        await app.initialize()
        await app.process_update(update)
    except Exception as e:
        logger.error(f"Erro no webhook: {e}")

    return {"status": "ok"}


# ==============================
# MAIN
# ==============================
async def main():
    logger.info("🚀 Iniciando bot...")
    scheduler.start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start_posting", start_posting))
    app.add_handler(CommandHandler("stop_posting", stop_posting))

    await app.bot.delete_webhook()
    webhook_url = f"https://amazon-ofertas-api.up.railway.app/webhook/{TOKEN}"
    await app.bot.set_webhook(webhook_url)
    logger.info(f"🌐 Webhook configurado em: {webhook_url}")

    config = uvicorn.Config(webapp, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
