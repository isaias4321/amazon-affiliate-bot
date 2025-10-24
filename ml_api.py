import requests
from bs4 import BeautifulSoup
import random
import logging
import asyncio
from shopee_api import buscar_produto_shopee  # <- integração automática de fallback

logger = logging.getLogger(__name__)

CATEGORIAS = [
    "eletronicos",
    "eletrodomesticos",
    "ferramentas",
    "pecas-de-computador"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0"
]

async def buscar_produto_mercadolivre():
    """
    Faz scraping do Mercado Livre com cabeçalhos aleatórios e atraso para evitar bloqueio.
    Se o acesso for bloqueado (403) ou falhar, busca automaticamente na Shopee.
    """
    categoria = random.choice(CATEGORIAS)
    url = f"https://lista.mercadolivre.com.br/{categoria}"

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
    }

    await asyncio.sleep(random.uniform(1.5, 4.0))  # atraso aleatório

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 403:
            logger.warning("⚠️ Mercado Livre retornou status 403 (acesso bloqueado temporariamente).")
            logger.info("🔄 Buscando automaticamente na Shopee...")
            return await buscar_produto_shopee()

        if response.status_code != 200:
            logger.warning(f"⚠️ Erro ao acessar Mercado Livre: status {response.status_code}")
            logger.info("🔄 Buscando automaticamente na Shopee...")
            return await buscar_produto_shopee()

        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.select(".ui-search-result__wrapper")

        if not produtos:
            logger.warning("⚠️ Nenhum produto encontrado no scraping do Mercado Livre.")
            logger.info("🔄 Buscando automaticamente na Shopee...")
            return await buscar_produto_shopee()

        item = random.choice(produtos)
        titulo = item.select_one(".ui-search-item__title")
        preco = item.select_one(".andes-money-amount__fraction")
        link = item.select_one("a.ui-search-link")

        if not (titulo and preco and link):
            logger.warning("⚠️ Produto sem informações completas, tentando Shopee...")
            return await buscar_produto_shopee()

        produto = {
            "titulo": titulo.text.strip(),
            "preco": preco.text.strip(),
            "link": link["href"]
        }

        logger.info(f"✅ Produto do Mercado Livre: {produto['titulo']} - R${produto['preco']}")
        return produto

    except Exception as e:
        logger.error(f"❌ Erro inesperado ao buscar produto no Mercado Livre: {e}")
        logger.info("🔄 Buscando automaticamente na Shopee...")
        return await buscar_produto_shopee()
