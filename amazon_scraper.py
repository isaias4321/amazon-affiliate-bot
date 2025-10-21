import logging
from typing import Dict, List

import aiohttp
from bs4 import BeautifulSoup

URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"
URL_AMAZON_SEARCH = "https://www.amazon.com.br/s"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}


async def buscar_ofertas() -> List[Dict[str, str]]:
    """Busca ofertas na página Goldbox da Amazon Brasil."""

    try:
        async with aiohttp.ClientSession(headers=DEFAULT_HEADERS) as session:
            async with session.get(URL_AMAZON_GOLDBOX) as resp:
                if resp.status != 200:
                    logging.warning(
                        "Erro HTTP %s ao acessar %s", resp.status, URL_AMAZON_GOLDBOX
                    )
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                itens = soup.select("div.DealCard-module__card_1LZr9")
                produtos: List[Dict[str, str]] = []

                for item in itens[:10]:  # pega só os 10 primeiros
                    titulo = item.select_one("span.DealCard-module__truncate_2QPsL")
                    preco = item.select_one("span.a-price-whole")
                    link_tag = item.select_one("a.a-link-normal")
                    img_tag = item.select_one("img")

                    if not link_tag or not titulo:
                        continue

                    produtos.append(
                        {
                            "titulo": titulo.get_text(strip=True),
                            "preco": preco.get_text(strip=True) if preco else "Ver preço",
                            "link": f"https://www.amazon.com.br{link_tag['href']}",
                            "imagem": img_tag["src"] if img_tag else None,
                        }
                    )

        return produtos

    except Exception as exc:  # pragma: no cover - log de rede
        logging.error("Erro ao buscar ofertas goldbox: %s", exc)
        return []


async def buscar_ofertas_por_categoria(
    categoria: str, limit: int = 10
) -> List[Dict[str, str]]:
    """Busca ofertas diretamente na Amazon Brasil para uma categoria.

    Args:
        categoria: Termo de busca em português.
        limit: Quantidade máxima de ofertas retornadas.

    Returns:
        Lista de dicionários com título, preço, link e imagem do produto.
    """

    params = {"k": categoria, "s": "featured-rank"}

    try:
        async with aiohttp.ClientSession(headers=DEFAULT_HEADERS) as session:
            async with session.get(URL_AMAZON_SEARCH, params=params) as resp:
                if resp.status != 200:
                    logging.warning(
                        "Erro HTTP %s ao buscar categoria '%s'", resp.status, categoria
                    )
                    return []

                html = await resp.text()

        soup = BeautifulSoup(html, "html.parser")
        produtos: List[Dict[str, str]] = []

        for item in soup.select("div[data-component-type='s-search-result']"):
            titulo_tag = item.select_one("h2 a span")
            link_tag = item.select_one("h2 a")

            if not titulo_tag or not link_tag:
                continue

            preco_inteiro = item.select_one("span.a-price-whole")
            preco_centavos = item.select_one("span.a-price-fraction")

            preco = None
            if preco_inteiro:
                centavos = preco_centavos.get_text(strip=True) if preco_centavos else "00"
                preco = f"R$ {preco_inteiro.get_text(strip=True)},{centavos}"

            link_href = link_tag.get("href", "").strip()
            if not link_href:
                continue

            if link_href.startswith("/"):
                link_href = f"https://www.amazon.com.br{link_href}"

            imagem_tag = item.select_one("img.s-image")
            imagem = None
            if imagem_tag:
                imagem = imagem_tag.get("src") or imagem_tag.get("data-image-src")

            produtos.append(
                {
                    "titulo": titulo_tag.get_text(strip=True),
                    "preco": preco or "Ver preço",
                    "link": link_href,
                    "imagem": imagem,
                }
            )

            if len(produtos) >= limit:
                break

        logging.info("%s produtos coletados para a categoria %s", len(produtos), categoria)
        return produtos

    except Exception as exc:  # pragma: no cover - log de rede
        logging.error("Erro ao buscar categoria '%s': %s", categoria, exc)
        return []
