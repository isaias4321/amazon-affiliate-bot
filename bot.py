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
# 3. Funções de Busca (SIMULAÇÃO) - CORRIGIDO PARA INCLUIR IMAGEM
# -----------------------------------------------------

def buscar_ofertas_amazon():
    """
    SIMULA a busca por ofertas nas categorias desejadas.
    Adiciona uma URL de imagem simulada para que o bot possa enviar a foto.
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
            'categoria': 'Notebooks',
            # URL de Imagem SIMULADA. TROQUE POR UMA REAL PARA TESTES!
            'imagem_url': 'https://m.media-amazon.com/images/I/71Yt4rVn-pL._AC_SX679_.jpg' 
        },
        {
            'nome': 'PROCESSADOR HIGH-END: Velocidade Máxima (30% de Desconto)',
            'preco_atual': 'R$ 1.999,90',
            'preco_antigo': 'R$ 2.857,00',
            'desconto': '30%',
            'link_original': 'https://www.amazon.com.br/dp/B08S3XXXX2A',
            'categoria': 'Peças de Computador',
            # URL de Imagem SIMULADA. TROQUE POR UMA REAL PARA TESTES!
            'imagem_url': 'https://m.media-amazon.com/images/I/71Yt4rVn-pL._AC_SX679_.jpg'
        },
        {
            'nome': 'Kit Chaves de Precisão para Reparos (25% OFF)',
            'preco_atual': 'R$ 99,90',
            'preco_antigo': 'R$ 133,20',
            'desconto': '25%',
            'link_original': 'https://www.amazon.com.br/dp/B07YQXXXXXX',
            'categoria': 'Ferramentas',
            # URL de Imagem SIMULADA. TROQUE POR UMA REAL PARA TESTES!
            'imagem_url': 'https://m.media-amazon.com/images/I/71Yt4rVn-pL._AC_SX679_.jpg'
        }
    ]
    
    # Adicionando a Tag de Afiliado aos links
    for oferta in ofertas_simuladas:
        if '?' in oferta['link_original']:
            oferta['link_afiliado'] = f"{oferta['link_original']}&tag={AFFILIATE_TAG}"
        else:
            oferta['link_afiliado'] = f"{oferta['link_original']}?tag={AFFILIATE_TAG}"
            
    return ofertas_simuladas

# ALTERADO: Agora usa send_photo
async def enviar_oferta_telegram(oferta):
    """
    Envia a foto (imagem_url) com o texto formatado como legenda (caption).
    """
    
    # FORMATANDO O TEXTO PARA SER A LEGENDA DA FOTO (CAPTION)
    mensagem = (
        f"🔥 <b>OFERTA IMPERDÍVEL AMAZON ({oferta['categoria'].upper()})</b> 🔥\n\n"
        f"🛒 <i>{oferta['nome']}</i>\n\n"
        f"🏷️ De: <strike>{oferta['preco_antigo']}</strike>\n"
        f"✅ <b>POR APENAS: {oferta['preco_atual']}</b>\n"
        f"💥 <i>Economize {oferta['desconto']}!</i> \n\n"
        # Link Clicável: A tag HTML <a> garante a formatação
        f"➡️ <a href=\"{oferta['link_afiliado']}\">CLIQUE AQUI PARA GARANTIR!</a>"
    )
    
    try:
        # CRUCIAL: Uso de send_photo com a URL da imagem e o texto como legenda
        await bot.send_photo( 
            chat_id=GROUP_CHAT_ID,
            photo=oferta['imagem_url'], # O Telegram baixa e envia a imagem dessa URL
            caption=mensagem,          # O texto formatado vai como legenda da foto
            parse_mode=ParseMode.HTML, # Mantemos o HTML para a legenda
        )
        logger.info(f"Oferta enviada: {oferta['nome']}")
    except Exception as e:
        logger.error(f"Erro ao enviar FOTO/mensagem para o grupo {GROUP_CHAT_ID}: {e}")
        # Tenta enviar apenas o texto em caso de falha de envio da foto (ex: URL inválida)
        await bot.send_message(chat_id=GROUP_CHAT_ID, text=mensagem, parse_mode=ParseMode.HTML)


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
    
    # Frequência: 2 minutos
    scheduler.add_job(job_busca_e_envio, 'interval', minutes=2)
    
    # Executa a primeira vez imediatamente
    await job_busca_e_envio()
    
    scheduler.start()
    
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
