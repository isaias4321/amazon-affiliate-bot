import asyncio
import aiohttp
import logging
import os
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from dotenv import load_dotenv
from colorama import Fore, Style, init
from tqdm import tqdm  # 👈 nova dependência: barra de progresso

# Inicializa colorama e dotenv
init(autoreset=True)
load_dotenv()

# Configurações principais
API_URL = "https://amazon-affiliate-bot-production.up.railway.app/buscar"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = -4983279500
AFFILIATE_TAG = "isaias06f-20"

bot = Bot(token=TELEGRAM_TOKEN)
scheduler = AsyncIOScheduler()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CATEGORIAS = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]

# Contador global de ciclos
ciclo_atual = 0

async def buscar_ofertas():
    global ciclo_atual
    ciclo_atual += 1
    inicio = time.strftime("%H:%M:%S")
    logger.info(f"{Fore.CYAN}🔄 Iniciando ciclo {ciclo_atual} às {inicio}...")
    
    async with aiohttp.ClientSession() as session:
        for categoria in tqdm(CATEGORIAS, desc=f"{Fore.YELLOW}Buscando ofertas", colour="green"):
            try:
                async with session.post(API_URL, json={"categoria": categoria}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if "erro" in data:
                            logger.warning(f"{Fore.YELLOW}⚠️ Nenhuma oferta encontrada para {categoria}")
                            continue
                        oferta = data["oferta"]
                        mensagem = (
                            f"🔥 {oferta['titulo']}\n"
                            f"💰 Preço: {oferta['preco']}\n"
                            f"🔗 [Compre aqui]({oferta['link']}?tag={AFFILIATE_TAG})"
                        )
                        await bot.send_message(chat_id=GROUP_ID, text=mensagem, parse_mode="Markdown")
                        logger.info(f"{Fore.GREEN}✅ Enviado: {categoria}")
                    else:
                        logger.warning(f"{Fore.RED}⚠️ Erro HTTP {resp.status} ao buscar {categoria}")
            except Exception as e:
                logger.error(f"{Fore.RED}❌ Erro ao buscar {categoria}: {e}")

    fim = time.strftime("%H:%M:%S")
    logger.info(f"{Fore.MAGENTA}✅ Ciclo {ciclo_atual} concluído! ({inicio} → {fim})")
    logger.info(f"{Fore.BLUE}📊 Total de ciclos executados: {ciclo_atual}\n{Style.RESET_ALL}")

async def main():
    logger.info(f"{Fore.GREEN}🤖 Bot de Ofertas Amazon iniciado com sucesso!")
    logger.info(f"{Fore.BLUE}📡 API em uso: {API_URL}")
    scheduler.add_job(buscar_ofertas, "interval", minutes=15)
    scheduler.start()
    await buscar_ofertas()  # Executa um ciclo imediato
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
