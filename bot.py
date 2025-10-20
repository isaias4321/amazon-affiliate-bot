import logging
import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup

# === CONFIGURAÇÕES DO BOT ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

if not BOT_TOKEN:
    raise ValueError("❌ A variável BOT_TOKEN não está definida!")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

scheduler = AsyncIOScheduler()

# === FUNÇÃO PARA BUSCAR OFERTAS ===
async def fetch_amazon_promotions():
    """Busca promoções da Amazon GoldBox"""
    url = "https://www.amazon.com.br/gp/goldbox"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logging.warning(f"⚠️ Erro HTTP {response.status} ao acessar {url}")
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")
                promos = [a.text.strip() for a in soup.select("a.a-link-normal") if a.text.strip()]
                return promos[:5]  # retorna as 5 primeiras
    except Exception as e:
        logging.error(f"Erro ao buscar promoções: {e}")
        return []

# === TAREFA AGENDADA ===
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    """Envia as promoções no grupo periodicamente"""
    promotions = await fetch_amazon_promotions()
    if not promotions:
        logging.info("Nenhuma promoção encontrada no momento.")
        return

    for promo in promotions:
        await context.bot.send_message(chat_id=GROUP_ID, text=f"🔥 {promo}")

    logging.info(f"🕒 {len(promotions)} promoções postadas às {datetime.now()}")

# === COMANDOS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Use /start_posting para iniciar as postagens automáticas!")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Comandos disponíveis:\n"
        "/start - Inicia o bot\n"
        "/ajuda - Mostra esta mensagem\n"
        "/start_posting - Começa a postar ofertas automáticas"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Você disse: {update.message.text}")

# === INICIAR POSTAGENS AUTOMÁTICAS ===
async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa a tarefa de postagem automática"""
    if not GROUP_ID:
        await update.message.reply_text("⚠️ Defina o GROUP_ID nas variáveis de ambiente!")
        return

    if not scheduler.running:
        scheduler.start()

    # Remove qualquer tarefa anterior antes de criar uma nova
    for job in scheduler.get_jobs():
        job.remove()

    scheduler.add_job(
        postar_ofertas,
        "interval",
        minutes=1,
        args=[context],
        id="job_postar_ofertas"
    )

    await update.message.reply_text("✅ Postagens automáticas iniciadas! A cada 1 minuto serão verificadas novas promoções.")

# === FUNÇÃO PRINCIPAL ===
def main():
    logging.info("🚀 Iniciando bot...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("start_posting", start_posting))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logging.info("✅ Bot iniciado e aguardando mensagens...")
    app.run_polling(close_loop=False)

# === EXECUÇÃO ===
if __name__ == "__main__":
    main()
