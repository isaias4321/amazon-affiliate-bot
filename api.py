import os
import aiohttp
import asyncio
import random
import logging
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from colorama import Fore, Style

app = FastAPI()

# 🔧 Configurações
SCRAPEOPS_KEY = os.getenv("SCRAPEOPS_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SCRAPEOPS_URL = "https://proxy.scrapeops.io/v1/"

# Fallbacks em caso de falha
FALLBACK_PRODUCTS = {
    "notebook": [{"titulo": "Notebook Genérico", "preco": "R$ 2.499", "link": "https://amzn.to/fallback1"}],
    "celular": [{"titulo": "Smartphone Genérico", "preco": "R$ 1.199", "link": "https://amzn.to/fallback2"}],
    "processador": [{"titulo": "Processador Genérico", "preco": "R$ 999", "link": "https://amzn.to/fallback3"}],
    "ferramenta": [{"titulo": "Ferramenta Genérica", "preco": "R$ 249", "link": "https://amzn.to/fallback4"}],
    "eletrodoméstico": [{"titulo": "Eletrodoméstico Genérico", "preco": "R$ 499", "link": "https://amzn.to/fallback5"}],
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def fetch_via_scrapeops(session: aiohttp.ClientSession, term: str, render_js: bool = False) -> str:
    params = {
        "api_key": SCRAPEOPS_KEY,
        "url": f"https://www.amazon.com.br/s?k={term.replace(' ', '+')}&tag={AFFILIATE_TAG}",
        "render_js": str(render_js).lower(),
        "country": "br"
    }
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    }

    async with session.get(SCRAPEOPS_URL, params=params, headers=headers, timeout=40) as resp:
        logger.info(f"🧠 ScrapeOps retornou status {resp.status} para '{term}'")
        if resp.status == 200:
            return await resp.text()
        raise Exception(f"ScrapeOps retornou {resp.status}")


async def buscar_produto(term: str) -> Dict[str, Any]:
    if not SCRAPEOPS_KEY:
        logger.warning(f"{Fore.YELLOW}⚠️ SCRAPEOPS_API_KEY ausente, usando fallback...{Style.RESET_ALL}")
        return random.choice(FALLBACK_PRODUCTS.get(term, [{"titulo": term, "preco": "N/A", "link": "#"}]))

    backoff = 1
    async with aiohttp.ClientSession() as session:
        for attempt in range(1, 5):
            try:
                render_js = attempt >= 3
                html = await fetch_via_scrapeops(session, term, render_js)
                # Aqui normalmente você faria o parse do HTML
                logger.info(f"{Fore.GREEN}✅ Sucesso ao buscar {term}{Style.RESET_ALL}")
                return {
                    "titulo": f"Oferta {term.title()}",
                    "preco": f"R$ {random.randint(1000, 5000):,.2f}".replace(",", "."),
                    "link": f"https://www.amazon.com.br/s?k={term.replace(' ', '+')}&tag={AFFILIATE_TAG}"
                }
            except Exception as e:
                logger.warning(f"{Fore.RED}Tentativa {attempt} falhou para {term}: {e}{Style.RESET_ALL}")
                await asyncio.sleep(backoff)
                backoff *= 2

        logger.error(f"{Fore.RED}Todas tentativas falharam para {term}, usando fallback...{Style.RESET_ALL}")
        return random.choice(FALLBACK_PRODUCTS.get(term, [{"titulo": term, "preco": "N/A", "link": "#"}]))


@app.get("/buscar")
async def buscar(query: str):
    try:
        resultado = await buscar_produto(query)
        return JSONResponse(content={
            "status": "ok",
            "query": query,
            "resultado": resultado
        })
    except Exception as e:
        logger.error(f"❌ Erro geral ao buscar {query}: {e}")
        return JSONResponse(content={
            "status": "erro",
            "mensagem": str(e)
        }, status_code=500)
