import os
import asyncio
import logging
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from dotenv import load_dotenv

# === Configurações de log colorido ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# === Carregar variáveis de ambiente ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")
API_URL = os.getenv("API_URL")

# === Verificar se tudo foi carregado ===
logger.info("🔍 Verificando variáveis de ambiente...")
for var_name, var_value in {
    "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
    "GROUP_ID": GROUP_ID,
    "AFFILIATE_TAG": AFFILIATE_TAG,
    "API_URL": API_URL,
}.items():
    if not var_value:
        logger.error(f"❌ Variável ausente: {var_name}")
    else:
        logger.info(f"✅ {var_name} = {var_value}")

# === Inicializar bot ===
bot = Bot(token=TELEGRAM_TOKEN)

# === Função para buscar produtos ===
async def buscar_produto(categoria: str):
    url = f"{API_URL}?q={categoria}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Erro HTTP {resp.status} ao buscar {categoria}")
                    return None
                data = await resp.json()
                logger.info(f"✅ {categoria} retornou dados: {data}")
                return data
        except Exception as e:
            logger.error(f"❌ Erro ao buscar {categoria}: {e}")
            return None

# === Função principal de busca + envio ===
async def enviar_ofertas():
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca e envio de ofertas...")

    for categoria in categorias:
        produto = await buscar_produto(categoria)
        if not produto:
            logger.warning(f"⚠️ Nenhum produto encontrado para {categoria}")
            continue

        try:
            mensagem = f"🔥 *{produto['titulo']}*\n💰 {produto['preco']}\n🔗 {produto['link']}"
            await bot.send_message(chat_id=GROUP_ID, text=mensagem, parse_mode="Markdown")
            logger.info(f"✅ Oferta enviada: {categoria}")
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem para {categoria}: {e}")

    logger.info("✅ Ciclo concluído!")

# === Iniciar agendador ===
scheduler = AsyncIOScheduler()
scheduler.add_job(enviar_ofertas, "interval", minutes=5)
scheduler.start()

# === Loop principal ===
async def main():
    logger.info("🤖 Bot Amazon Affiliate iniciado e monitorando ofertas...")
    await enviar_ofertas()
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
