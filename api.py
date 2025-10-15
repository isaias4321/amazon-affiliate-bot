import os
import aiohttp
import logging
from fastapi import FastAPI, Query
from dotenv import load_dotenv
from rich.logging import RichHandler

# ========== CONFIGURAÇÕES ==========
load_dotenv()
app = FastAPI(title="Amazon Affiliate API", version="2.0")

# Logs coloridos e organizados
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("rich")

# ========== VARIÁVEIS ==========
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")

if not SCRAPEOPS_API_KEY:
    logger.error("❌ Variável SCRAPEOPS_API_KEY ausente! Configure-a no Railway.")
else:
    logger.info("✅ Proxy ScrapeOps configurado com sucesso.")

# ========== ENDPOINT PRINCIPAL ==========
@app.get("/buscar")
async def buscar_produto(q: str = Query(..., description="Categoria ou termo para buscar na Amazon")):
    """
    Busca produtos na Amazon via ScrapeOps Proxy.
    Exemplo: /buscar?q=notebook
    """
    amazon_url = f"https://www.amazon.com.br/s?k={q.replace(' ', '+')}&tag={AFFILIATE_TAG}"
    proxy_url = "https://proxy.scrapeops.io/v1/"
    params = {"api_key": SCRAPEOPS_API_KEY, "url": amazon_url}

    logger.info(f"🔎 Buscando categoria: [bold cyan]{q}[/bold cyan]")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(proxy_url, params=params, timeout=30) as resp:
                logger.info(f"📡 Status ScrapeOps: {resp.status}")
                if resp.status != 200:
                    texto_erro = await resp.text()
                    logger.error(f"⚠️ Falha HTTP {resp.status}: {texto_erro[:200]}")
                    return {"status": "erro", "http": resp.status, "detalhe": texto_erro[:500]}
                
                html = await resp.text()
                logger.success(f"✅ Resultado recebido para {q} (tamanho: {len(html)} bytes)")
                return {"status": "ok", "categoria": q, "fonte": "Amazon via ScrapeOps", "html_preview": html[:800]}
    except Exception as e:
        logger.exception(f"💥 Erro inesperado ao buscar {q}: {e}")
        return {"status": "erro", "mensagem": str(e)}

# ========== ROTA DE TESTE ==========
@app.get("/")
async def root():
    return {"mensagem": "🚀 API Amazon Affiliate ativa e funcionando via ScrapeOps Proxy!"}
