import os
import asyncio
import logging
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

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
API_URL = os.getenv("API_URL")

if not BOT_TOKEN or not GROUP_ID or not API_URL:
    logger.error("❌ Variáveis de ambiente ausentes! Verifique BOT_TOKEN, GROUP_ID e API_URL.")
    raise SystemExit("Erro de configuração")

bot = Bot(token=BOT_TOKEN)

# ===============================
# 🔍 FUNÇÃO: Buscar produtos da API própria
# ===============================
async def buscar_produto(categoria: str):
    """Busca 1 produto da categoria informada usando nossa API."""
    url = f"{API_URL}?q={categoria}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Erro HTTP {resp.status} ao buscar {categoria}")
                    return None
                data = await resp.json()
        except Exception as e:
            logger.error(f"Erro ao buscar {categoria}: {e}")
            return None

    # Pega o primeiro produto retornado
    if not data or len(data) == 0:
        logger.warning(f"Nenhum produto encontrado para {categoria}")
        return None

    return data[0]

# ===============================
# 💬 ENVIO PARA O TELEGRAM
# ===============================
async def enviar_oferta(produto: dict, categoria: str):
    """Envia uma oferta formatada com imagem, título e preço para o grupo."""
    titulo = produto.get("titulo") or produto.get("title", "Produto sem título")
    preco = produto.get("preco") or produto.get("price", "N/A")
    imagem = produto.get("imagem") or produto.get("image")
    link = produto.get("link") or produto.get("url")

    legenda = (
        f"🔥 <b>OFERTA AMAZON ({categoria.upper()})</b> 🔥\n\n"
        f"🛒 <b>{titulo}</b>\n"
        f"💰 <b>Preço:</b> {preco}\n\n"
        f"👉 <a href=\"{link}\">Compre com desconto aqui!</a>"
    )

    try:
        await bot.send_photo(
            chat_id=GROUP_ID,
            photo=imagem,
            caption=legenda,
            parse_mode=ParseMode.HTML,
        )
        logger.info(f"✅ Oferta enviada: {titulo}")
    except Exception as e:
        logger.error(f"Erro ao enviar oferta: {e}")

# ===============================
# 🔁 CICLO PRINCIPAL
# ===============================
async def job_busca_envio():
    categorias = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca e envio de ofertas...")

    for categoria in categorias:
        produto = await buscar_produto(categoria)
        if produto:
            await enviar_oferta(produto, categoria)
            await asyncio.sleep(10)  # evita flood no Telegram

    logger.info("✅ Ciclo concluído!")

# ===============================
# 🚀 MAIN LOOP
# ===============================
async def main():
    logger.info("🤖 Bot de Ofertas Amazon iniciado com sucesso!")
    logger.info(f"📡 API em uso: {API_URL}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_busca_envio, "interval", minutes=3)
    await job_busca_envio()  # executa uma vez ao iniciar
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
