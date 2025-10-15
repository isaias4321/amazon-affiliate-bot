from fastapi import FastAPI, Query
import logging
import os
import aiohttp
import asyncio
from bs4 import BeautifulSoup

# -----------------------------------------------------
# CONFIGURAÇÃO BÁSICA
# -----------------------------------------------------
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base da Amazon (.com evita erro 502 no Railway)
AMAZON_BASE = "https://www.amazon.com/s"
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")

CATEGORY_KEYWORDS = [
    "notebook", "processador", "celular", "ferramenta", "eletrodoméstico",
    "gamer", "monitor", "ssd", "mouse gamer", "placa de vídeo", "tv", "fone"
]


# -----------------------------------------------------
# FUNÇÃO DE REQUISIÇÃO HTML (com headers realistas)
# -----------------------------------------------------
async def fetch_html(url: str) -> str:
    """Faz requisição assíncrona com cabeçalhos realistas e tratamento de erro aprimorado"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
        "Host": "www.amazon.com"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Erro HTTP {resp.status} ao acessar {url}")
                    text = await resp.text()
                    if "Bot Check" in text or "captcha" in text.lower():
                        logger.warning("🚫 Amazon retornou CAPTCHA — bloqueio de bot detectado.")
                    return ""
                return await resp.text()
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Timeout ao acessar {url}")
        return ""
    except aiohttp.ClientError as e:
        logger.error(f"Erro de conexão ao acessar {url}: {e}")
        return ""
    except Exception as e:
        logger.error(f"Erro inesperado em fetch_html({url}): {e}")
        return ""


# -----------------------------------------------------
# ADICIONA TAG DE AFILIADO
# -----------------------------------------------------
def build_affiliate_link(url: str) -> str:
    """Adiciona tag de afiliado à URL"""
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}tag={AFFILIATE_TAG}"


# -----------------------------------------------------
# BUSCA PRODUTOS NA AMAZON (.com)
# -----------------------------------------------------
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
            "url": build_affiliate_link("https://www.amazon.com" + link_el["href"].split("?")[0]),
            "price": price_el.text.strip() if price_el else "N/A",
            "image": image_el["src"] if image_el else "",
        }
        results.append(product)

    logger.info(f"🔍 Encontrados {len(results)} produtos para '{query}'")
    return results


# -----------------------------------------------------
# ROTAS FASTAPI
# -----------------------------------------------------
@app.get("/")
def root():
    return {"message": "🚀 API Amazon Affiliate Bot rodando com sucesso!"}


@app.get("/buscar")
async def buscar_produtos(q: str = Query(..., description="Termo de busca na Amazon")):
    produtos = await search_amazon_products(q)
    return {"query": q, "count": len(produtos), "results": produtos}
