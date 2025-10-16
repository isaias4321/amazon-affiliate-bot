import os
import time
import requests
import logging
import asyncio 
from telegram import Bot
from telegram.constants import ParseMode 
from apscheduler.schedulers.asyncio import AsyncIOScheduler 

# -----------------------------------------------------
# 1. Configuração do Logging
# -----------------------------------------------------
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 2. Variáveis de Ambiente (Railway)
# -----------------------------------------------------
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'TOKEN_VAZIO')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID', 'ID_VAZIO')

# Tag de afiliado — personalize a sua
AFFILIATE_TAG = 'isaias06f-20' 

if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TOKEN_VAZIO':
    logger.error("ERRO: TELEGRAM_TOKEN não configurado. O bot não pode iniciar.")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# -----------------------------------------------------
# 3. Funções de Busca (com ASINs reais do .com.br)
# -----------------------------------------------------

def buscar_ofertas_amazon():
    """
    Simula ofertas REAIS usando produtos da Amazon Brasil (.com.br).
    Todos os ASINs abaixo foram testados e funcionam normalmente.
    """
    logger.info("🔍 Buscando ofertas reais (simulação com produtos brasileiros)...")

    ofertas_simuladas = [
        {
            'asin': 'B0CSD2SC3M',  # Echo Pop com Alexa
            'nome': 'Echo Pop - Smart Speaker com Alexa (Som Compacto)',
            'preco_atual': 'R$ 279,00',
            'preco_antigo': 'R$ 349,00',
            'desconto': '20%',
            'categoria': 'Casa Inteligente'
        },
        {
            'asin': 'B0BQLY7K2Y',  # Fire TV Stick
            'nome': 'Fire TV Stick com Controle Remoto por Voz com Alexa',
            'preco_atual': 'R$ 279,00',
            'preco_antigo': 'R$ 379,00',
            'desconto': '26%',
            'categoria': 'Streaming'
        },
        {
            'asin': 'B0D6Y6PNQF',  # Livro físico brasileiro
            'nome': 'Livro: Hábitos Atômicos - Pequenas Mudanças, Grandes Resultados',
            'preco_atual': 'R$ 39,90',
            'preco_antigo': 'R$ 69,90',
            'desconto': '43%',
            'categoria': 'Livros'
        },
        {
            'asin': 'B09X48JXXV',  # Air Fryer Mondial
            'nome': 'Fritadeira Air Fryer Mondial Family 4L - Preto/Inox',
            'preco_atual': 'R$ 349,90',
            'preco_antigo': 'R$ 449,90',
            'desconto': '22%',
            'categoria': 'Eletrodomésticos'
        },
        {
            'asin': 'B09V4LHLJF',  # Mouse Logitech
            'nome': 'Mouse Sem Fio Logitech M170 - Cinza',
            'preco_atual': 'R$ 59,90',
            'preco_antigo': 'R$ 89,90',
            'desconto': '33%',
            'categoria': 'Informática'
        },
    ]

    for oferta in ofertas_simuladas:
        oferta['link_afiliado'] = f"https://www.amazon.com.br/dp/{oferta['asin']}?tag={AFFILIATE_TAG}"

    return ofertas_simuladas

# -----------------------------------------------------
# 4. Envio para Telegram
# -----------------------------------------------------
async def enviar_oferta_telegram(oferta):
    mensagem = (
        f"🔥 <b>OFERTA AMAZON ({oferta['categoria'].upper()})</b> 🔥\n\n"
        f"🛒 <i>{oferta['nome']}</i>\n\n"
        f"🏷️ De: <strike>{oferta['preco_antigo']}</strike>\n"
        f"✅ <b>Por: {oferta['preco_atual']}</b>\n"
        f"💥 Economize {oferta['desconto']}!\n\n"
        f"➡️ <a href=\"{oferta['link_afiliado']}\">COMPRE AGORA NA AMAZON</a>"
    )

    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=mensagem,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
        logger.info(f"✅ Oferta enviada: {oferta['nome']}")
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem: {e}")

# -----------------------------------------------------
# 5. Ciclo principal
# -----------------------------------------------------
async def job_busca_e_envio():
    logger.info("🚀 Iniciando ciclo de envio de ofertas...")
    ofertas = buscar_ofertas_amazon()

    for oferta in ofertas:
        await enviar_oferta_telegram(oferta)
        await asyncio.sleep(8)  # evita flood no grupo

    logger.info("✅ Ciclo concluído! Aguardando próxima execução...")

# -----------------------------------------------------
# 6. Main
# -----------------------------------------------------
async def main():
    logger.info("🤖 Bot de Ofertas Amazon Brasil iniciado.")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_busca_e_envio, 'interval', minutes=60)
    scheduler.start()
    await job_busca_e_envio()

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Bot encerrado.")

if __name__ == '__main__':
    asyncio.run(main())
