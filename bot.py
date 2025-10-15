import os
import time
import requests
import logging
# Importação assíncrona necessária para rodar o agendador
import asyncio 
from telegram import Bot
from telegram.constants import ParseMode 
# Mudança para o agendador assíncrono para resolver o RuntimeWarning
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

if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TOKEN_VAZIO':
    logger.error("ERRO: TELEGRAM_TOKEN não configurado. O bot não pode iniciar.")
    exit(1)
    
bot = Bot(token=TELEGRAM_TOKEN)


# -----------------------------------------------------
# 3. Funções de Busca (SIMULAÇÃO)
# -----------------------------------------------------

# A função de busca permanece síncrona, pois só está simulando a lógica.
def buscar_ofertas_amazon():
    """
    SIMULA a busca por ofertas. SUBSTITUA ESTE CÓDIGO pela sua integração real com 
    a Amazon PA API, usando as chaves secretas.
    """
    
    logger.info("Executando a simulação de busca de ofertas na Amazon...")
    
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
    
    for oferta in ofertas_simuladas:
        if '?' in oferta['link_original']:
            oferta['link_afiliado'] = f"{oferta['link_original']}&tag={AFFILIATE_TAG}"
        else:
            oferta['link_afiliado'] = f"{oferta['link_original']}?tag={AFFILIATE_TAG}"
            
    return ofertas_simuladas

# Tornamos a função assíncrona (async) e usamos await
async def enviar_oferta_telegram(oferta):
    """
    Formata e envia a mensagem de oferta para o grupo do Telegram de forma assíncrona.
    """
    
    mensagem = (
        f"🔥 **OFERTA IMPERDÍVEL AMAZON ({oferta['categoria'].upper()})** 🔥\n\n"
        f"🛒 *{oferta['nome']}*\n\n"
        f"🏷️ De: ~{oferta['preco_antigo']}~\n"
        f"✅ **POR APENAS: {oferta['preco_atual']}**\n"
        f"💥 *Economize {oferta['desconto']}!* \n\n"
        f"➡️ [CLIQUE AQUI PARA GARANTIR!]( {oferta['link_afiliado']} )"
    )
    
    try:
        # Usamos await na chamada de send_message para resolver o RuntimeWarning
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False 
        )
        logger.info(f"Oferta enviada: {oferta['nome']}")
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem para o grupo {GROUP_CHAT_ID}. Verifique o ID e se o bot é administrador: {e}")


# -----------------------------------------------------
# 4. Agendamento Principal (Scheduler)
# -----------------------------------------------------

# Tornamos a função assíncrona (async) e usamos await
async def job_busca_e_envio():
    """
    Função chamada pelo agendador. Busca ofertas e as envia.
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
            # time.sleep() não deve ser usado em código assíncrono. Usamos asyncio.sleep.
            await asyncio.sleep(10) 
    else:
        logger.info("Nenhuma oferta significativa encontrada neste ciclo.")

# Usamos async def no main para rodar o agendador assíncrono
async def main():
    """
    Configura o agendador e mantém o programa rodando de forma assíncrona.
    """
    logger.info("Bot de Ofertas Amazon (Railway) iniciando...")
    
    # Cria o agendador assíncrono
    scheduler = AsyncIOScheduler()
    
    # Adiciona a tarefa: executa a função 'job_busca_e_envio' a cada 60 minutos
    scheduler.add_job(job_busca_e_envio, 'interval', minutes=60)
    
    # Executa a primeira vez imediatamente
    await job_busca_e_envio()
    
    # Inicia o agendador
    scheduler.start()
    
    logger.info("Agendador iniciado. Próximo ciclo em 60 minutos.")

    # Loop para manter o worker rodando
    try:
        # Roda o loop de eventos assíncronos
        while True:
            await asyncio.sleep(10)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Bot de Ofertas encerrado.")


if __name__ == '__main__':
    # Roda a função principal assíncrona
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Erro fatal ao iniciar o loop: {e}")
