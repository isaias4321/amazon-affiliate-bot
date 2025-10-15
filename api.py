import os
import logging
import requests
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from colorama import init, Fore, Style

# Inicializa cores no terminal
init(autoreset=True)

app = FastAPI(title="Amazon Ofertas API")

# Configuração de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Variáveis de ambiente
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")

if not AFFILIATE_TAG:
    logger.error(Fore.RED + "❌ AFFILIATE_TAG não configurado!")
if not SCRAPEOPS_API_KEY:
    logger.error(Fore.RED + "❌ SCRAPEOPS_API_KEY não configurado!")

@app.get("/")
def home():
    return {"status": "ok", "mensagem": "API da Amazon com ScrapeOps ativa!"}

@app.get("/buscar")
def buscar_produto(
    q: str = Query(..., description="Termo de busca (ex: notebook, celular, etc.)")
):
    """
    Busca produtos da Amazon Brasil usando o ScrapeOps Proxy.
    """

    if not SCRAPEOPS_API_KEY:
        return JSONResponse(
            status_code=500,
            content={"erro": "SCRAPEOPS_API_KEY ausente."}
        )

    # Monta a URL da Amazon
    amazon_url = f"https://www.amazon.com.br/s?k={q}&tag={AFFILIATE_TAG}"

    # Monta a URL do ScrapeOps
    proxy_url = "https://proxy.scrapeops.io/v1/"
    params = {
        "api_key": SCRAPEOPS_API_KEY,
        "url": amazon_url,
        "country": "br",
        "render_js": "false"
    }

    logger.info(Fore.CYAN + f"🔍 Buscando: {q}")
    logger.info(Fore.MAGENTA + f"➡️  URL via ScrapeOps: {amazon_url}")

    try:
        resp = requests.get(proxy_url, params=params, timeout=30)

        if resp.status_code == 200:
            logger.info(Fore.GREEN + f"✅ Sucesso! ({resp.status_code}) - Resultados obtidos.")
            return JSONResponse(
                content={
                    "status": "sucesso",
                    "categoria": q,
                    "codigo_http": resp.status_code,
                    "conteudo_html": resp.text[:1000],  # preview de segurança
                }
            )

        else:
            logger.warning(Fore.YELLOW + f"⚠️ HTTP {resp.status_code} ao buscar {q}")
            return JSONResponse(
                status_code=resp.status_code,
                content={
                    "status": "erro",
                    "codigo_http": resp.status_code,
                    "mensagem": f"Erro HTTP {resp.status_code} ao buscar {q}",
                },
            )

    except requests.exceptions.RequestException as e:
        logger.error(Fore.RED + f"❌ Erro na requisição: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "erro",
                "mensagem": "Falha na requisição ScrapeOps",
                "detalhes": str(e),
            },
        )
