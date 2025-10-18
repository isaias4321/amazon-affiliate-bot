import os
import asyncio
import logging
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)
from dotenv import load_dotenv

# ==========================
# CONFIGURAÇÕES E LOGGING
# ==========================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

if not BOT_TOKEN or not GROUP_ID:
    raise ValueError("BOT_TOKEN e GROUP_ID precisam estar definidos.")

bot = Bot(token=BOT_TOKEN)

# ==========================
# FUNÇÕES DE BUSCA
# ==========================

async def safe_get_text(url: str) -> str:
    """Faz requisição segura e retorna HTML como texto."""
    try:
        async with ClientSession() as session:
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    return await response.text()
                logging.warning(f"Erro HTTP {response.status} ao acessar {url}")
                return ""
    except Exception as e:
        logging.error(f"Erro ao acessar {url}: {e}")
        return ""


def parse_amazon_promotions(html: str):
    """Extrai as promoções da página GoldBox da Amazon."""
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    produtos = []

    for item in soup.select("div.dealContainer"):
        titulo = item.select_one("span.dealTitle")
        preco = item.select_one("span.a-price-whole")

        if titulo and preco:
            produtos.append({
                "titulo": titulo.text.strip(),
                "preco": preco.text.strip(),
                "link": "https://www.amazon.com.br" + item.find("a")["href"]
            })

    logging.info(f"Encontradas {len(produtos)} promoções válidas.")
    return produtos


async def fetch_promotions_async():
    """Função assíncrona para buscar promoções."""
    html = await safe_get_text(URL_AMAZON_GOLDBOX)
    return parse_amazon_promotions(html)


# ==========================
# JOB DE POSTAGEM AUTOMÁTICA
# ==========================

async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    """Publica automaticamente promoções no grupo."""
    promotions = await fetch_promotions_async()

    if not promotions:
        logging.info("Nenhuma promoção válida encontrada.")
        return

    for promo in promotions[:5]:  # Limita a 5 promoções por ciclo
        mensagem = (
            f"🔥 *{promo['titulo']}*\n"
            f"💰 Preço: R${promo['preco']}\n"
            f"🔗 [Ver na Amazon]({promo['link']})"
        )
        try:
            await bot.send_message(
                chat_id=GROUP_ID,
                text=mensagem,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem: {e}")


# ==========================
# COMANDO /START
# ==========================

async def start(update, context):
    await update.message.reply_text(
        "🤖 Bot de ofertas Amazon iniciado!\n"
        "As promoções serão publicadas automaticamente a cada minuto."
    )


# ==========================
# FUNÇÃO PRINCIPAL
# ==========================

async def main():
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    # Adiciona comando manual de inicialização
    application.add_handler(CommandHandler("start", start))

    # Agenda a postagem automática de ofertas a cada 60 segundos
    application.job_queue.run_repeating(postar_ofertas, interval=60, first=10)

    logging.info("Bot iniciado com sucesso. Aguardando mensagens...")

    # Garante que não haja conflitos de instâncias
    await bot.delete_webhook(drop_pending_updates=True)
    await application.run_polling(close_loop=False)


# ==========================
# EXECUÇÃO DIRETA
# ==========================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot finalizado manualmente.")
