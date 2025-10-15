import os
import logging
import requests
import time
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from colorama import Fore, Style, init

# Inicializa cor no terminal (Railway mostra cores)
init(autoreset=True)

app = FastAPI(title="Amazon Affiliate API", version="2.0")

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Variáveis de ambiente
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")

# Endpoint base da ScrapeOps
BASE_URL = "https://api.scrapeops.io/scrapers/amazon-search"

# ---------------------------
# Função de busca principal
# ---------------------------
def buscar_produtos(categoria: str):
    """Busca produtos da Amazon via ScrapeOps API"""
    if not SCRAPEOPS_API_KEY:
        logger.error(Fore.RED + "❌ SCRAPEOPS_API_KEY ausente!" + Style.RESET_ALL)
        return []

    params = {
        "api_key": SCRAPEOPS_API_KEY,
        "search_term": categoria,
        "amazon_domain": "amazon.com.br",
        "num_results": 10,
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/118.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    }

    for tentativa in range(3):
        try:
            response = requests.get(BASE_URL, params=params, headers=headers, timeout=30)

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                if results:
                    logger.info(Fore.GREEN + f"✅ {len(results)} resultados encontrados para '{categoria}'" + Style.RESET_ALL)
                    produtos = []
                    for item in results[:5]:
                        titulo = item.get("title")
                        preco = item.get("price_string", "Preço indisponível")
                        url = item.get("url")

                        # Adiciona o affiliate tag à URL
                        if url and "tag=" not in url:
                            separador = "&" if "?" in url else "?"
                            url = f"{url}{separador}tag={AFFILIATE_TAG}"

                        produtos.append({
                            "titulo": titulo,
                            "preco": preco,
                            "url": url
                        })
                    return produtos
                else:
                    logger.warning(Fore.YELLOW + f"⚠️ Nenhum produto encontrado para '{categoria}'" + Style.RESET_ALL)
                    return []

            else:
                logger.warning(Fore.RED + f"⚠️ Erro HTTP {response.status_code} ao buscar '{categoria}'" + Style.RESET_ALL)

        except Exception as e:
            logger.error(Fore.RED + f"❌ Exceção ao buscar '{categoria}': {e}" + Style.RESET_ALL)

        espera = 2 * (tentativa + 1)
        logger.info(Fore.CYAN + f"🔁 Tentando novamente em {espera}s..." + Style.RESET_ALL)
        time.sleep(espera)

    logger.error(Fore.RED + f"❌ Falha ao buscar '{categoria}' após várias tentativas" + Style.RESET_ALL)
    return []


# ---------------------------
# Endpoint principal da API
# ---------------------------
@app.get("/")
async def root():
    return JSONResponse({
        "status": "ok",
        "mensagem": "🚀 API de Ofertas da Amazon rodando com ScrapeOps!",
        "instruções": "/ofertas?q=termo"
    })


@app.get("/ofertas")
async def ofertas(q: str):
    if not q:
        return JSONResponse({"erro": "Parâmetro 'q' obrigatório."}, status_code=400)

    logger.info(Fore.BLUE + f"🔍 Buscando ofertas para '{q}'..." + Style.RESET_ALL)
    produtos = buscar_produtos(q)

    if not produtos:
        return JSONResponse({
            "status": "erro",
            "mensagem": f"Nenhum produto encontrado para '{q}'"
        }, status_code=404)

    return JSONResponse({
        "status": "sucesso",
        "query": q,
        "quantidade": len(produtos),
        "produtos": produtos
    })
