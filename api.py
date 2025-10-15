from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import aiohttp
import os
import random
import logging

# ===============================
# 🔧 CONFIGURAÇÃO
# ===============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Amazon Offers API")

RAIN_API_KEY = os.getenv("RAIN_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")

if not RAIN_API_KEY:
    logger.warning("⚠️ Variável RAIN_API_KEY ausente! As requisições podem falhar.")
if not AFFILIATE_TAG:
    logger.warning("⚠️ Variável AFFILIATE_TAG ausente! Os links não terão tag de afiliado.")

# ===============================
# 🧠 FUNÇÃO AUXILIAR
# ===============================
async def buscar_produtos(termo: str):
    """
    Simula uma busca na Amazon usando API pública de ofertas (substituto da PA API).
    Retorna até 5 produtos aleatórios no formato padronizado.
    """
    url = f"https://api.rainforestapi.com/request?api_key={RAIN_API_KEY}&type=search&amazon_domain=amazon.com.br&search_term={termo}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as resp:
                if resp.status != 200:
                    logger.warning(f"Erro HTTP {resp.status} ao buscar {termo}")
                    return []

                data = await resp.json()
    except Exception as e:
        logger.error(f"Erro ao buscar {termo}: {e}")
        return []

    produtos = []
    resultados = data.get("search_results", [])

    for item in resultados[:5]:
        titulo = item.get("title")
        preco = item.get("price", {}).get("raw", "Preço indisponível")
        imagem = item.get("image")
        link = item.get("link")

        if AFFILIATE_TAG and "tag=" not in link:
            separador = "&" if "?" in link else "?"
            link = f"{link}{separador}tag={AFFILIATE_TAG}"

        produtos.append({
            "titulo": titulo,
            "preco": preco,
            "imagem": imagem,
            "link": link
        })

    random.shuffle(produtos)
    return produtos

# ===============================
# 📦 ENDPOINT PRINCIPAL
# ===============================
@app.get("/buscar")
async def buscar(q: str = Query(..., description="Termo da busca")):
    produtos = await buscar_produtos(q)
    if not produtos:
        return JSONResponse({"erro": f"Nenhum produto encontrado para '{q}'"}, status_code=404)
    return produtos

# ===============================
# 🏠 ROTA RAIZ
# ===============================
@app.get("/")
def home():
    return {"status": "✅ API Amazon funcionando!", "endpoints": ["/buscar?q=notebook"]}
