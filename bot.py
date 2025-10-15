import os
import time
import requests
import logging
# -------------------------------------------------------------------------
# CORREÇÃO AQUI:
from telegram import Bot
from telegram.constants import ParseMode 
# -------------------------------------------------------------------------
from apscheduler.schedulers.background import BackgroundScheduler

# -----------------------------------------------------
# 1. Configuração do Logging
# -----------------------------------------------------
# Configura o log para exibir informações de tempo e nível
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 2. Variáveis de Ambiente (Railway)
# -----------------------------------------------------
# O bot.py irá buscar estas variáveis que você configurou no painel do Railway.
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID', '-4983279500')
AFFILIATE_TAG = os.getenv('AFFILIATE_TAG', 'isaias06f-20')

# OBS: As chaves da Amazon PA API (ACCESS_KEY e SECRET_KEY) deveriam ser
# carregadas aqui, mas estamos usando dados simulados.
# PAAPI_ACCESS_KEY = os.getenv('PAAPI_ACCESS_KEY')
# PAAPI_SECRET_KEY = os.getenv('PAAPI_SECRET_KEY')

# Inicialização do bot
bot = Bot(token=TELEGRAM_TOKEN)


# -----------------------------------------------------
# 3. Funções de Busca (SIMULAÇÃO)
# -----------------------------------------------------

# A função abaixo SIMULA a busca e geração de ofertas.
# VOCÊ DEVE SUBSTITUÍ-LA PELA INTEGRAÇÃO REAL COM A AMAZON PA API.
def buscar_ofertas_amazon():
    """
    SIMULA a busca por ofertas nas categorias desejadas.
    Esta função DEVE ser substituída pela integração real com a Amazon PA API.
    A integração real precisa:
    1. Usar as chaves PAAPI_ACCESS_KEY e PAAPI_SECRET_KEY.
    2. Filtrar produtos das categorias (Ferramentas, PC, Notebook, Celular, Eletrodoméstico).
    3. Garantir que o link gerado contenha o AFFILIATE_TAG.
    """
    
    logger.info("Executando a simulação de busca de ofertas na Amazon...")
    
    # Lista de ofertas simuladas que seriam retornadas pela PA API
    ofertas_simuladas = [
        {
            'nome': 'Notebook Gamer Ultra Rápido (40% OFF!)',
            'preco_atual': 'R$ 4.299,00',
            'preco_antigo': 'R$ 7.165,00',
            'desconto': '40%',
            'link_original': 'https://www.amazon.com.br/dp/B09V74XXXX', # ASIN de exemplo
            'categoria': 'Notebooks'
        },
        {
            'nome': 'Processador High-End (30% de Desconto)',
            'preco_atual': 'R$ 1.999,90',
            'preco_antigo': 'R$ 2.857,00',
            'desconto': '30%',
            'link_original': 'https://www.amazon.com.br/dp/B08S3XXX2A', # ASIN de exemplo
            'categoria': 'Peças de Computador'
        }
        # Adicione mais ofertas simuladas aqui
    ]
    
    # Adicionando a Tag de Afiliado aos links
    for oferta in ofertas_simuladas:
        # Cria o link de afiliado final com a tag
        if '?' in oferta['link_original']:
            oferta['link_afiliado'] = f"{oferta['link_original']}&tag={AFFILIATE_TAG}"
        else:
            oferta['link_afiliado'] = f"{oferta['link_original']}?tag={AFFILIATE_TAG}"
            
    # Na simulação, vamos retornar apenas uma oferta a cada ciclo
    if time.time() % 2 == 0:
        return ofertas_simuladas
    else:
        return []

def enviar_oferta_telegram(oferta):
    """
    Formata e envia a mensagem de oferta para o grupo do Telegram.
    """
    
    mensagem = (
        f"🔥 **OFERTA QUENTE AMAZON - {oferta['categoria'].upper()}** 🔥\n\n"
        f"🛒 *{oferta['nome']}*\n\n"
        f"🏷️ De: ~{oferta['preco_antigo']}~\n"
        f"✅ **Por Apenas: {oferta['preco_atual']}**\n"
        f"💥 *Economize {oferta['desconto']}!* \n\n"
        f"➡️ [CLIQUE AQUI PARA GARANTIR! (Afiliado)]( {oferta['link_afiliado']} )"
    )
    
    try:
        # Tenta enviar a mensagem para o grupo
        bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=mensagem,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False # Permite a prévia da imagem/link da Amazon
        )
        logger.info(f"Oferta enviada: {oferta['nome']}")
    except Exception as e:
        logger.error(f"Erro ao enviar mensagem para o grupo {GROUP_CHAT_ID}: {e}")
        # Uma causa comum é o bot não ser administrador no grupo/canal.


# -----------------------------------------------------
# 4. Agendamento Principal (Scheduler)
# -----------------------------------------------------

def job_busca_e_envio():
    """
    Função chamada pelo agendador. Busca ofertas e as envia.
    """
    logger.info("Iniciando ciclo de busca e envio de ofertas.")
    
    ofertas = buscar_ofertas_amazon()
    
    if ofertas:
        for oferta in ofertas:
            enviar_oferta_telegram(oferta)
            # Pausa entre os envios para evitar spam e limites de taxa do Telegram
            time.sleep(5) 
    else:
        logger.info("Nenhuma oferta significativa encontrada neste ciclo.")

def main():
    """
    Configura o agendador e mantém o programa rodando.
    """
    logger.info("Bot de Ofertas Amazon (Railway) iniciado.")
    logger.info(f"Target Group ID: {GROUP_CHAT_ID}")
    
    # Cria o agendador
    scheduler = BackgroundScheduler()
    
    # Adiciona a tarefa: executa a função 'job_busca_e_envio' a cada 30 minutos
    # Altere 'minutes=30' para o intervalo desejado (ex: hours=1)
    scheduler.add_job(job_busca_e_envio, 'interval', minutes=30)
    
    # Inicia o agendador
    scheduler.start()
    
    logger.info("Agendador iniciado. Próximo ciclo em 30 minutos.")

    # Loop infinito para manter o bot rodando no Railway
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        # Desliga o agendador de forma limpa
        scheduler.shutdown()
        logger.info("Bot de Ofertas encerrado.")


if __name__ == '__main__':
    # Pequena pausa para garantir que o Railway inicialize
    time.sleep(10)
    main()
