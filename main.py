import os
import time
import logging
import asyncio
import aiohttp
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from colorama import Fore, Style, init

# ===============================
# 🎨 Inicializa cores no terminal
# ===============================
init(autoreset=True)

# ===============================
# 🔧 CONFIGURAÇÕES BÁSICAS
# ===============================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ✅ Lendo variáveis de ambiente
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GROUP_ID = os.getenv("GROUP_ID", "")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
API_URL = os.getenv("API_URL", "")

# ===============================
# 🧩 Verificação das variáveis
# ===============================
print(Fore.CYAN + "===============================")
print(Fore.CYAN + "🔍 VERIFICAÇÃO DE VARIÁVEIS DE AMBIENTE")
print(Fore.CYAN + "===============================")
print(Fore.YELLOW + f"BOT_TOKEN: {'OK ✅' if BOT_TOKEN else '❌ VAZIO'}")
print(Fore.YELLOW + f"GROUP_ID: {'OK ✅' if GROUP_ID else '❌ VAZIO'}")
print(Fore.YELLOW + f"AFFILIATE_TAG: {AFFILIATE_TAG}")
print(Fore.YELLOW + f"API_URL: {API_URL or '❌ VAZIO'}")
print(Fore.CYAN + "===============================" + Style.RESET_ALL)

if not BOT_TOKEN or not GROUP_ID or not API_URL:
    logger.error("❌ Variáveis de ambiente ausentes! Verifique BOT_TOKEN, GROUP_ID e API_URL.")
    raise SystemExit("Erro de configuração")

# Inicializa o bot
bot = Bot(token=BOT_TOKEN)

# ===============================
# 🔍 FUNÇÃO: Buscar produto via API
# ===============================
async def buscar_produto(categoria: str):
    """Busca 1 produto da categoria informada usando a API personalizada."""
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

    if not data or "titulo" not in data:
        logger.warning(f"Nenhum produto válido retornado para {categoria}")
        return None

    return data

# ===============================
# 💬 ENVIO DE OFERTA PARA TELEGRAM
# ===============================
async def enviar_oferta(produto: dict, categoria: str):
    legenda = (
        f"🔥 <b>OFERTA AMAZON ({categoria.upper()})</b> 🔥\n\n"
        f"🛒 <b>{produto['titulo']}</b>\n"
        f"💰 <b>Preço:</b> {produto.get('preco', 'N/A')}\n\n"
        f"👉 <a href=\"{produto['link']}\">Compre com desconto aqui!</a>"
    )

    try:
        await bot.send_photo(
            chat_id=GROUP_ID,
            photo=produto["imagem"],
            caption=legenda,
            parse_mode=ParseMode.HTML,
        )
        print(Fore.GREEN + f"✅ Oferta enviada: {produto['titulo']}")
    except Exception as e:
        print(Fore.RED + f"Erro ao enviar oferta: {e}")

# ===============================
# 🔁 CICLO PRINCIPAL DE ENVIO
# ===============================
async def job_busca_envio():
    categorias = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]
    print(Fore.MAGENTA + "🔄 Iniciando ciclo de busca e envio de ofertas...")

    for categoria in categorias:
        produto = await buscar_produto(categoria)
        if produto:
            await enviar_oferta(produto, categoria)
            await asyncio.sleep(10)  # Evita flood no Telegram
        else:
            logger.warning(f"Nenhum produto encontrado para {categoria}")

    print(Fore.GREEN + "✅ Ciclo concluído!\n")

# ===============================
# 🚀 LOOP PRINCIPAL
# ===============================
async def main():
    print(Fore.GREEN + "🤖 Bot de Ofertas Amazon iniciado com sucesso!")
    print(Fore.CYAN + f"📡 API em uso: {API_URL}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_busca_envio, "interval", minutes=2)
    await job_busca_envio()  # executa uma vez ao iniciar
    scheduler.start()

    try:
        await asyncio.Future()  # mantém o bot ativo
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print(Fore.RED + "🛑 Bot encerrado.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(Fore.RED + f"❌ Erro fatal: {e}")
