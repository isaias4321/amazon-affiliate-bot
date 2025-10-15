from fastapi import FastAPI, Query
import os
import random

app = FastAPI()

# 🔹 Sua tag de afiliado da Amazon
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "seu-tag-aqui")

@app.get("/")
def home():
    """Endpoint raiz - mostra status da API."""
    return {"status": "online", "message": "🚀 API Amazon Affiliate ativa e funcionando!"}

@app.get("/buscar")
def buscar(q: str = Query(..., description="Categoria ou termo de busca")):
    """Simula a busca de 1 produto por categoria."""
    
    produtos_exemplo = [
        {
            "titulo": f"{q.title()} Ultra Rápido 2025",
            "preco": "R$ 2.499,00",
            "link": f"https://www.amazon.com.br/s?k={q.replace(' ', '+')}&tag={AFFILIATE_TAG}",
            "imagem": "https://m.media-amazon.com/images/I/71KZfQA-Y7L._AC_SL1500_.jpg",
        },
        {
            "titulo": f"{q.title()} Premium Plus",
            "preco": "R$ 3.199,00",
            "link": f"https://www.amazon.com.br/s?k={q.replace(' ', '+')}&tag={AFFILIATE_TAG}",
            "imagem": "https://m.media-amazon.com/images/I/81QpkIctqPL._AC_SL1500_.jpg",
        },
        {
            "titulo": f"{q.title()} Compact Edition",
            "preco": "R$ 1.999,00",
            "link": f"https://www.amazon.com.br/s?k={q.replace(' ', '+')}&tag={AFFILIATE_TAG}",
            "imagem": "https://m.media-amazon.com/images/I/61tBzN-7XrL._AC_SL1500_.jpg",
        },
    ]

    # Retorna 1 produto aleatório por categoria
    produto_escolhido = random.choice(produtos_exemplo)

    return {
        "categoria": q,
        "produto": produto_escolhido,
    }
