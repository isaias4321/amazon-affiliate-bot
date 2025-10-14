from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import os

app = FastAPI(title="Amazon Affiliate API")

AMAZON_ASSOCIATE_TAG = os.getenv("AMAZON_ASSOCIATE_TAG", "seu-tag-afiliado-20")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

@app.get("/api/amazon")
def get_products(query: str = Query(...)):
    """
    Busca produtos na Amazon Brasil e retorna dados simulados (ou da API oficial se configurada).
    """
    try:
        search_url = f"https://www.amazon.com.br/s?k={query.replace(' ', '+')}&tag={AMAZON_ASSOCIATE_TAG}"
        response = requests.get(search_url, headers=HEADERS, timeout=10)

        if response.status_code != 200:
            return JSONResponse(status_code=response.status_code, content={"error": "Erro ao buscar produtos"})

        # Simulação simples (ideal substituir por scraping com BeautifulSoup ou Amazon PA API)
        # Exemplo de dados de resposta para teste
        fake_data = [
            {
                "title": f"{query.title()} Premium Edition",
                "price": "R$ 1.999,00",
                "image": "https://m.media-amazon.com/images/I/61x2+z3K5hL._AC_SL1500_.jpg",
                "link": search_url,
            },
            {
                "title": f"{query.title()} Pro Gamer",
                "price": "R$ 899,90",
                "image": "https://m.media-amazon.com/images/I/71kWYm4PpXL._AC_SL1500_.jpg",
                "link": search_url,
            },
        ]

        return {"items": fake_data}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
