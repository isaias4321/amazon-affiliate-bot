from fastapi import FastAPI, Query
import requests
import logging
import os
import aiohttp
import asyncio
from bs4 import BeautifulSoup

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- CONFIG ----------------
AMAZON_BASE = "https://www.amazon.com.br/s"
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")

CATEGORY_KEYWORDS = [
    "gamer", "monitor", "notebook", "ssd", "mouse gamer", "cadeira gamer",
    "placa de vídeo", "processador", "fonte", "tv", "fone", "geladeira", "ferramenta"
]


async def fetch_html(url: str) -> str:
    """Faz requisição assíncrona com aiohttp"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
                if resp.status != 200:
                    logger.warning(f"Erro HTTP {resp.status} ao acessar {url}")
                    return ""
                return await resp.text()
    except Exception as e:
        logger.error(f"Erro ao acessar {url}: {e}")
        return ""


def build_affiliate_link(url: str) -> str:
    """Adiciona tag de afiliado à URL"""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}tag={AFFILIATE_TAG}"


async def search_amazon_products(query: str, limit: int = 5):
    """Busca produtos por termo na Amazon"""
    search_url = f"{AMAZON_BASE}?k={query.replace(' ', '+')}"
    html = await fetch_html(search_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = soup.select("div.s-main-slot div.s-result-item[data-asin]")[:limit]
    results = []

    for item in items:
        title_el = item.select_one("h2 a span")
        link_el = item.select_one("h2 a")
        price_el = item.select_one(".a-price-whole")
        image_el = item.select_one("img.s-image")

        if not title_el or not link_el:
            continue

        product = {
            "title": title_el.text.strip(),
            "url": build_affiliate_link("https://www.amazon.com.br" + link_el["href"].split("?")[0]),
            "price": price_el.text.strip() if price_el else "N/A",
            "image": image_el["src"] if image_el else "",
        }
        results.append(product)

    return results


@app.get("/")
def root():
    return {"message": "API Amazon Affiliate Bot rodando com sucesso 🚀"}


@app.get("/buscar")
async def buscar_produtos(q: str = Query(..., description="Termo de busca na Amazon")):
    produtos = await search_amazon_products(q)
    return {"query": q, "count": len(produtos), "results": produtos}

