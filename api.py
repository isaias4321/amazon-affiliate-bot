from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import logging
import random

# 🔹 Configurar logging colorido
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Amazon Ofertas API", version="1.0")

# 🔹 Simulação de produtos (você pode integrar futuramente com scraping ou API real)
PRODUTOS = {
    "notebook": [
        {"titulo": "Notebook Acer Aspire 5", "preco": "R$ 2.999", "link": "https://amzn.to/3notebook"},
        {"titulo": "Notebook Lenovo IdeaPad 3", "preco": "R$ 2.799", "link": "https://amzn.to/3lenovo"},
    ],
    "celular": [
        {"titulo": "Samsung Galaxy S23", "preco": "R$ 3.999", "link": "https://amzn.to/3samsung"},
        {"titulo": "iPhone 14", "preco": "R$ 5.499", "link": "https://amzn.to/3iphone"},
    ],
    "processador": [
        {"titulo": "AMD Ryzen 5 5600X", "preco": "R$ 1.099", "link": "https://amzn.to/3ryzen"},
        {"titulo": "Intel Core i7-13700K", "preco": "R$ 2.499", "link": "https://amzn.to/3intel"},
    ],
    "ferramenta": [
        {"titulo": "Parafusadeira Bosch", "preco": "R$ 499", "link": "https://amzn.to/3bosch"},
        {"titulo": "Furadeira DeWalt", "preco": "R$ 399", "link": "https://amzn.to/3dewalt"},
    ],
    "eletrodoméstico": [
        {"titulo": "Geladeira Brastemp Frost Free", "preco": "R$ 3.199", "link": "https://amzn.to/3brastemp"},
        {"titulo": "Micro-ondas Electrolux", "preco": "R$ 699", "link": "https://amzn.to/3micro"},
    ],
}

@app.get("/buscar")
def buscar_produto(q: str = Query(..., description="Categoria do produto")):
    q = q.lower().strip()
    logger.info(f"🔎 Buscando produto na categoria: {q}")

    if q not in PRODUTOS:
        logger.warning(f"❌ Categoria '{q}' não encontrada")
        return JSONResponse(
            content={"status": "erro", "mensagem": f"Categoria '{q}' não encontrada."},
            status_code=404,
        )

    produto = random.choice(PRODUTOS[q])
    logger.info(f"✅ Produto encontrado: {produto['titulo']}")

    return JSONResponse(
        content={
            "status": "ok",
            "categoria": q,
            "produto": produto,
        },
        status_code=200,
    )
