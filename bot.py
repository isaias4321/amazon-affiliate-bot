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
AFFILIATE_TAG = os.getenv('AFFILIATE_TAG', 'isaias06f-20')

# Inicialização do bot
if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TOKEN_VAZIO':
    logger.error("ERRO: TELEGRAM_TOKEN não configurado. O bot não pode iniciar.")
    exit(1)
    
bot = Bot(token=TELEGRAM_TOKEN)


# -----------------------------------------------------
# 3. Funções de Busca (SIMULAÇÃO)
# -----------------------------------------------------

def buscar_ofertas_amazon():
    """
    SIMULA a busca por ofertas nas categorias desejadas.
    
    ATENÇÃO: ESTE CÓDIGO DEVE SER SUBSTITUÍDO PELA INTEGRAÇÃO REAL COM A AMAZON PA API.
    """
    
    logger.info("Executando a simulação de busca de ofertas na Amazon...")
    
    # Lista de ofertas simuladas
    ofertas_simuladas = [
        {
            'nome': 'NOTEBOOK GAMER: O Mais Potente da Amazon (40% OFF!)',
            'preco_atual': 'R$ 4.299,00',
            'preco_antigo': 'R$ 7.165,00',
            'desconto': '40%',
            'link_original': 'https://www.amazon.com.br/dp/B09V74XXXX', 
            'categoria': 'Notebooks'
        },
        {
            'nome': 'PROCESSADOR HIGH-END: Velocidade Máxima (30% de Desconto)',
            'preco_atual': 'R$ 1.999,90',
            'preco_antigo': 'R$ 2.857,00',
            'desconto': '30%',
            'link_original': 'https://www.amazon.com.br/dp/B08S3XXXX2A',
            'categoria': 'Peças de Computador'
        },
        {
            'nome': 'Kit Chaves de Precisão para Reparos (25% OFF)',
            'preco_atual': 'R$ 99,90',
            'preco_antigo': 'R$ 133,20',
            'desconto': '25%',
            'link_original': 'https://www.amazon.com.br/dp/B07YQXXXXXX',
            'categoria': 'Ferramentas'
        }
    ]
    
    # Adicionando a Tag de Afiliado aos links
    for oferta in ofertas_simuladas:
        if '?' in oferta['link_original']:
            oferta['link_afiliado'] = f"{oferta['link_original']}&tag={AFFILIATE_TAG}"
        else:
            oferta['link_afiliado'] = f"{oferta['link_original']}?tag={AFFILIATE_TAG}"
            
    return ofertas_simuladas

# Agora é uma função assíncrona (async def)
async def enviar_oferta_telegram(oferta):
    """
    Formata e envia a mensagem de oferta para o grupo do Telegram de forma assíncrona.
    """
    
    # Formatação do link para garantir que o bot envie o link e a foto (prévia).
    mensagem = (
        f"🔥 **OFERTA IMPERDÍVEL AMAZON ({oferta['categoria'].upper()})** 🔥\n\n"
        f"🛒 *{oferta['nome']}*\n\n"
        f"🏷️ De: ~{oferta['preco_antigo']}~\n"
        f"✅ **POR APENAS: {oferta['preco_atual']}**\n"
        f"💥 *Economize {oferta['desconto']}!* \n\n"
        f"➡️ [CLIQUE AQUI PARA GARANTIR!]( {oferta['link_afiliado']} )"
    )
    
    try:
        await bot.send_message( 
            chat_id=GROUP_CHAT_ID,
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN,
            # Mantém a prévia da página web (foto do produto) ativada
            disable_web_page_preview=False 
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
            # Pausa assíncrona de 10 segundos entre cada envio de oferta no mesmo ciclo
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
    
    # CORREÇÃO DE FREQUÊNCIA: Executa a cada 2 minutos
    scheduler.add_job(job_busca_e_envio, 'interval', minutes=2)
    
    # Executa a primeira vez imediatamente
    await job_busca_e_envio()
    
    scheduler.start()
    
    # LOG ATUALIZADO
    logger.info("Agendador iniciado. Próximo ciclo em 2 minutos.")

    # Mantém o loop assíncrono rodando infinitamente
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
