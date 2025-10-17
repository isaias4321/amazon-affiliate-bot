import aiohttp
from bs4 import BeautifulSoup
import logging

URL_AMAZON_GOLDBOX = "https://www.amazon.com.br/gp/goldbox"

async def buscar_ofertas():
    produtos = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(URL_AMAZON_GOLDBOX) as resp:
                if resp.status != 200:
                    logging.warning(f"Erro HTTP {resp.status} ao acessar {URL_AMAZON_GOLDBOX}")
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                itens = soup.select("div.DealCard-module__card_1LZr9")
                for item in itens[:10]:  # pega só os 10 primeiros
                    titulo = item.select_one("span.DealCard-module__truncate_2QPsL")
                    preco = item.select_one("span.a-price-whole")
                    link_tag = item.select_one("a.a-link-normal")
                    img_tag = item.select_one("img")

                    if not link_tag or not titulo:
                        continue

                    produtos.append({
                        "titulo": titulo.get_text(strip=True),
                        "preco": preco.get_text(strip=True) if preco else "Ver preço",
                        "link": f"https://www.amazon.com.br{link_tag['href']}",
                        "imagem": img_tag["src"] if img_tag else None,
                    })

        return produtos

    except Exception as e:
        logging.error(f"Erro ao buscar ofertas: {e}")
        return []
