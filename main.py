import os
import asyncio
import logging
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import buscar_ofertas_e_enviar  # ajuste conforme o nome do seu scraper

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# 🔧 Lendo variáveis de ambiente
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8463817884:AAE23cMr1605qbMV4c79cMcr8F5dn0ETqRo").strip()
GROUP_ID = os.getenv("GROUP_ID", "-1003140787649").strip()
AXESSO_API_KEY = os.getenv("AXESSO_API_KEY", "fb2f7fd38c57470489d000c1c7aa8cd6").strip()

# 🔍 Mostrando token no log (repr mostra se há espaços escondidos)
logging.info(f"🔑 Token detectado: {repr(TELEGRAM_BOT_TOKEN)}")

# 🧠 Verificações de segurança
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ ERRO: Variável TELEGRAM_BOT_TOKEN não encontrada no ambiente!")

if not AXESSO_API_KEY:
    logging.warning("⚠️ Nenhuma AXESSO_API_KEY detectada — a API pode retornar 401 Unauthorized.")

# 🧩 Inicializa o bot
try:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    logging.info("✅ Bot inicializado com sucesso!")
except Exception as e:
    logging.error(f"❌ Erro ao inicializar o bot: {e}")
    raise e


# 🕒 Função principal
async def ciclo_de_busca():
    categorias = ["eletrodomesticos", "computers", "tools"]
    await buscar_ofertas_e_enviar(bot, GROUP_ID, categorias, AXESSO_API_KEY)


def main():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: asyncio.run(ciclo_de_busca()),
        "interval",
        minutes=2  # executa a cada 2 minutos
    )
    scheduler.start()

    logging.info("🤖 Iniciando bot *Amazon Ofertas Brasil* (2 em 2 minutos)...")
    asyncio.run(ciclo_de_busca())

if __name__ == "__main__":
    main()
