import os
import logging
import asyncio
import aiohttp
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import ApplicationBuilder, ContextTypes
from bs4 import BeautifulSoup

# Carrega variáveis do .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("BOT_TOKEN e GROUP_ID precisam estar definidos no .env")

URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

# Configura logs
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# Função para buscar promoções
async def fetch_promotions():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(URL_AMAZON_GOLDBOX, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning(f"Erro HTTP {resp.status} ao acessar {URL_AMAZON_GOLDBOX}")
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                produtos = []
                for item in soup.select(".DealCard")[:5]:
                    titulo = item.select_one(".DealCardTitle")
                    link = item.select_one("a")["href"] if item.select_one("a") else None
                    preco = item.select_one(".a-price-whole")

                    if titulo and link:
                        produtos.append({
                            "titulo": titulo.get_text(strip=True),
                            "link": f"https://www.amazon.com.br{link}",
                            "preco": preco.get_text(strip=True) if preco else "Preço indisponível"
                        })

                logger.info(f"Encontradas {len(produtos)} promoções.")
                return produtos

    except Exception as e:
        logger.error(f"Erro ao buscar promoções: {e}")
        return []


# Tarefa periódica (a cada 1 minuto)
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    promos = await fetch_promotions()

    if not promos:
        logger.info("Nenhuma promoção válida encontrada.")
        return

    for p in promos:
        msg = f"🔥 *{p['titulo']}*\n💰 {p['preco']}\n🔗 [Ver oferta]({p['link']})"
        try:
            await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown")
            await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")


# Função principal
async def main():
    logger.info("Iniciando bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Agendamento da tarefa automática
    app.job_queue.run_repeating(postar_ofertas, interval=60, first=5)

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("Bot iniciado com sucesso. Aguardando mensagens...")

    await asyncio.Event().wait()  # Mantém o bot ativo


if __name__ == "__main__":
    asyncio.run(main())
