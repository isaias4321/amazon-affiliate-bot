import os
import logging
import aiohttp
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

# ===============================
# ⚙️ Configuração básica
# ===============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Amazon Affiliate API", version="1.0")

# 🔑 Variáveis de ambiente
RAIN_API_KEY = os.getenv("RAIN_API_KEY", "")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")

if not RAIN_API_KEY:
    logger.error("❌ Variável RAIN_API_KEY não configurada.")
else:
    logger.info("✅ Chave RAIN_API_KEY detectada.")


# ===============================
# 🔍 Rota principal
# ===============================
@app.get("/buscar")
async def buscar_produto(q: str = Query(..., description="Termo de busca na Amazon")):
    """Busca um produto na Amazon via Rainforest API e retorna dados simplificados."""
    if not RAIN_API_KEY:
        return JSONResponse({"erro": "RAIN_API_KEY não configurada no servidor"}, status_code=500)

    url = (
        f"https://api.rainforestapi.com/request?"
        f"api_key={RAIN_API_KEY}&type=search&amazon_domain=amazon.com.br"
        f"&search_term={q.replace(' ', '+')}&language=pt_BR"
    )

    logger.info(f"🔍 Buscando produtos: {q}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=25) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Erro HTTP {resp.status} na busca por '{q}'")
                    return JSONResponse({"erro": f"Erro HTTP {resp.status}"}, status_code=resp.status)
                data = await resp.json()
    except Exception as e:
        logger.error(f"❌ Erro na requisição: {e}")
        return JSONResponse({"erro": str(e)}, status_code=500)

    resultados = data.get("search_results", [])
    if not resultados:
        logger.warning(f"Nenhum produto encontrado para '{q}'")
        return JSONResponse({"erro": "Nenhum produto encontrado"}, status_code=404)

    item = resultados[0]  # Pega o primeiro resultado
    title = item.get("title", "Sem título")
    link = item.get("link", "")
    image = item.get("image", "")
    price = item.get("price", {}).get("raw") if item.get("price") else "N/A"

    sep = "&" if "?" in link else "?"
    link_afiliado = f"{link}{sep}tag={AFFILIATE_TAG}"

    produto = {
        "titulo": title,
        "preco": price,
        "imagem": image,
        "link": link_afiliado
    }

    logger.info(f"✅ Produto retornado: {title[:50]}...")
    return produto


# ===============================
# 🚀 Execução local / Railway
# ===============================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🚀 Iniciando servidor na porta {port}")
    uvicorn.run("api:app", host="0.0.0.0", port=port)
