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

app_tg = Application.builder().token(TOKEN).build()
scheduler = AsyncIOScheduler()


# 🛒 Função para buscar ofertas do Mercado Livre
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


# 🛍️ Função para buscar ofertas da Shopee
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


# 🚀 Função que posta as ofertas
async def postar_ofertas():
    try:
        ml_ofertas = await buscar_ofertas_mercadolivre()
        shopee_ofertas = await buscar_ofertas_shopee()

        if not ml_ofertas and not shopee_ofertas:
            logging.info("Nenhuma oferta encontrada no momento.")
            return

        ofertas = ml_ofertas + shopee_ofertas
        mensagens = "\n\n".join(ofertas[:6])

        await app_tg.bot.send_message(chat_id=CHAT_ID, text=mensagens, parse_mode="Markdown")
        logging.info("✅ Ofertas enviadas com sucesso!")
    except Exception as e:
        logging.error(f"Erro ao postar ofertas: {e}")


# ▶️ Comandos
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Olá! Eu vou te ajudar a divulgar ofertas automáticas do Mercado Livre e Shopee!")

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scheduler.add_job(postar_ofertas, "interval", minutes=2)
    scheduler.start()
    await update.message.reply_text("🚀 Postagem automática iniciada! Verificando novas ofertas a cada 2 minutos.")


# Handlers
app_tg.add_handler(CommandHandler("start", start))
app_tg.add_handler(CommandHandler("start_posting", start_posting))


# 🔗 Inicialização
if __name__ == "__main__":
    logging.info("Bot iniciado 🚀")
    app_tg.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        url_path=TOKEN,
        webhook_url=f"https://{os.getenv('WEBHOOK_BASE')}/{TOKEN}"
    )
