import requests
from bs4 import BeautifulSoup
import random
import logging

# Configuração do log
logger = logging.getLogger(__name__)

# Categorias principais que o bot irá buscar
CATEGORIAS = [
    "eletronicos",
    "eletrodomesticos",
    "ferramentas",
    "pecas-de-computador"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0 Safari/537.36"
    )
}

async def buscar_produto_mercadolivre():
    """
    Busca produtos do Mercado Livre de forma aleatória.
    Faz scraping simples e retorna título, preço e link do produto.
    Se for bloqueado (403), retorna None e loga o erro.
    """
    categoria = random.choice(CATEGORIAS)
    url = f"https://lista.mercadolivre.com.br/{categoria}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code == 403:
            logger.warning("⚠️ Mercado Livre retornou status 403 (acesso bloqueado temporariamente).")
            return None

        if response.status_code != 200:
            logger.warning(f"⚠️ Erro ao acessar Mercado Livre: status {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        produtos = soup.select(".ui-search-result__wrapper")

        if not produtos:
            logger.warning("⚠️ Nenhum produto encontrado no scraping.")
            return None

        # Escolhe um produto aleatório
        item = random.choice(produtos)
        titulo = item.select_one(".ui-search-item__title")
        preco = item.select_one(".andes-money-amount__fraction")
        link = item.select_one("a.ui-search-link")

        if not (titulo and preco and link):
            logger.warning("⚠️ Produto sem informações completas, ignorando.")
            return None

        # Monta o resultado
        produto = {
            "titulo": titulo.text.strip(),
            "preco": preco.text.strip(),
            "link": link["href"]
        }

        logger.info(f"✅ Produto encontrado: {produto['titulo']} - R${produto['preco']}")
        return produto

    except Exception as e:
        logger.error(f"❌ Erro inesperado ao buscar produto no Mercado Livre: {e}")
        return None
