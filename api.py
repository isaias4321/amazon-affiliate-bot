from fastapi import FastAPI, Query
import requests
import os

app = FastAPI()

# Obtenha a chave da API de ambiente (opcional)
RAIN_API_KEY = os.getenv("RAIN_API_KEY")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "seu-tag-aqui")  # substitua se quiser

@app.get("/")
def home():
    return {"status": "online", "message": "🚀 API Amazon Affiliate ativa!"}


@app.get("/buscar")
def buscar(q: str = Query(..., description="Categoria ou termo de busca")):
    """
    Endpoint para buscar produtos da Amazon.
    Exemplo: /buscar?q=notebook
    """
    try:
        # Simulação de busca — substitua por uma chamada real à API de ofertas se quiser.
        produtos = [
            {
                "titulo": f"{q.title()} em promoção",
                "preco": "R$ 2.499,00",
                "link": f"https://www.amazon.com.br/s?k={q.replace(' ', '+')}&tag={AFFILIATE_TAG}",
                "imagem": "https://m.media-amazon.com/images/I/71KZfQA-Y7L._AC_SL1500_.jpg",
            }
        ]
        return {"categoria": q, "produtos": produtos}

    except Exception as e:
        return {"erro": str(e), "mensagem": "Erro interno ao buscar produtos."}
