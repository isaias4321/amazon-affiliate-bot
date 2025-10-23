import requests
from bs4 import BeautifulSoup
import random
import logging

logging.basicConfig(level=logging.INFO)

def buscar_produto_ml(categoria="eletronicos"):
    """
    Busca produtos no Mercado Livre pela API pública.
    Faz fallback com scraping leve se a API retornar 403.
    """

    url = f"https://api.mercadolibre.com/sites/MLB/search?q={categoria}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Referer": "https://www.mercadolivre.com.br"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 403:
            logging.warning("⚠️ Mercado Livre retornou status 403 — tentando fallback scraping...")
            return buscar_produto_fallback(categoria)

        if response.status_code != 200:
            logging.warning(f"⚠️ Erro ao buscar produtos (status {response.status_code})")
            return None

        data = response.json()
        resultados = data.get("results", [])
        if not resultados:
            logging.warning("⚠️ Nenhuma oferta encontrada na API.")
            return None

        produto = random.choice(resultados)
        return {
            "titulo": produto.get("title", "Sem título"),
            "preco": produto.get("price", "Preço não disponível"),
            "link": produto.get("permalink", "#"),
            "imagem": produto.get("thumbnail", None)
        }

    except Exception as e:
        logging.error(f"❌ Erro ao buscar no Mercado Livre: {e}")
        return None


def buscar_produto_fallback(categoria="eletronicos"):
    """
    Busca simples via scraping leve na busca pública do Mercado Livre.
    Apenas lê o HTML, sem automatizar login.
    """
    try:
        query = categoria.replace(" ", "+")
        url = f"https://lista.mercadolivre.com.br/{query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "pt-BR,pt;q=0.9"
        }

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logging.warning(f"⚠️ Fallback falhou (status {response.status_code})")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.select("li.ui-search-layout__item div.ui-search-result__content-wrapper")

        if not items:
            logging.warning("⚠️ Nenhum produto encontrado no fallback.")
            return None

        item = random.choice(items)
        titulo = item.select_one("h2.ui-search-item__title")
        link = item.select_one("a.ui-search-link")
        preco = item.select_one("span.price-tag-fraction")

        return {
            "titulo": titulo.text.strip() if titulo else "Produto sem nome",
            "preco": preco.text.strip() if preco else "Preço não disponível",
            "link": link["href"] if link else "#",
            "imagem": None
        }

    except Exception as e:
        logging.error(f"❌ Erro no fallback Mercado Livre: {e}")
        return None
