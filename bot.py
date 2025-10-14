import os
import asyncio
import aiohttp
import random
import logging
from bs4 import BeautifulSoup
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
import nest_asyncio

nest_asyncio.apply()

# ---------------- CONFIGURAÇÕES ----------------
BOT_TOKEN = "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A"
GROUP_ID = -4983279500
AFFILIATE_TAG = "isaias06f-20"
INTERVAL_MIN = 1  # intervalo em minutos
MAX_PRODUCTS = 3  # quantos produtos por rodada

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

CATEGORIES = [
    "notebook", "monitor gamer", "mouse gamer", "teclado gamer", "cadeira gamer",
    "headset gamer", "console", "xbox", "playstation", "ssd", "placa de vídeo",
    "fonte", "processador", "pc gamer", "fone bluetooth", "smartphone", "tablet"
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ---------------- FUNÇÕES ----------------
async def get_html(session, url, retries=3):
    for i in range(retries):
        try:
            async with session.get(url, headers=HEADERS, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.text()
                logger.warning(f"Erro HTTP {resp.status} ao acessar {url}")
        except Exception as e:
            logger.warning(f"Tentativa {i+1} falhou: {e}")
        await asyncio.sleep(3 + random.random() * 2)
    return ""


def extract_price(text):
    import re
    try:
        text = text.replace(".", "").replace(",", ".")
        return float(re.search(r"(\d+(\.\d+)?)", text).group(1))
    except:
        return 0.0


async def fetch_products():
    async with aiohttp.ClientSession() as session:
        results = []
        for keyword in random.sample(CATEGORIES, k=min(5, len(CATEGORIES))):
            url = f"https://www.amazon.com.br/s?k={keyword.replace(' ', '+')}"
            html = await get_html(session, url)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            items = soup.select("div.s-main-slot div[data-asin][data-component-type='s-search-result']")
            for item in items:
                title_tag = item.select_one("h2 a span")
                link_tag = item.select_one("h2 a")
                price_tag = item.select_one("span.a-price span.a-offscreen")
                old_price_tag = item.select_one("span.a-text-price span.a-offscreen")
                img_tag = item.select_one("img.s-image")

                if not (title_tag and link_tag and price_tag and img_tag):
                    continue

                title = title_tag.text.strip()
                link = "https://www.amazon.com.br" + link_tag["href"].split("?")[0]
                image = img_tag["src"]
                price_new = extract_price(price_tag.text)
                price_old = extract_price(old_price_tag.text) if old_price_tag else 0.0
                discount = round((1 - (price_new / price_old)) * 100) if price_old > price_new > 0 else 0

                if discount > 0:
                    results.append({
                        "title": title,
                        "url": f"{link}?tag={AFFILIATE_TAG}",
                        "image": image,
                        "price_new": price_new,
                        "price_old": price_old,
                        "discount": discount
                    })

                if len(results) >= MAX_PRODUCTS:
                    break
            if len(results) >= MAX_PRODUCTS:
                break
        return results


async def post_to_group(bot):
    products = await fetch_products()
    if not products:
        logger.warning("Nenhum produto encontrado.")
        return

    for p in products:
        msg = (
            f"<b>{p['title']}</b>\n"
            f"💰 <b>R$ {p['price_new']:.2f}</b> "
        )
        if p['price_old'] > p['price_new']:
            msg += f"(de R$ {p['price_old']:.2f}) 🔻 {p['discount']}% OFF\n"
        msg += "\nClique abaixo para ver na Amazon 👇"

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Ver oferta na Amazon", url=p['url'])]]
        )

        try:
            await bot.send_photo(
                chat_id=GROUP_ID,
                photo=p["image"],
                caption=msg,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )
            logger.info(f"Produto postado: {p['title']}")
        except Exception as e:
            logger.error(f"Erro ao enviar produto: {e}")

    logger.info("Rodada finalizada ✅")


async def main():
    bot = Bot(BOT_TOKEN)
    while True:
        await post_to_group(bot)
        await asyncio.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    asyncio.run(main())
