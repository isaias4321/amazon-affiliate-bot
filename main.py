import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scraper import buscar_ofertas
from sendtotelegram import enviar_mensagem
from keepalive import keep_alive

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A"
GROUP_ID = "-4983279500"
AFFILIATE_TAG = "isaias06f-20"
SCRAPEOPS_API_KEY = "3694ad1e-583c-4a39-bdf9-9de5674814ee"

async def job_buscar_e_enviar():
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    for categoria in categorias:
        ofertas = await buscar_ofertas(categoria, AFFILIATE_TAG, SCRAPEOPS_API_KEY)
        for oferta in ofertas:
            await enviar_mensagem(TELEGRAM_TOKEN, GROUP_ID, oferta)
    logger.info("✅ Ciclo concluído!")

async def main():
    logger.info("🤖 Iniciando bot Amazon Affiliate (promoções reais, ScrapeOps ativo)...")
    keep_alive()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=5)
    await job_buscar_e_enviar()
    scheduler.start()
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
