import os
import asyncio
import logging
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import aiohttp
from bs4 import BeautifulSoup

# Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
MERCADO_AFIL = os.getenv("MERCADO_AFIL")
SHOPEE_AFIL = os.getenv("SHOPEE_AFIL")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "")
PORT = int(os.getenv("PORT", 8080))

app_tg = Application.builder().token(TOKEN).build()
scheduler = AsyncIOScheduler()


# 🛒 Buscar ofertas do Mercado Livre
async def buscar_ofertas_mercadolivre():
    url = "https://www.mercadolivre.com.br/ofertas"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            ofertas = []
            for item in soup.select("a.promotion-item__link")[:5]:
                titulo = item.get("title") or item.text.strip()
                link = item["href"].split("?")[0] + f"?ref={MERCADO_AFIL}"
                ofertas.append(f"🛍️ *{titulo}*\n🔗 {link}")

            return ofertas


# 🛍️ Buscar ofertas da Shopee
async def buscar_ofertas_shopee():
    url = "https://shopee.com.br/flash_sale"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            ofertas = []
            for item in soup.select("a")[:5]:
                if "/product/" in item.get("href", ""):
                    titulo = item.text.strip() or "Oferta Shopee"
                    link = "https://shopee.com.br" + item["href"] + f"?aff_id={SHOPEE_AFIL}"
                    ofertas.append(f"🔥 *{titulo}*\n🔗 {link}")

            return ofertas


# 🚀 Enviar ofertas
async def postar_ofertas():
    try:
        ml = await buscar_ofertas_mercadolivre()
        sp = await buscar_ofertas_shopee()

        if not ml and not sp:
            logging.info("Nenhuma oferta encontrada no momento.")
            return

        todas = ml + sp
        msg = "\n\n".join(todas[:6])
        await app_tg.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        logging.info("✅ Ofertas enviadas com sucesso!")
    except Exception as e:
        logging.error(f"Erro ao postar ofertas: {e}")


# ▶️ Comandos
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot de ofertas automáticas ativo! Use /start_posting para iniciar.")

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scheduler.add_job(postar_ofertas, "interval", minutes=2)
    scheduler.start()
    await update.message.reply_text("🚀 Postagem automática iniciada! A cada 2 minutos verificarei novas ofertas.")


# Registrar comandos
app_tg.add_handler(CommandHandler("start", start))
app_tg.add_handler(CommandHandler("start_posting", start_posting))


# 🔗 Inicialização
if __name__ == "__main__":
    logging.info("Bot iniciado 🚀")

    # Detecta ambiente automaticamente
    if "RAILWAY_ENVIRONMENT" in os.environ:
        # Modo Webhook (Railway)
        webhook_url = f"{WEBHOOK_BASE}/{TOKEN}"
        logging.info(f"🌐 Iniciando em modo Webhook: {webhook_url}")
        app_tg.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=webhook_url
        )
    else:
        # Modo local (Polling)
        logging.info("🧩 Executando localmente com polling...")
        app_tg.run_polling()
