import os
import asyncio
import aiohttp
import logging
import time
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler
from typing import List, Dict

# ========================= CONFIGURAÇÕES =========================
BOT_TOKEN = os.getenv("BOT_TOKEN") or "COLOQUE_SEU_TOKEN_AQUI"
GROUP_ID = os.getenv("GROUP_ID") or "-4983279500"

# URL principal de promoções da Amazon
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

# Limite e tempo de espera entre requisições
MAX_PRODUCTS_PER_ROUND = 3
REQUEST_DELAY = 2

# ================================================================

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("BOT_TOKEN e GROUP_ID precisam estar definidos.")

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ================================================================

async def safe_get_text(url: str, session: aiohttp.ClientSession = None) -> str:
    """Faz uma requisição HTTP e retorna o HTML (ou None se falhar)."""
    try:
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as response:
            if response.status == 200:
                return await response.text()
            else:
                logger.warning(f"Erro HTTP {response.status} ao acessar {url}")
                return None
    except Exception as e:
        logger.error(f"Erro ao buscar {url}: {e}")
        return None
    finally:
        if close_session:
            await session.close()

def parse_product_page(html: str, url: str) -> Dict:
    """Extrai dados de um produto individual."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("#productTitle")
    price = soup.select_one(".a-price .a-offscreen")
    image = soup.select_one("#imgTagWrapperId img")

    return {
        "title": title.get_text(strip=True) if title else None,
        "price": price.get_text(strip=True) if price else None,
        "image": image["src"] if image and image.get("src") else None,
        "url": url,
    }

def fetch_promotions_blocking(limit: int = MAX_PRODUCTS_PER_ROUND) -> List[Dict]:
    """Busca promoções diretamente do Goldbox."""
    html = asyncio.run(safe_get_text(URL_AMAZON_GOLDBOX))
    if not html:
        logger.warning("Nenhum HTML retornado da Amazon.")
        return []

    soup = BeautifulSoup(html, "html.parser")

    # 🔥 apenas links de produtos válidos
    anchors = soup.select("a[href*='/dp/']")
    seen = set()
    promotions = []

    for a in anchors:
        href = a.get("href")
        if not href:
            continue

        if href.startswith("/"):
            prod_url = "https://www.amazon.com.br" + href.split("?")[0]
        else:
            prod_url = href.split("?")[0]

        if prod_url in seen:
            continue
        seen.add(prod_url)

        time.sleep(REQUEST_DELAY)
        page_html = asyncio.run(safe_get_text(prod_url))
        if not page_html:
            continue

        pdata = parse_product_page(page_html, prod_url)
        if pdata.get("title") and pdata.get("image"):
            promotions.append(pdata)

        if len(promotions) >= limit:
            break

    logger.info("Encontradas %d promoções válidas.", len(promotions))
    return promotions

# ================================================================

async def postar_ofertas(context):
    """Tarefa periódica para postar promoções no grupo."""
    bot = context.bot
    promotions = fetch_promotions_blocking()

    if not promotions:
        logger.info("Nenhuma promoção válida encontrada.")
        return

    for p in promotions:
        msg = f"🛒 *{p['title']}*\n💰 {p['price'] or 'Preço indisponível'}\n🔗 [Ver na Amazon]({p['url']})"
        try:
            await bot.send_photo(
                chat_id=GROUP_ID,
                photo=p["image"],
                caption=msg,
                parse_mode="Markdown",
            )
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Erro ao enviar promoção: {e}")

# ================================================================

async def start(update, context):
    """Comando /start para iniciar manualmente."""
    await update.message.reply_text("🤖 Bot de ofertas da Amazon iniciado!")
    await postar_ofertas(context)

# ================================================================

def iniciar_bot():
    """Inicializa o bot do Telegram."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # ✅ loop automático de 1 minuto
    app.job_queue.run_repeating(postar_ofertas, interval=60, first=10)

    logger.info("Bot iniciado com sucesso.")
    app.run_polling()

# ================================================================

if __name__ == "__main__":
    iniciar_bot()
