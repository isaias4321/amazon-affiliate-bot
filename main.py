from fastapi import FastAPI, Query
import random

app = FastAPI(
    title="Amazon Affiliate Bot API",
    description="API de ofertas simuladas da Amazon para integração com o bot Telegram.",
    version="1.0.0",
)

# Banco de dados simulado — 1 produto por categoria
produtos = {
    "notebook": [
        {
            "titulo": "Notebook Lenovo IdeaPad 3i",
            "preco": "R$ 2.799,00",
            "imagem": "https://m.media-amazon.com/images/I/61f8YtYvHQL._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B0D1234567",
        }
    ],
    "processador": [
        {
            "titulo": "Processador AMD Ryzen 5 5600G",
            "preco": "R$ 899,00",
            "imagem": "https://m.media-amazon.com/images/I/71Q5sdPHD-L._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B092L9GF5N",
        }
    ],
    "celular": [
        {
            "titulo": "Smartphone Samsung Galaxy S23 FE",
            "preco": "R$ 2.499,00",
            "imagem": "https://m.media-amazon.com/images/I/71qGzvLh6kL._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B0CJN2QH2F",
        }
    ],
    "ferramenta": [
        {
            "titulo": "Parafusadeira Bosch 12V",
            "preco": "R$ 489,00",
            "imagem": "https://m.media-amazon.com/images/I/61GqU2B1bVL._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B07X9YQ3TG",
        }
    ],
    "eletrodoméstico": [
        {
            "titulo": "Aspirador de Pó Philco Ciclone Force",
            "preco": "R$ 299,00",
            "imagem": "https://m.media-amazon.com/images/I/71a3rMebJCL._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B09KLMNOPQ",
        }
    ],
}

@app.get("/")
def home():
    return {"status": "✅ API de Ofertas Amazon Online"}

@app.get("/buscar")
def buscar(categoria: str = Query(..., description="Categoria do produto para buscar")):
    categoria = categoria.lower()
    if categoria not in produtos:
        return {"erro": f"Categoria '{categoria}' não encontrada."}
    return random.choice(produtos[categoria])
