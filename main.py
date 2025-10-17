import os
import logging
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from keepalive import keep_alive

# Configurações e variáveis
TOKEN = os.getenv("TELEGRAM_TOKEN", "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A")
GROUP_ID = int(os.getenv("GROUP_ID", "-4983279500"))
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY", "3694ad1e-583c-4a39-bdf9-9de5674814ee")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=TOKEN)
scheduler = AsyncIOScheduler()

# --- Função para buscar ofertas ---
def buscar_ofertas(categoria):
    url = f"https://proxy.scrapeops.io/v1/?api_key={SCRAPEOPS_API_KEY}&url=https://www.amazon.com.br/s?k={categoria.replace(' ', '+')}"
    ofertas = []

    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            logging.warning(f"⚠️ Erro HTTP {r.status_code} ao buscar {categoria}")
            return ofertas

        soup = BeautifulSoup(r.text, "html.parser")
        produtos = soup.select("div.s-main-slot div[data-component-type='s-search-result']")
        for p in produtos:
            nome = p.select_one("h2 a span")
            preco = p.select_one("span.a-price span.a-offscreen")
            link = p.select_one("h2 a")

            if not (nome and preco and link):
                continue

            nome, preco, link = nome.text.strip(), preco.text.strip(), "https://www.amazon.com.br" + link["href"]
            if "?tag=" not in link:
                link += f"?tag={AFFILIATE_TAG}"

            ofertas.append((nome, preco, link))

        logging.info(f"🔍 {len(ofertas)} ofertas encontradas em {categoria}")
    except Exception as e:
        logging.error(f"Erro ao buscar {categoria}: {e}")

    return ofertas

# --- Envio para Telegram ---
async def enviar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    for cat in categorias:
        ofertas = buscar_ofertas(cat)
        if not ofertas:
            continue

        for nome, preco, link in ofertas[:3]:
            msg = f"🔥 *{nome}*
💰 {preco}
🔗 [Ver na Amazon]({link})"
            await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=True)
            await asyncio.sleep(3)

# --- Comandos Telegram ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot Amazon Ofertas Brasil ativo! Use /ofertas para ver as promoções.")

async def ofertas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Buscando ofertas mais recentes...")
    await enviar_ofertas(context)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot em execução e monitorando ofertas a cada 5 minutos.")

# --- Main ---
async def main():
    logging.info("🤖 Iniciando bot Amazon Ofertas Brasil...")
    keep_alive()

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ofertas", ofertas))
    app.add_handler(CommandHandler("status", status))

    scheduler.add_job(enviar_ofertas, "interval", minutes=5, args=[None])
    scheduler.start()

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
