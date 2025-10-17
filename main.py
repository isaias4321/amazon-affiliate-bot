import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot
from scraper import buscar_ofertas_e_enviar

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

# Variáveis de ambiente (você deve defini-las no Railway)
import os
TELEGRAM_BOT_TOKEN = os.getenv("8463817884:AAG1cuPG4l77RFy8l95WsCjj9tp88dRDomE")
GROUP_ID = int(os.getenv("GROUP_ID", "-1003140787649"))
AXESSO_API_KEY = os.getenv("fb2f7fd38c57470489d000c1c7aa8cd6")

# Inicializa o bot do Telegram
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Categorias de busca
CATEGORIAS = [
    "eletrodomesticos",
    "computers",
    "tools"
]

async def ciclo_de_busca(bot):
    """Executa a busca de ofertas em todas as categorias e envia para o Telegram."""
    logger.info("🔄 Iniciando ciclo de busca de ofertas...")

    houve_ofertas = False

    for categoria in CATEGORIAS:
        logger.info(f"🔍 Buscando ofertas na categoria '{categoria}'...")
        try:
            resultados = await buscar_ofertas_e_enviar(bot, GROUP_ID, categoria, AXESSO_API_KEY)
            if resultados:
                houve_ofertas = True
        except Exception as e:
            logger.error(f"❌ Erro ao buscar '{categoria}': {e}")

    if not houve_ofertas:
        logger.info("⚠️ Nenhuma oferta encontrada neste ciclo.")
    else:
        logger.info("✅ Ofertas enviadas com sucesso!")

async def main():
    """Função principal: inicia o bot e o agendador."""
    logger.info("🤖 Iniciando bot *Amazon Ofertas Brasil* (2 em 2 minutos)...")

    scheduler = BackgroundScheduler()

    def agendar_busca():
        asyncio.run(ciclo_de_busca(bot))

    # Agendar o ciclo a cada 2 minutos
    scheduler.add_job(agendar_busca, "interval", minutes=2)
    scheduler.start()

    logger.info("✅ Agendador iniciado. Executando primeira busca agora...")
    await ciclo_de_busca(bot)

    # Mantém o bot rodando indefinidamente
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
