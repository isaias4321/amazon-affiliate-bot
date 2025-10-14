import asyncio
import logging
import aiohttp
import os
import nest_asyncio
from telegram import Bot
from telegram.error import Forbidden
from datetime import datetime
from dotenv import load_dotenv

# Corrige event loop (Railway e Jupyter)
nest_asyncio.apply()

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") or "SEU_TOKEN_AQUI"
GROUP_ID = int(os.getenv("GROUP_ID") or -4983279500)
API_URL = os.getenv("API_URL") or "https://amazon-affiliate-bot-production.up.railway.app"
INTERVAL_MIN = 1  # minutos

# ======================
# BUSCAR PRODUTOS VIA SUA API
# ======================
async def buscar_produtos():
    categorias = ["notebook", "monitor", "mouse", "cadeira gamer", "teclado", "ferramenta", "geladeira"]
    produtos = []

    async with aiohttp.ClientSession() as session:
        for categoria in categorias:
            try:
                async with session.get(f"{API_URL}/api/amazon?query={categoria}") as resp:
                    if resp.status != 200:
                        logger.warning(f"Erro HTTP {resp.status} ao acessar {categoria}")
                        continue
                    data = await resp.json()
                    if "items" in data:
                        produtos.extend(data["items"])
            except Exception as e:
                logger.error(f"Erro ao buscar {categoria}: {e}")

    return produtos

# ======================
# ENVIAR OFERTAS PARA O GRUPO
# ======================
async def postar_ofertas(bot):
    produtos = await buscar_produtos()

    if not produtos:
        logger.warning("Nenhum produto encontrado.")
        return

    for produto in produtos[:3]:
        try:
            nome = produto.get("title", "Produto sem nome")
            preco = produto.get("price", "Preço indisponível")
            imagem = produto.get("image", None)
            link = produto.get("link", "https://amazon.com.br")

            legenda = f"🔥 *{nome}*\n💰 {preco}\n🔗 [Ver na Amazon]({link})"
            
            if imagem:
                await bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=imagem,
                    caption=legenda,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=legenda,
                    parse_mode="Markdown"
                )

            await asyncio.sleep(5)

        except Forbidden:
            logger.error("Bot sem permissão para enviar mensagens no grupo!")
            return
        except Exception as e:
            logger.error(f"Erro ao postar produto: {e}")

# ======================
# LOOP PRINCIPAL
# ======================
async def main():
    bot = Bot(BOT_TOKEN)
    await bot.send_message(chat_id=GROUP_ID, text="🤖 Bot iniciado com sucesso! Buscando ofertas...")

    while True:
        await postar_ofertas(bot)
        logger.info(f"Rodada finalizada às {datetime.now().strftime('%H:%M:%S')}")
        await asyncio.sleep(INTERVAL_MIN * 60)

if __name__ == "__main__":
    asyncio.run(main())
