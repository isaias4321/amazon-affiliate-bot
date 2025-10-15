import os
import time
import requests
import logging
import asyncio 
from telegram import Bot
from telegram.constants import ParseMode 
from apscheduler.schedulers.asyncio import AsyncIOScheduler 

# NOVO: Importa a biblioteca da Amazon PA API
from paapi5_python_sdk.api.default_api import DefaultApi
from paapi5_python_sdk.models.search_items_request import SearchItemsRequest
from paapi5_python_sdk.models.search_items_resource import SearchItemsResource
from paapi5_python_sdk.models.partner_type import PartnerType

# -----------------------------------------------------
# 1. Configuração do Logging
# -----------------------------------------------------
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 2. Variáveis de Ambiente (Railway) - NOVAS CHAVES DA AMAZON
# -----------------------------------------------------
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'TOKEN_VAZIO')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID', 'ID_VAZIO')
AFFILIATE_TAG = os.getenv('AFFILIATE_TAG', 'isaias06f-20') # Usado no link final
# CHAVES DA AMAZON PA API (Configure no Railway!)
PAAPI_ACCESS_KEY = os.getenv('PAAPI_ACCESS_KEY', 'CHAVE_VAZIA')
PAAPI_SECRET_KEY = os.getenv('PAAPI_SECRET_KEY', 'SECRETO_VAZIO')
PAAPI_PARTNER_TAG = os.getenv('PAAPI_PARTNER_TAG', AFFILIATE_TAG) # Sua tag de afiliado principal

# Configurações regionais
HOST = 'webservices.amazon.com.br'  # Para o Brasil
REGION = 'us-east-1'              # Região de serviço da API para o Brasil

# Inicialização do bot
if not TELEGRAM_TOKEN or TELEGRAM_TOKEN == 'TOKEN_VAZIO':
    logger.error("ERRO: TELEGRAM_TOKEN não configurado. O bot não pode iniciar.")
    exit(1)
    
bot = Bot(token=TELEGRAM_TOKEN)


# -----------------------------------------------------
# 3. Funções de Busca (INTEGRAÇÃO REAL COM PA API)
# -----------------------------------------------------

def buscar_ofertas_amazon():
    """
    Tenta buscar ofertas reais usando a Amazon Product Advertising API.
    A API retorna a URL da imagem (o que resolve seu problema).
    """
    
    if PAAPI_ACCESS_KEY == 'CHAVE_VAZIA' or PAAPI_SECRET_KEY == 'SECRETO_VAZIO':
        logger.error("CHAVES PA API NÃO CONFIGURADAS. Revertendo para simulação (sem imagem real)...")
        # Retornar uma simulação de fallback para não quebrar o bot
        return simular_ofertas_fallback()


    logger.info("Executando busca real de ofertas na Amazon PA API...")
    
    # 1. Configurar a API
    api = DefaultApi(access_key=PAAPI_ACCESS_KEY, secret_key=PAAPI_SECRET_KEY, host=HOST, region=REGION)
    
    # 2. Definir os recursos que queremos (incluindo preço e imagem)
    resources = [
        SearchItemsResource.IMAGES_PRIMARY_LARGE_URL,
        SearchItemsResource.ITEM_INFO_TITLE,
        SearchItemsResource.OFFERS_LISTINGS_PRICE,
        SearchItemsResource.OFFERS_LISTINGS_SAVING_PERCENT,
        SearchItemsResource.OFFERS_LISTINGS_SAVING_AMOUNT,
    ]
    
    # 3. Definir o que buscar (ex: Notebooks e Processadores)
    # Este é um exemplo simples. Você deve refinar sua Query.
    query = "Notebook Gamer e Processador High End"
    
    # 4. Montar a requisição
    try:
        search_items_request = SearchItemsRequest(
            partner_tag=PAAPI_PARTNER_TAG,
            partner_type=PartnerType.ASSOCIATES,
            search_index='All',
            item_count=10,
            keywords=query,
            resources=resources
        )
        
        # 5. Enviar a requisição (Esta parte requer a assinatura correta)
        response = api.search_items(search_items_request)
        
    except Exception as e:
        logger.error(f"Erro ao chamar a Amazon PA API: {e}")
        # Retornar uma simulação de fallback em caso de erro da API
        return simular_ofertas_fallback()

    
    # 6. Processar a resposta e formatar as ofertas
    ofertas_reais = []
    if response.search_result and response.search_result.items:
        for item in response.search_result.items:
            # Pular se faltar preço, imagem ou título
            if not item.offers or not item.offers.listings or not item.offers.listings[0].price or not item.images or not item.images.primary:
                continue
                
            titulo = item.item_info.title.display_value
            preco = item.offers.listings[0].price.display_amount
            link_afiliado = item.detail_page_url # A PA API retorna a URL já com a tag
            
            # **A SOLUÇÃO DO SEU PROBLEMA ESTÁ AQUI:** URL da Imagem Real
            imagem_url = item.images.primary.large.url
            
            # Tentar obter o preço antigo e o desconto (pode não existir)
            try:
                # A PA API geralmente não retorna o "Preço Antigo" diretamente, mas a % de desconto sim.
                # Para simplificar, vamos estimar ou usar o saving percent, mas para um preço "De:",
                # você teria que fazer um cálculo inverso que é complexo e nem sempre possível.
                desconto = item.offers.listings[0].saving_percent 
                desconto_texto = f"{desconto}%" if desconto else "Ótimo Preço"
            except:
                desconto_texto = "Ótimo Preço"


            ofertas_reais.append({
                'nome': titulo,
                'preco_atual': preco,
                'preco_antigo': 'Preço indisponível', # Preenchido assim para fins de demonstração
                'desconto': desconto_texto,
                'link_afiliado': link_afiliado,
                'categoria': 'PA API',
                'imagem_url': imagem_url # A URL real!
            })
    
    return ofertas_reais

# Função de Simulação de Contingência
def simular_ofertas_fallback():
    """ Usado se a API falhar ou não estiver configurada. """
    logger.info("Retornando ofertas simuladas (sem imagens reais)...")
    URL_IMAGEM_FALLBACK = 'https://via.placeholder.com/400x300?text=INTEGRE+A+PA+API'
    return [
        {
            'nome': 'NOTEBOOK GAMER: O Mais Potente da Amazon (40% OFF!)',
            'preco_atual': 'R$ 4.299,00',
            'preco_antigo': 'R$ 7.165,00',
            'desconto': '40%',
            'link_afiliado': f'https://www.amazon.com.br/dp/B09V74XXXX?tag={AFFILIATE_TAG}', 
            'categoria': 'Notebooks',
            'imagem_url': URL_IMAGEM_FALLBACK
        },
        {
            'nome': 'PROCESSADOR HIGH-END: Velocidade Máxima (30% de Desconto)',
            'preco_atual': 'R$ 1.999,90',
            'preco_antigo': 'R$ 2.857,00',
            'desconto': '30%',
            'link_afiliado': f'https://www.amazon.com.br/dp/B08S3XXXX2A?tag={AFFILIATE_TAG}',
            'categoria': 'Peças de Computador',
            'imagem_url': URL_IMAGEM_FALLBACK
        }
    ]

# O restante do código (Funções Assíncronas e Main) permanece o mesmo, mas foi incluído abaixo para facilitar o copy/paste completo.

# Usa send_photo (com fallback para message em caso de erro)
async def enviar_oferta_telegram(oferta):
    """
    Envia a foto (imagem_url) com o texto formatado como legenda (caption).
    """
    
    # FORMATANDO O TEXTO PARA SER A LEGENDA DA FOTO (CAPTION)
    mensagem = (
        f"🔥 <b>OFERTA IMPERDÍVEL AMAZON ({oferta['categoria'].upper()})</b> 🔥\n\n"
        f"🛒 <i>{oferta['nome']}</i>\n\n"
        # O preço antigo virá como "Preço indisponível" se a API não fornecer
        f"🏷️ De: <strike>{oferta['preco_antigo']}</strike>\n" 
        f"✅ <b>POR APENAS: {oferta['preco_atual']}</b>\n"
        f"💥 <i>Economize {oferta['desconto']}!</i> \n\n"
        f"➡️ <a href=\"{oferta['link_afiliado']}\">CLIQUE AQUI PARA GARANTIR!</a>"
    )
    
    try:
        await bot.send_photo( 
            chat_id=GROUP_CHAT_ID,
            photo=oferta['imagem_url'], 
            caption=mensagem,          
            parse_mode=ParseMode.HTML, 
        )
        logger.info(f"Oferta enviada: {oferta['nome']}")
    except Exception as e:
        logger.error(f"Erro ao enviar FOTO/mensagem para o grupo {GROUP_CHAT_ID}: {e}. Tentando enviar apenas texto...")
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
    
    # CHAMA A FUNÇÃO DE BUSCA REAL (OU SIMULAÇÃO, SE FALTAR CHAVES)
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
