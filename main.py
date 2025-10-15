from fastapi import FastAPI
import os
import logging
import aiohttp
import asyncio

app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===============================
# 🔧 CONFIGURAÇÕES
# ===============================
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
RAIN_API_KEY = os.getenv("RAIN_API_KEY")

if not RAIN_API_KEY:
    logger.error("❌ ERRO: variável RAIN_API_KEY não configurada no Railway!")
    raise SystemExit("RAIN_API_KEY ausente — adicione no painel do Railway.")

CATEGORIES = [
    "notebook",
    "processador",
    "celular",
    "ferramenta",
    "eletrodoméstico"
]

# ===============================
# 🔍 FUNÇÃO: Buscar produtos via Rainforest API
# ===============================
async def buscar_produtos_rainforest(query: str, limit: int = 5):
    """Busca produtos usando a Rainforest API."""
    url = (
        f"https://api.rainforestapi.com/request?"
        f"api_key={RAIN_API_KEY}&type=search&amazon_domain=amazon.com.br"
        f"&search_term={query.replace(' ', '+')}"
        f"&language=pt_BR"
    )

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    logger.warning(f"Erro HTTP {resp.status} ao buscar {query}")
                    return []
                data = await resp.json()
        except Exception as e:
            logger.error(f"Erro ao buscar {query}: {e}")
            return []

    # Extrair resultados
    produtos = []
    results = data.get("search_results", [])
    for item in results[:limit]:
        title = item.get("title")
        link = item.get("link")
        image = item.get("image")
        price = item.get("price", {}).get("raw") if item.get("price") else "N/A"

        if title and link:
            # Adiciona o link de afiliado
            sep = "&" if "?" in link else "?"
            link_afiliado = f"{link}{sep}tag={AFFILIATE_TAG}"

            produtos.append({
                "title": title,
                "price": price,
                "url": link_afiliado,
                "image": image or "",
            })

    return produtos


# ===============================
# 🌐 ROTAS FASTAPI
# ===============================
@app.get("/")
def root():
    return {"message": "🚀 API do Bot de Ofertas Amazon com Rainforest ativa!"}


@app.get("/buscar")
async def buscar(q: str = "notebook"):
    produtos = await buscar_produtos_rainforest(q)
    return {"query": q, "count": len(produtos), "results": produtos}


# ===============================
# 🧠 TESTE LOCAL (opcional)
# ===============================
if __name__ == "__main__":
    async def test():
        for cat in CATEGORIES:
            produtos = await buscar_produtos_rainforest(cat)
            print(f"\nCategoria: {cat}")
            for p in produtos:
                print(f"- {p['title']} | {p['price']}")
    asyncio.run(test())
