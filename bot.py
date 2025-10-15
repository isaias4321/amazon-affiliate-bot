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

# DEFINIÇÃO DA TAG DE AFILIADO NO CÓDIGO PARA GARANTIR A LEITURA CORRETA
# ATENÇÃO: SUBSTITUA 'SUA_TAG_REAL_AQUI' pela sua tag de afiliado EXATA (ex: 'isaias06f-20')
AFFILIATE_TAG = 'SUA_TAG_REAL_AQUI' 

# Inicialização do bot
if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TOKEN_VAZIO':
    logger.error("ERRO: TELEGRAM_TOKEN não configurado. O bot não pode iniciar.")
    exit(1)
    
bot = Bot(token=TELEGRAM_TOKEN)


# -----------------------------------------------------
# 3. Funções de Busca (SIMULAÇÃO COM ASINs REAIS)
# -----------------------------------------------------

def buscar_ofertas_amazon():
    """
    SIMULA a busca por ofertas, focando apenas nos dados de texto.
    Usa ASINs de EXEMPLO REAIS para garantir que o link final funcione na Amazon BR.
    """
    
    logger.info("Executando a simulação de busca de ofertas na Amazon...")
    
    # Mapeamento dos dados de simulação com ASINs de EXEMPLO REAIS da Amazon BR
    ofertas_simuladas = [
        {
            # ASIN de Exemplo: Livro "O Poder do Hábito" (B0B13Q4W7P)
            'asin': 'B0B13Q4W7P', 
            'nome': 'Livro: O Poder do Hábito (40% OFF!)',
            'preco_atual': 'R$ 49,90',
            'preco_antigo': 'R$ 83,16',
            'desconto': '40%',
            'categoria': 'Livros'
        },
        {
            # ASIN de Exemplo: Fone de Ouvido Bluetooth (B07T2K9R1Z)
            'asin': 'B07T2K9R1Z',
            'nome': 'Fone de Ouvido Bluetooth TWS (30% de Desconto)',
            'preco_atual': 'R$ 149,90',
            'preco_antigo': 'R$ 214,14',
            'desconto': '30%',
            'categoria': 'Eletrônicos'
        },
        {
            # ASIN de Exemplo: Cafeteira Expresso (B0B7F8JFXC)
            'asin': 'B0B7F8JFXC',
            'nome': 'Cafeteira Expresso Automática (25% OFF)',
            'preco_atual': 'R$ 749,90',
            'preco_antigo': 'R$ 999,87',
            'desconto': '25%',
            'categoria': 'Cozinha'
        }
    ]
    
    # Construímos o link no formato mais seguro: https://www.amazon.com.br/dp/ASIN?tag=SUATAG
    for oferta in ofertas_simuladas:
        oferta['link_afiliado'] = f"https://www.amazon.com.br/dp/{oferta['asin']}?tag={AFFILIATE_TAG}"
            
    return ofertas_simuladas

# Usa send_message (apenas texto)
async def enviar_oferta_telegram(oferta):
    """
    Formata e envia a mensagem de oferta para o grupo do Telegram usando formatação HTML.
    """
    
    # FORMATANDO USANDO SINTAXE HTML
    mensagem = (
        f"🔥 <b>OFERTA IMPERDÍVEL AMAZON ({oferta['categoria'].upper()})</b> 🔥\n\n"
        f"🛒 <i>{oferta['nome']}</i>\n\n"
        f"🏷️ De: <strike>{oferta['preco_antigo']}</strike>\n"
        f"✅ <b>POR APENAS: {oferta['preco_atual']}</b>\n"
        f"💥 <i>Economize {oferta['desconto']}!</i> \n\n"
        f"➡️ <a href=\"{oferta['link_afiliado']}\">CLIQUE AQUI PARA GARANTIR!</a>"
    )
    
    try:
        await bot.send_message( 
            chat_id=GROUP_CHAT_ID,
            text=mensagem,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True 
        )
        logger.info(f"Oferta enviada: {oferta['nome']}")
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem para o grupo {GROUP_CHAT_ID}. Verifique o ID e se o bot é administrador: {e}")


# -----------------------------------------------------
# 4. Agendamento Principal (Async Scheduler)
# -----------------------------------------------------

async def job_busca_e_envio():
    """
    Função assíncrona chamada pelo agendador. Busca ofertas e as envia.
    """
    if GROUP_CHAT_ID == 'ID_VAZIO':
        logger.error("GROUP_CHAT_ID não configurado. Ignorando envio.")
        return
        
    logger.info("Iniciando ciclo de busca e envio de ofertas.")
    
    ofertas = buscar_ofertas_amazon() 
    
    if ofertas:
        logger.info(f"Encontradas {len(ofertas)} ofertas.")
        for oferta in ofertas:
            await enviar_oferta_telegram(oferta) 
            await asyncio.sleep(10) 
    else:
        logger.info("Nenhuma oferta significativa encontrada neste ciclo.")

async def main():
    """
    Configura o agendador assíncrono e mantém o loop rodando.
    """
    logger.info("Bot de Ofertas Amazon (Railway) iniciando...")
    logger.info(f"Tag de Afiliado: {AFFILIATE_TAG}")
    
    scheduler = AsyncIOScheduler() 
    
    # Frequência: 2 minutos
    scheduler.add_job(job_busca_e_envio, 'interval', minutes=2)
    
    # Executa a primeira vez imediatamente
    await job_busca_e_envio()
    
    scheduler.start()
    
    logger.info("Agendador iniciado. Próximo ciclo em 2 minutos.")

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Bot de Ofertas encerrado.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Erro fatal ao iniciar o loop asyncio: {e}")
