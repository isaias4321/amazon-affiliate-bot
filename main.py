import asyncio
import logging
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scraper import buscar_ofertas_e_enviar

# Configurações principais
TELEGRAM_BOT_TOKEN = "8463817884:AAE23cMr1605qbMV4c79cMcr8F5dn0ETqRo"
GROUP_ID = "-1003140787649"
AXESSO_API_KEY = "59ce64518d90456d95ad55f293bb877e"

# Categorias a serem monitoradas
CATEGORIAS = ["eletrodomesticos", "computers", "tools"]

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

async def ciclo_de_busca(bot):
    logging.info("🔄 Iniciando ciclo de busca de ofertas...")
    await buscar_ofertas_e_enviar(bot, GROUP_ID, CATEGORIAS, AXESSO_API_KEY)

async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    scheduler = AsyncIOScheduler()

    # Primeira execução imediata
    await ciclo_de_busca(bot)

    # Agendamento a cada 2 minutos
    scheduler.add_job(lambda: asyncio.create_task(ciclo_de_busca(bot)), "interval", minutes=2)
    scheduler.start()

    logging.info("🤖 Iniciando bot *Amazon Ofertas Brasil* (2 em 2 minutos)...")

    # Mantém o bot rodando
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
