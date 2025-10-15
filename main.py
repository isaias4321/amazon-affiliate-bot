import os
import asyncio
import logging
import aiohttp
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from colorama import Fore, Style, init

# Inicializa cor no terminal
init(autoreset=True)

# Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Variáveis de ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
API_URL = os.getenv("API_URL")  # URL da tua API no Railway

# Verificação das variáveis
logger.info(Fore.CYAN + "🔍 Verificando variáveis de ambiente..." + Style.RESET_ALL)

if TELEGRAM_TOKEN:
    logger.info(Fore.GREEN + f"✅ TELEGRAM_TOKEN = {TELEGRAM_TOKEN}" + Style.RESET_ALL)
else:
    logger.error(Fore.RED + "❌ TELEGRAM_TOKEN ausente!" + Style.RESET_ALL)

if GROUP_ID:
    logger.info(Fore.GREEN + f"✅ GROUP_ID = {GROUP_ID}" + Style.RESET_ALL)
else:
    logger.error(Fore.RED + "❌ GROUP_ID ausente!" + Style.RESET_ALL)

if AFFILIATE_TAG:
    logger.info(Fore.GREEN + f"✅ AFFILIATE_TAG = {AFFILIATE_TAG}" + Style.RESET_ALL)
else:
    logger.warning(Fore.YELLOW + "⚠️ AFFILIATE_TAG não definida, usando padrão 'isaias06f-20'" + Style.RESET_ALL)

if API_URL:
    logger.info(Fore.GREEN + f"✅ API_URL = {API_URL}" + Style.RESET_ALL)
else:
    logger.error(Fore.RED + "❌ Variável ausente: API_URL" + Style.RESET_ALL)

# Inicializa bot do Telegram
bot = Bot(token=TELEGRAM_TOKEN)

# Categorias para busca
CATEGORIAS = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]

# ---------------------------------
# Função de busca e envio
# ---------------------------------
async def buscar_produtos(categoria: str):
    """Busca produtos da API e retorna lista."""
    if not API_URL:
        logger.error(Fore.RED + "❌ API_URL não configurada!" + Style.RESET_ALL)
        return []

    url = f"{API_URL}/ofertas?q={categoria}"
    for tentativa in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=40) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        produtos = data.get("produtos", [])
                        if produtos:
                            logger.info(Fore.GREEN + f"✅ {len(produtos)} produtos encontrados para '{categoria}'" + Style.RESET_ALL)
                        else:
                            logger.warning(Fore.YELLOW + f"⚠️ Nenhum produto encontrado para '{categoria}'" + Style.RESET_ALL)
                        return produtos
                    else:
                        logger.warning(Fore.RED + f"⚠️ Erro HTTP {resp.status} ao buscar '{categoria}'" + Style.RESET_ALL)
        except Exception as e:
            logger.error(Fore.RED + f"❌ Erro ao buscar '{categoria}': {e}" + Style.RESET_ALL)

        espera = 2 * (tentativa + 1)
        logger.info(Fore.CYAN + f"🔁 Tentando novamente em {espera}s..." + Style.RESET_ALL)
        await asyncio.sleep(espera)

    return []


async def enviar_ofertas():
    """Busca e envia ofertas ao grupo."""
    logger.info(Fore.MAGENTA + "🔄 Iniciando ciclo de busca e envio de ofertas..." + Style.RESET_ALL)
    for categoria in CATEGORIAS:
        produtos = await buscar_produtos(categoria)

        if not produtos:
            continue

        for p in produtos[:3]:  # Envia os 3 primeiros
            msg = f"🔥 *{p['titulo']}*\n💰 {p['preco']}\n🔗 [Ver na Amazon]({p['url']})"
            try:
                await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown")
                logger.info(Fore.GREEN + f"📤 Enviado: {p['titulo'][:40]}..." + Style.RESET_ALL)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(Fore.RED + f"❌ Falha ao enviar mensagem: {e}" + Style.RESET_ALL)

    logger.info(Fore.GREEN + "✅ Ciclo concluído!" + Style.RESET_ALL)


# ---------------------------------
# Scheduler (executa a cada 30 min)
# ---------------------------------
scheduler = AsyncIOScheduler()
scheduler.add_job(enviar_ofertas, "interval", minutes=30)
scheduler.start()

# ---------------------------------
# Loop principal
# ---------------------------------
async def main():
    logger.info(Fore.GREEN + "🤖 Bot Amazon Affiliate iniciado e monitorando ofertas..." + Style.RESET_ALL)
    await enviar_ofertas()  # Executa logo ao iniciar

if __name__ == "__main__":
    asyncio.run(main())
