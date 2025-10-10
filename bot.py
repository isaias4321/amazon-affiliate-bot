import asyncio
import logging
import random
import re
from bs4 import BeautifulSoup
import aiohttp
from telegram import Bot
from telegram.ext import Application, CommandHandler

# ==========================
# CONFIGURAÇÕES DO BOT
# ==========================
BOT_TOKEN = "SEU_TOKEN_AQUI"
CHAT_ID = "-4983279500"  # ID do seu grupo
AFILIADO = "isaias06f-20"
INTERVALO_MINUTOS = 2  # tempo entre postagens automáticas

# ==========================
# LOG
# ==========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================
# URLs de CATEGORIAS
# ==========================
urls = [
    "https://www.amazon.com.br/gp/browse.html?node=16243862011",  # Eletrônicos
    "https://www.amazon.com.br/gp/browse.html?node=16364755011",  # Games
    "https://www.amazon.com.br/gp/browse.html?node=16243890011"   # Computadores
]

# ==========================
# BUSCAR PRODUTOS COM DESCONTO
# ==========================
async def buscar_produtos_com_desconto():
    produtos = []

    async with aiohttp.ClientSession() as session:
        for url in urls:
            try:
                async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as response:
                    if response.status != 200:
                        logger.warning(f"Erro HTTP {response.status} ao acessar {url}")
                        continue
                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    for produto in soup.select(".s-result-item"):
                        titulo = produto.select_one("h2 a span")
                        preco = produto.select_one(".a-price-whole")
                        link = produto.select_one("h2 a")
                        imagem = produto.select_one("img")
                        preco_antigo = produto.select_one(".a-text-price span")

                        if not (titulo and preco and link):
                            continue

                        titulo = titulo.text.strip()
                        preco = preco.text.strip()
                        link = link["href"]
                        if not link.startswith("http"):
                            link = f"https://www.amazon.com.br{link}"
                        imagem_url = imagem["src"] if imagem else None

                        # Cálculo do desconto (se houver preço antigo)
                        desconto = None
                        if preco_antigo:
                            try:
                                preco_antigo_val = float(re.sub(r"[^\d]", "", preco_antigo.text)) / 100
                                preco_atual_val = float(re.sub(r"[^\d]", "", preco)) / 100
                                if preco_antigo_val > preco_atual_val:
                                    desconto = int(100 - (preco_atual_val / preco_antigo_val * 100))
                            except:
                                pass

                        # Só adiciona se tiver desconto
                        if desconto and desconto >= 5:
                            produtos.append({
                                "titulo": titulo,
                                "preco": preco,
                                "desconto": desconto,
                                "link": f"{link}?tag={AFILIADO}",
                                "imagem": imagem_url
                            })
            except Exception as e:
                logger.warning(f"Erro ao buscar em {url}: {e}")

    return produtos

# ==========================
# POSTAR NO TELEGRAM
# ==========================
async def postar_produto(bot: Bot, produto: dict):
    mensagem = (
        f"🔥 <b>{produto['titulo']}</b>\n"
        f"💰 Preço: R$ {produto['preco']}  (-{produto['desconto']}%)\n\n"
        f"🛒 <a href='{produto['link']}'>Ver na Amazon</a>"
    )

    try:
        if produto["imagem"]:
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=produto["imagem"],
                caption=mensagem,
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=mensagem,
                parse_mode="HTML",
            )
    except Exception as e:
        logger.error(f"Erro ao postar produto: {e}")

# ==========================
# LOOP AUTOMÁTICO
# ==========================
async def loop_postagens(bot: Bot):
    logger.info("Loop de postagens iniciado.")
    while True:
        produtos = await buscar_produtos_com_desconto()
        if not produtos:
            logger.info("Nenhum produto com desconto encontrado. Tentando novamente em breve.")
        else:
            produto = random.choice(produtos)
            await postar_produto(bot, produto)
            logger.info(f"Produto postado: {produto['titulo']}")
        await asyncio.sleep(INTERVALO_MINUTOS * 60)

# ==========================
# COMANDO /start_posting
# ==========================
async def start_posting(update, context):
    await update.message.reply_text("🚀 Postagens automáticas ativadas a cada 2 minutos!")
    bot = context.bot
    asyncio.create_task(loop_postagens(bot))

# ==========================
# MAIN
# ==========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start_posting", start_posting))
    app.run_polling()

if __name__ == "__main__":
    main()
