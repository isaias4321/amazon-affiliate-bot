import os
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
import logging

# ==============================
# 🔧 CONFIGURAÇÕES
# ==============================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
AMAZON_TAG = os.getenv("AMAZON_TAG")
INTERVAL = int(os.getenv("INTERVAL", 300))  # padrão: 5 min
CATEGORIES = ["games", "eletrônicos"]

# ==============================
# 📜 LOGGING
# ==============================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================
# 📡 SCRAPER AMAZON
# ==============================
async def fetch_deals():
    deals = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    async with aiohttp.ClientSession() as session:
        for category in CATEGORIES:
            url = f"https://www.amazon.com.br/s?k={category}&s=featured-rank"
            async with session.get(url, headers=headers) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                products = soup.select(".s-result-item")
                for product in products:
                    title_tag = product.select_one("h2 a span")
                    price_tag = product.select_one(".a-price-whole")
                    old_price_tag = product.select_one(".a-text-price .a-offscreen")
                    image_tag = product.select_one("img")

                    if not title_tag or not price_tag or not image_tag or not old_price_tag:
                        continue

                    try:
                        title = title_tag.get_text(strip=True)
                        price = float(price_tag.get_text(strip=True).replace(".", "").replace(",", "."))
                        old_price = float(old_price_tag.get_text(strip=True).replace("R$", "").replace(".", "").replace(",", "."))
                        image_url = image_tag["src"]
                        link = "https://www.amazon.com.br" + product.select_one("h2 a")["href"]
                        link += f"&tag={AMAZON_TAG}"

                        discount_percent = round(((old_price - price) / old_price) * 100, 0)

                        # ✅ apenas produtos com desconto real
                        if discount_percent < 5:
                            continue

                        deals.append({
                            "title": title,
                            "price": price,
                            "old_price": old_price,
                            "discount": discount_percent,
                            "image": image_url,
                            "link": link
                        })
                    except Exception:
                        continue
    return deals

# ==============================
# 📢 ENVIAR MENSAGENS
# ==============================
async def send_deals(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    deals = await fetch_deals()

    if not deals:
        logger.info("Nenhuma promoção encontrada no momento.")
        return

    for deal in deals[:5]:  # Envia até 5 produtos por ciclo
        message_text = (
            f"🔥 <b>{deal['title']}</b>\n"
            f"💰 De ~R${deal['old_price']:.2f}~ por <b>R${deal['price']:.2f}</b>\n"
            f"📉 <b>-{int(deal['discount'])}% OFF!</b>"
        )

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🛒 Ver na Amazon", url=deal['link'])]]
        )

        try:
            await bot.send_photo(
                chat_id=GROUP_ID,
                photo=deal["image"],
                caption=message_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.error(f"Erro ao enviar produto: {e}")

# ==============================
# 🤖 COMANDOS
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu sou um bot de promoções Amazon.\n\n"
        "📢 Envio automaticamente ofertas de Games e Eletrônicos com desconto.\n"
        "🛍️ Todos os links já têm meu ID de afiliado.\n"
        "✅ Se você comprar por eles, apoia o canal!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Comandos disponíveis:\n"
        "/start - Apresentação\n"
        "/help - Ajuda\n\n"
        "As ofertas são enviadas automaticamente no grupo a cada 5 minutos ⏳"
    )

# ==============================
# 🕒 MAIN
# ==============================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Tarefa automática
    app.job_queue.run_repeating(send_deals, interval=INTERVAL, first=5)

    logger.info("🚀 Bot de promoções iniciado com sucesso!")
    app.run_polling()

if __name__ == "__main__":
    main()
