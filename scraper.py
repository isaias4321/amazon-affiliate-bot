import aiohttp
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

async def buscar_ofertas(categoria, affiliate_tag, scrapeops_key):
    url = f"https://proxy.scrapeops.io/v1/?api_key={scrapeops_key}&url=https://www.amazon.com.br/s?k={categoria}"
    ofertas = []
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.warning(f"⚠️ Erro HTTP {resp.status} ao buscar {categoria}")
                return []
            html = await resp.text()
    soup = BeautifulSoup(html, "html.parser")
    for item in soup.select(".s-card-container")[:5]:
        titulo = item.select_one("h2 a span")
        preco = item.select_one(".a-price-whole")
        desconto = item.select_one(".a-text-price")
        if titulo and preco and desconto:
            ofertas.append({
                "titulo": titulo.text.strip(),
                "preco": preco.text.strip(),
                "link": f"https://www.amazon.com.br{item.select_one('h2 a')['href']}?tag={affiliate_tag}"
            })
    logger.info(f"🔍 {len(ofertas)} ofertas encontradas em {categoria}")
    return ofertas
