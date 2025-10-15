from fastapi import FastAPI
import random

# ======================================================
# 🚀 API Simulada de Ofertas Amazon
# ======================================================

app = FastAPI(
    title="Amazon Affiliate API",
    description="API simples para fornecer produtos simulados por categoria.",
    version="1.0.0"
)

# ======================================================
# 🛒 Catálogo Simulado de Produtos
# ======================================================

PRODUTOS = {
    "notebook": [
        {
            "titulo": "Notebook Lenovo IdeaPad 3i Intel Core i5 8GB 256GB SSD 15.6”",
            "preco": "R$ 2.899,00",
            "imagem": "https://m.media-amazon.com/images/I/71g8t+R9JtL._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B09G9HD6DF"
        },
        {
            "titulo": "Notebook Acer Aspire 5 AMD Ryzen 7 5700U 16GB RAM 512GB SSD",
            "preco": "R$ 3.599,00",
            "imagem": "https://m.media-amazon.com/images/I/81m1s4wIPML._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B09M7PZ7D8"
        }
    ],
    "processador": [
        {
            "titulo": "AMD Ryzen 5 5600G 3.9GHz (4.4GHz Turbo) 6 Núcleos 12 Threads",
            "preco": "R$ 899,00",
            "imagem": "https://m.media-amazon.com/images/I/61o2ASbT5ZL._AC_SL1000_.jpg",
            "link": "https://www.amazon.com.br/dp/B092L9GF5N"
        },
        {
            "titulo": "Intel Core i5-12400F 4.4GHz 6 Núcleos 12 Threads",
            "preco": "R$ 1.099,00",
            "imagem": "https://m.media-amazon.com/images/I/61-lv3oymXL._AC_SL1000_.jpg",
            "link": "https://www.amazon.com.br/dp/B09NQNGH2V"
        }
    ],
    "celular": [
        {
            "titulo": "Samsung Galaxy A15 128GB 4GB RAM",
            "preco": "R$ 1.099,00",
            "imagem": "https://m.media-amazon.com/images/I/71RvH6D+V+L._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B0CRF1MJ8D"
        },
        {
            "titulo": "Xiaomi Redmi Note 13 256GB 8GB RAM",
            "preco": "R$ 1.399,00",
            "imagem": "https://m.media-amazon.com/images/I/61Hh3xqZ2EL._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B0CWYQKNXY"
        }
    ],
    "ferramenta": [
        {
            "titulo": "Parafusadeira/Furadeira Bosch Go 3.6V com 33 Acessórios",
            "preco": "R$ 289,00",
            "imagem": "https://m.media-amazon.com/images/I/61JbWf3c2vL._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B07H9R1BNM"
        },
        {
            "titulo": "Kit Chave de Fenda Tramontina 6 Peças",
            "preco": "R$ 49,90",
            "imagem": "https://m.media-amazon.com/images/I/71uTCc4XmoL._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B08GKQGRKS"
        }
    ],
    "eletrodoméstico": [
        {
            "titulo": "Fritadeira Air Fryer Mondial Family 4L",
            "preco": "R$ 349,00",
            "imagem": "https://m.media-amazon.com/images/I/61CsGcud7IL._AC_SL1000_.jpg",
            "link": "https://www.amazon.com.br/dp/B07ZY2FSVZ"
        },
        {
            "titulo": "Cafeteira Expresso Nespresso Essenza Mini Preta",
            "preco": "R$ 599,00",
            "imagem": "https://m.media-amazon.com/images/I/61BchS2JZ3L._AC_SL1500_.jpg",
            "link": "https://www.amazon.com.br/dp/B075SMN5D4"
        }
    ]
}

# ======================================================
# 🔍 Rota principal de busca
# ======================================================

@app.get("/buscar")
async def buscar(q: str):
    """
    Busca 1 produto da categoria informada.
    Exemplo: /buscar?q=notebook
    """
    categoria = q.lower().strip()

    if categoria not in PRODUTOS:
        return {"erro": f"Categoria '{categoria}' não encontrada."}

    produto = random.choice(PRODUTOS[categoria])
    return produto


# ======================================================
# 🌐 Rota base
# ======================================================

@app.get("/")
async def root():
    return {
        "mensagem": "🚀 API de Ofertas Amazon está online!",
        "endpoints": ["/buscar?q=notebook", "/buscar?q=celular", "/buscar?q=ferramenta"],
        "status": "ok"
    }
