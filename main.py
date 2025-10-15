import os
import asyncio
import logging
import aiohttp
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# === CONFIGURAÇÕES ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
GROUP_ID = int(os.getenv("GROUP_ID", "-4983279500"))
RAIN_API_KEY = os.getenv("RAIN_API_KEY")  # <- Chave da Rainforest API

CATEGORIAS = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)

# === FUNÇÃO PARA BUSCAR OFERTAS ===
async def buscar_ofertas(session, categoria):
    url = "https://api.rainforestapi.com/request"
    params = {
        "api_key": RAIN_API_KEY,
        "type": "search",
        "amazon_domain": "amazon.com.br",
        "search_term": categoria,
    }

    try:
        async with session.get(url, params=params, timeout=30) as resp:
            if resp.status != 200:
                logger.warning(f"Erro HTTP {resp.status} ao buscar {categoria}")
                return []

            data = await resp.json()
            produtos = []

            for item in data.get("search_results", [])[:5]:
                titulo = item.get("title")
                preco = item.get("price", {}).get("raw", "Preço indisponível")
                imagem = item.get("image")
                link = item.get("link")

                if not titulo or not link:
                    continue

                link_afiliado = f"{link}?tag={AFFILIATE_TAG}"
                produtos.append({
                    "titulo": titulo,
                    "preco": preco,
                    "imagem": imagem,
                    "url": link_afiliado
                })

            return produtos

    except Exception as e:
        logger.error(f"Erro ao buscar {categoria}: {e}")
        return []


# === ENVIO DE OFERTAS ===
async def enviar_ofertas():
    logger.info("🔄 Iniciando ciclo de busca e envio de ofertas...")

    async with aiohttp.ClientSession() as session:
        todas_ofertas = []

        for categoria in CATEGORIAS:
            ofertas = await buscar_ofertas(session, categoria)
            if ofertas:
                todas_ofertas.extend(ofertas)
            else:
                logger.warning(f"Nenhuma oferta encontrada para {categoria}")

        if not todas_ofertas:
            logger.info("Nenhuma oferta encontrada neste ciclo.")
            return

        for oferta in todas_ofertas:
            try:
                msg = f"💥 <b>{oferta['titulo']}</b>\n💰 {oferta['preco']}\n🔗 <a href='{oferta['url']}'>Ver na Amazon</a>"
                await bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=oferta["imagem"],
                    caption=msg,
                    parse_mode="HTML"
                )
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Erro ao enviar oferta: {e}")

    logger.info("✅ Ciclo de envio concluído.")


# === AGENDAMENTO ===
async def job_busca_e_envio():
    await enviar_ofertas()


async def main():
    logger.info("🤖 Bot de Ofertas Amazon iniciado com sucesso!")
    logger.info(f"Tag de Afiliado: {AFFILIATE_TAG}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_busca_e_envio, "interval", minutes=60)
    scheduler.start()

    await enviar_ofertas()  # executa imediatamente

    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
