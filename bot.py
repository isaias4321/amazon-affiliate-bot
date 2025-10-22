import os
import asyncio
import logging
import random
from telegram import Update, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    AIORateLimiter,
)
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import nest_asyncio

# =========================
# CONFIGURAÇÃO DE LOGS
# =========================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# =========================
# CONFIGURAÇÕES DO BOT
# =========================
TOKEN = os.getenv("BOT_TOKEN") or "COLOQUE_SEU_TOKEN_AQUI"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Railway: ex -> https://seuapp.up.railway.app/webhook
PORT = int(os.getenv("PORT", 8080))

# =========================
# CONFIGURAÇÕES DE CATEGORIAS
# =========================
CATEGORIAS = [
    "smartphone",
    "notebook",
    "periféricos gamer",
    "eletrodomésticos",
    "ferramentas",
]

# =========================
# SIMULAÇÃO DE OFERTAS AUTOMÁTICAS
# =========================
async def buscar_oferta_aleatoria():
    """Gera uma oferta aleatória simulando Shopee e Mercado Livre."""
    lojas = ["Shopee", "Mercado Livre"]
    loja = random.choice(lojas)

    produtos = {
        "smartphone": [
            ("Smartphone Samsung Galaxy A15", "https://s.shopee.com.br/4fnnmDB1am"),
            ("iPhone 13 128GB Apple", "https://s.shopee.com.br/60JBMhVbkU"),
        ],
        "notebook": [
            ("Notebook Acer Aspire 5", "https://s.shopee.com.br/8pdMjx6PWT"),
            ("Notebook Lenovo IdeaPad 3i", "https://s.shopee.com.br/4fnnmDB1am"),
        ],
        "periféricos gamer": [
            ("Teclado Mecânico Redragon Kumara", "https://s.shopee.com.br/60JBMhVbkU"),
            ("Mouse Gamer Logitech G203", "https://s.shopee.com.br/8pdMjx6PWT"),
        ],
        "eletrodomésticos": [
            ("Air Fryer Mondial 4L", "https://s.shopee.com.br/60JBMhVbkU"),
            ("Liquidificador Philips Walita", "https://s.shopee.com.br/8pdMjx6PWT"),
        ],
        "ferramentas": [
            ("Parafusadeira Bosch 12V", "https://s.shopee.com.br/4fnnmDB1am"),
            ("Furadeira Black+Decker 560W", "https://s.shopee.com.br/60JBMhVbkU"),
        ],
    }

    categoria = random.choice(CATEGORIAS)
    produto, link = random.choice(produtos[categoria])
    preco = random.randint(150, 2500)
    desconto = random.randint(10, 60)

    oferta = {
        "loja": loja,
        "categoria": categoria,
        "produto": produto,
        "preco": preco,
        "desconto": desconto,
        "link": link,
        "imagem": "https://i.imgur.com/ox9CytL.jpeg",  # Imagem genérica
    }

    return oferta

# =========================
# FUNÇÃO DE POSTAGEM
# =========================
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    """Posta automaticamente uma oferta no grupo."""
    job = context.job
    chat_id = job.chat_id

    oferta = await buscar_oferta_aleatoria()

    mensagem = (
        f"🔥 *OFERTA RELÂMPAGO {oferta['loja']}!*\n\n"
        f"🛍️ {oferta['produto']}\n"
        f"💰 *Preço:* R$ {oferta['preco']:.2f}\n"
        f"💸 *Desconto:* {oferta['desconto']}%\n\n"
        f"📦 *Categoria:* {oferta['categoria'].capitalize()}\n"
        f"🔗 [Compre agora]({oferta['link']})"
    )

    try:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=oferta["imagem"],
            caption=mensagem,
            parse_mode="Markdown",
        )
        logger.info(f"✅ Oferta enviada para {chat_id}: {oferta['produto']}")
    except Exception as e:
        logger.error(f"Erro ao enviar oferta: {e}")

# =========================
# COMANDOS DO BOT
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Olá! Eu sou o bot de ofertas automáticas da Shopee e Mercado Livre!\n"
        "Use /start_posting para começar a receber promoções automáticas."
    )

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    scheduler = context.application.job_queue

    if scheduler.get_jobs_by_name(f"posting-{chat_id}"):
        await update.message.reply_text("⚠️ As postagens já estão ativas!")
        return

    scheduler.run_repeating(
        postar_oferta,
        interval=120,  # 2 minutos
        first=5,
        name=f"posting-{chat_id}",
        chat_id=chat_id,
    )

    await update.message.reply_text(
        "✅ Postagens automáticas ativadas! Receberá 1 oferta a cada 2 minutos 🔥"
    )
    logger.info(f"🚀 Iniciando ciclo de postagens no chat {chat_id}")

async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    scheduler = context.application.job_queue
    jobs = scheduler.get_jobs_by_name(f"posting-{chat_id}")

    if not jobs:
        await update.message.reply_text("❌ Nenhuma postagem automática ativa.")
        return

    for job in jobs:
        job.schedule_removal()

    await update.message.reply_text("🛑 Postagens automáticas desativadas.")
    logger.info(f"🛑 Postagens encerradas no chat {chat_id}")

# =========================
# MAIN
# =========================
async def main():
    logger.info("🚀 Iniciando bot...")

    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .rate_limiter(AIORateLimiter())
        .build()
    )

    # Adiciona handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))
    application.add_handler(CommandHandler("stop_posting", stop_posting))

    logger.info("Scheduler started")

    # Webhook (Railway) ou Polling (local)
    if WEBHOOK_URL:
        await application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
        )
    else:
        logger.info("▶️ Sem WEBHOOK_URL — executando via polling.")
        await application.run_polling()

# =========================
# EXECUÇÃO
# =========================
if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
