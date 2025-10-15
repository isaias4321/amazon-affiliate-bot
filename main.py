import os
import logging
import asyncio
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from colorama import Fore, Style
import aiohttp

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
API_URL = os.getenv("API_URL")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
scheduler = AsyncIOScheduler()


async def buscar_produtos_e_enviar():
    termos = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]

    if not API_URL:
        logger.error(f"{Fore.RED}❌ API_URL não configurada!{Style.RESET_ALL}")
        return

    async with aiohttp.ClientSession() as session:
        for termo in termos:
            try:
                async with session.get(f"{API_URL}/buscar", params={"query": termo}, timeout=40) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        produto = data.get("resultado", {})
                        msg = f"💥 *{produto['titulo']}*\n💰 {produto['preco']}\n🔗 [Compre aqui]({produto['link']})"
                        await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown")
                        logger.info(f"{Fore.GREEN}✅ Enviado: {termo}{Style.RESET_ALL}")
                    else:
                        logger.warning(f"{Fore.YELLOW}⚠️ Erro HTTP {resp.status} ao buscar {termo}{Style.RESET_ALL}")
            except Exception as e:
                logger.warning(f"{Fore.RED}❌ Falha ao buscar {termo}: {e}{Style.RESET_ALL}")
    logger.info(f"{Fore.CYAN}✅ Ciclo concluído!{Style.RESET_ALL}")


async def main():
    logger.info(f"{Fore.CYAN}🤖 Iniciando Bot Amazon Affiliate...{Style.RESET_ALL}")
    scheduler.add_job(buscar_produtos_e_enviar, "interval", minutes=10)
    scheduler.start()
    await buscar_produtos_e_enviar()
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
