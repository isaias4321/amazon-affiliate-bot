import asyncio
import logging
import aiohttp
import nest_asyncio
from telegram import Bot, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler
import random
from bs4 import BeautifulSoup

# --------------------------------------------------------
# CONFIGURAÇÕES PRINCIPAIS
# --------------------------------------------------------
BOT_TOKEN = "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A"
CHAT_ID = -4983279500  # grupo onde o bot vai postar
AFILIADO = "isaias06f-20"

# Intervalo de 1 minuto
INTERVALO = 60

# Palavras-chave que o bot deve procurar
CATEGORIAS = [
    "cadeira gamer", "mouse gamer", "monitor", "headset", "gabinete",
    "notebook", "ferramenta", "teclado mecânico", "ssd", "hd externo",
    "smartphone", "fone bluetooth", "tv", "roteador", "impressora"
]

# --------------------------------------------------------
# LOGGING
# --------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------------
# FUNÇÃO PARA BUSCAR PRODUTOS DA AMAZON
# --------------------------------------------------------
async def buscar_produtos():
    produtos = []
    url_base = "https://www.amazon.com.br/s?k="

    async with aiohttp.ClientSession() as session:
        for termo in random.sample(CATEGORIAS, 5):  # busca 5 termos diferentes
            url = f"{url_base}{termo.replace(' ', '+')}"
            try:
                async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                    if resp.status != 200:
                        logger.warning(f"Erro HTTP {resp.status} ao acessar {url}")
                        continue
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")

                    for item in soup.select(".s-result-item"):
                        titulo = item.select_one("h2 a span")
                        preco = item.select_one(".a-price-whole")
                        imagem = item.select_one("img.s-image")
                        link = item.select_one("h2 a")

                        if not (titulo and preco and link and imagem):
                            continue

                        titulo = titulo.text.strip()
                        preco = preco.text.strip()
                        imagem = imagem["src"]
                        link = "https://www.amazon.com.br" + link["href"].split("?")[0]

                        # Evita links de anúncios não afiliados
                        if "/gp/" not in link:
                            link += f"?tag={AFILIADO}"

                        # Exemplo de desconto simulado (não é exato, pois Amazon esconde essa info)
                        desconto = random.choice([10, 15, 20, 25, 30, 35])
                        produtos.append({
                            "titulo": titulo,
                            "preco": preco,
                            "desconto": desconto,
                            "imagem": imagem,
                            "link": link
                        })

            except Exception as e:
                logger.warning(f"Erro ao buscar {termo}: {e}")
                continue

    return produtos

# --------------------------------------------------------
# FUNÇÃO PARA POSTAR AUTOMATICAMENTE
# --------------------------------------------------------
async def postar_ofertas_automaticamente(context):
    bot = context.bot
    produtos = await buscar_produtos()

    if not produtos:
        logger.warning("Nenhum produto encontrado.")
        return

    for produto in produtos[:5]:  # envia até 5 por vez
        legenda = (
            f"🔥 *{produto['titulo']}*\n"
            f"💰 Preço: *R${produto['preco']}* (-{produto['desconto']}%)\n"
            f"🛒 [Compre aqui]({produto['link']})"
        )

        try:
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=produto["imagem"],
                caption=legenda,
                parse_mode="Markdown"
            )
            await asyncio.sleep(5)  # pequeno intervalo entre postagens
        except Exception as e:
            logger.error(f"Erro ao enviar produto: {e}")

# --------------------------------------------------------
# COMANDO /start_posting PARA ATIVAR AS POSTAGENS
# --------------------------------------------------------
async def start_posting(update, context):
    await update.message.reply_text("🤖 Postagens automáticas ativadas a cada 1 minuto.")
    context.job_queue.run_repeating(postar_ofertas_automaticamente, interval=INTERVALO, first=5)

# --------------------------------------------------------
# MAIN - INICIALIZA O BOT
# --------------------------------------------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start_posting", start_posting))

    logger.info("Bot iniciado e aguardando comando /start_posting")
    await app.run_polling()

# --------------------------------------------------------
# EXECUÇÃO CORRIGIDA (para evitar erro de loop)
# --------------------------------------------------------
if __name__ == "__main__":
    nest_asyncio.apply()
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot encerrado manualmente.")
