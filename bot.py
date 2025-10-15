import os
import time
import logging
import asyncio
import aiohttp
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ===============================
# 🔧 CONFIGURAÇÕES BÁSICAS
# ===============================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", "")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
RAIN_API_KEY = os.getenv("RAIN_API_KEY", "")

if not TELEGRAM_TOKEN or not GROUP_CHAT_ID or not RAIN_API_KEY:
    logger.error("❌ Variáveis de ambiente ausentes! Verifique TELEGRAM_TOKEN, GROUP_CHAT_ID e RAIN_API_KEY.")
    raise SystemExit("Erro de configuração")

bot = Bot(token=TELEGRAM_TOKEN)

# ===============================
# 🔍 FUNÇÃO: Buscar produtos via Rainforest API
# ===============================
async def buscar_produtos(query: str, limit: int = 3):
    url = (
        f"https://api.rainforestapi.com/request?"
        f"api_key={RAIN_API_KEY}&type=search&amazon_domain=amazon.com.br"
        f"&search_term={query.replace(' ', '+')}&language=pt_BR"
    )

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    logger.warning(f"Erro HTTP {resp.status} ao buscar {query}")
                    return []
                data = await resp.json()
        except Exception as e:
            logger.error(f"Erro ao buscar {query}: {e}")
            return []

    produtos = []
    for item in data.get("search_results", [])[:limit]:
        title = item.get("title")
        link = item.get("link")
        image = item.get("image")
        price = item.get("price", {}).get("raw") if item.get("price") else "N/A"

        if title and link:
            sep = "&" if "?" in link else "?"
            link_afiliado = f"{link}{sep}tag={AFFILIATE_TAG}"
            produtos.append({
                "titulo": title,
                "preco": price,
                "imagem": image,
                "link": link_afiliado,
            })

    return produtos

# ===============================
# 💬 ENVIO PARA O TELEGRAM
# ===============================
async def enviar_oferta(produto: dict, categoria: str):
    legenda = (
        f"🔥 <b>OFERTA AMAZON ({categoria.upper()})</b> 🔥\n\n"
        f"🛒 <b>{produto['titulo']}</b>\n"
        f"💰 <b>Preço:</b> {produto['preco']}\n\n"
        f"👉 <a href=\"{produto['link']}\">Compre com desconto aqui!</a>"
    )

    try:
        await bot.send_photo(
            chat_id=GROUP_CHAT_ID,
            photo=produto["imagem"],
            caption=legenda,
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"✅ Oferta enviada: {produto['titulo']}")
    except Exception as e:
        logger.error(f"Erro ao enviar oferta: {e}")

# ===============================
# 🔁 CICLO PRINCIPAL
# ===============================
async def job_busca_e_envio():
    categorias = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca e envio de ofertas...")

    for categoria in categorias:
        produtos = await buscar_produtos(categoria)
        if not produtos:
            logger.warning(f"Nenhum produto encontrado para {categoria}")
            continue

        for produto in produtos:
            await enviar_oferta(produto, categoria)
            await asyncio.sleep(10)  # Evita flood no Telegram

    logger.info("✅ Ciclo concluído!")

# ===============================
# 🚀 MAIN LOOP
# ===============================
async def main():
    logger.info("🤖 Bot de Ofertas Amazon iniciado com sucesso!")
    logger.info(f"Tag de Afiliado: {AFFILIATE_TAG}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_busca_e_envio, "interval", minutes=2)
    await job_busca_e_envio()  # executa uma vez ao iniciar
    scheduler.start()

    try:
        await asyncio.Future()  # mantém o bot ativo
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("🛑 Bot encerrado.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
