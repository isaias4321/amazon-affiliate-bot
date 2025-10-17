import os
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from scraper import buscar_ofertas_categoria

# === CONFIGURAÇÕES ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")
AXESSO_API_KEY = os.getenv("AXESSO_API_KEY")

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# === CATEGORIAS PARA BUSCA ===
CATEGORIAS = ["eletrodomesticos", "computers", "tools"]

# === CICLO DE BUSCA ===
async def ciclo_de_busca(bot: Bot):
    logging.info("🔄 Iniciando ciclo de busca de ofertas...")

    ofertas_encontradas = []

    for categoria in CATEGORIAS:
        logging.info(f"🔍 Buscando ofertas na categoria '{categoria}'...")
        ofertas = buscar_ofertas_categoria(categoria, AXESSO_API_KEY)
        ofertas_encontradas.extend(ofertas)

    if not ofertas_encontradas:
        logging.info("⚠️ Nenhuma oferta encontrada neste ciclo.")
        return

    logging.info(f"✅ {len(ofertas_encontradas)} ofertas encontradas! Enviando para o grupo...")

    for oferta in ofertas_encontradas:
        try:
            nome = oferta.get("nome", "Sem nome")
            preco = oferta.get("preco", "N/A")
            link = oferta.get("link", "")

            if not link:
                continue

            # Adiciona o link de afiliado
            if "amazon.com.br" in link:
                link = f"{link}?tag={AFFILIATE_TAG}"

            mensagem = (
                f"🔥 *{nome}*\n"
                f"💰 Preço: `{preco}`\n"
                f"🔗 [Ver na Amazon]({link})"
            )

            await bot.send_message(
                chat_id=GROUP_ID,
                text=mensagem,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )

        except Exception as e:
            logging.error(f"❌ Erro ao enviar mensagem: {e}")

    logging.info("📦 Ciclo de envio concluído!")

# === LOOP PRINCIPAL ===
async def main():
    if not TELEGRAM_TOKEN or not GROUP_ID or not AXESSO_API_KEY:
        logging.error("❌ Variáveis de ambiente ausentes! Verifique TELEGRAM_TOKEN, GROUP_ID e AXESSO_API_KEY.")
        return

    bot = Bot(token=TELEGRAM_TOKEN)
    scheduler = AsyncIOScheduler()

    async def agendar_busca():
        await ciclo_de_busca(bot)

    # Executa a cada 2 minutos
    scheduler.add_job(lambda: asyncio.create_task(agendar_busca()), "interval", minutes=2)
    scheduler.start()

    logging.info("🤖 Iniciando bot *Amazon Ofertas Brasil* (2 em 2 minutos)...")
    await agendar_busca()  # primeira execução imediata

    # Mantém o bot rodando
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot finalizado manualmente.")
