import logging
import asyncio
import aiohttp
from telegram import Bot
from telegram.ext import ApplicationBuilder, ContextTypes
from telegram.ext import JobQueue
import os

# ==============================
# CONFIGURAÇÕES DO BOT
# ==============================
BOT_TOKEN = "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A"
GROUP_ID = -4983279500  # ID do grupo
INTERVALO_POSTAGEM = 60  # segundos

# ==============================
# CONFIGURAÇÃO DE LOGS
# ==============================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==============================
# VARIÁVEL GLOBAL DE CONTROLE
# ==============================
ofertas_postadas = set()

# ==============================
# FUNÇÃO PARA BUSCAR OFERTAS
# ==============================
async def buscar_ofertas():
    """
    Simula a busca de ofertas na Amazon.
    Você pode adaptar depois para fazer scraping real.
    """
    ofertas = [
        {
            "titulo": "Fone Bluetooth JBL Tune 510BT",
            "preco": "R$199,00",
            "link": "https://www.amazon.com.br/dp/B08WRN2T3T",
            "imagem": "https://m.media-amazon.com/images/I/61p2vU+fQxL._AC_SL1500_.jpg"
        },
        {
            "titulo": "Echo Dot 5ª Geração",
            "preco": "R$379,00",
            "link": "https://www.amazon.com.br/dp/B09B8V1LZ3",
            "imagem": "https://m.media-amazon.com/images/I/61IxWv3ecpL._AC_SL1000_.jpg"
        },
        {
            "titulo": "Fire TV Stick Lite com Alexa",
            "preco": "R$249,00",
            "link": "https://www.amazon.com.br/dp/B08C1X5JVD",
            "imagem": "https://m.media-amazon.com/images/I/51Kc+7+zZzL._AC_SL1000_.jpg"
        }
    ]
    return ofertas

# ==============================
# FUNÇÃO PARA POSTAR OFERTAS
# ==============================
async def postar_ofertas_automaticamente(context: ContextTypes.DEFAULT_TYPE):
    global ofertas_postadas
    ofertas = await buscar_ofertas()

    if not ofertas:
        logger.warning("Nenhuma oferta encontrada.")
        return

    bot: Bot = context.bot

    for oferta in ofertas:
        # Evita postagens repetidas
        if oferta["link"] in ofertas_postadas:
            continue

        try:
            legenda = (
                f"🔥 <b>{oferta['titulo']}</b>\n"
                f"💰 {oferta['preco']}\n"
                f"👉 <a href='{oferta['link']}'>Compre aqui</a>"
            )

            await bot.send_photo(
                chat_id=GROUP_ID,
                photo=oferta["imagem"],
                caption=legenda,
                parse_mode="HTML"
            )

            # Marca como postada
            ofertas_postadas.add(oferta["link"])
            logger.info(f"Oferta postada: {oferta['titulo']}")

            await asyncio.sleep(3)  # Pausa entre postagens

        except Exception as e:
            logger.error(f"Erro ao postar oferta: {e}")

# ==============================
# FUNÇÃO PRINCIPAL
# ==============================
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Adiciona a tarefa automática
    job_queue = app.job_queue
    job_queue.run_repeating(
        postar_ofertas_automaticamente,
        interval=INTERVALO_POSTAGEM,
        first=5
    )

    logger.info("🤖 Bot de ofertas iniciado com sucesso!")
    await app.run_polling(close_loop=False)

# ==============================
# EXECUTAR BOT
# ==============================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot encerrado manualmente.")
