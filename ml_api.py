# ml_api.py
import os
import requests
import random
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

# Site id para Brasil
SITE_ID = "MLB"

# User-Agent razoável para evitar bloqueios básicos
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/119.0 Safari/537.36"
    )
}

# Mapeie suas "categorias amigáveis" para consultas de busca.
# Ajuste os termos conforme a forma que você quer filtrar.
CATEGORIAS_QUERY_MAP = {
    "eletronicos": "eletr%C3%B4nicos",
    "eletrodomesticos": "eletrodom%C3%A9sticos",
    "ferramentas": "ferramentas",
    "pecas-de-computador": "pe%C3%A7as+de+computador"
}

def montar_url_busca_por_categoria(categoria):
    """
    Monta a URL de busca para a categoria.
    Usa query simples (q=) mas você pode trocar para category id se tiver.
    """
    if categoria in CATEGORIAS_QUERY_MAP:
        q = CATEGORIAS_QUERY_MAP[categoria]
    else:
        q = quote_plus(categoria)
    return f"https://api.mercadolibre.com/sites/{SITE_ID}/search?q={q}&limit=50"

def extrair_item_api_ml(item):
    """
    Recebe o objeto JSON do item do ML e retorna dicionário padronizado.
    """
    titulo = item.get("title")
    preco = None
    price_info = item.get("price")
    if price_info is not None:
        # price geralmente vem como number
        preco = f"{price_info:.2f}" if isinstance(price_info, (int, float)) else str(price_info)

    permalink = item.get("permalink")
    thumbnail = item.get("thumbnail") or item.get("thumbnail_id")
    # link de imagem maior pode ser construído a partir de thumbnail_id, mas permalink + thumbnail é suficiente

    return {
        "titulo": titulo or "Produto sem título",
        "preco": preco or "N/D",
        "link": permalink or "",
        "imagem": thumbnail or ""
    }

def buscar_produto_ml_sync(categoria: str = None):
    """
    Versão síncrona que retorna um produto aleatório ou None.
    - categoria: nome em CATEGORIAS_QUERY_MAP ou string livre.
    """
    if categoria is None:
        categoria = random.choice(list(CATEGORIAS_QUERY_MAP.keys()))

    url = montar_url_busca_por_categoria(categoria)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        if resp.status_code == 403:
            logger.warning("⚠️ Mercado Livre retornou status 403 (acesso bloqueado).")
            return None
        if resp.status_code != 200:
            logger.warning(f"⚠️ Mercado Livre retornou status {resp.status_code}")
            return None

        data = resp.json()
        results = data.get("results", [])
        if not results:
            logger.warning("⚠️ Nenhum resultado retornado pela API do Mercado Livre.")
            return None

        # Filtrar itens com permalink e price
        filtered = [r for r in results if r.get("permalink")]
        if not filtered:
            filtered = results

        item = random.choice(filtered)
        produto = extrair_item_api_ml(item)
        logger.info(f"✅ Produto ML encontrado: {produto['titulo']} - R${produto['preco']}")
        return produto

    except Exception as e:
        logger.exception(f"❌ Erro ao buscar produto no Mercado Livre: {e}")
        return None

# Async wrapper (facilita uso dentro do bot async)
async def buscar_produto_ml(categoria: str = None):
    """
    Wrapper assíncrono (não faz I/O async real, apenas torna compatível com async code).
    """
    return buscar_produto_ml_sync(categoria)
