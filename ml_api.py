import os
import requests
import random
import logging

logger = logging.getLogger(__name__)

# IDs das categorias principais do Mercado Livre Brasil (MLB)
CATEGORIAS = [
    "MLB1648",   # Eletrônicos
    "MLB5726",   # Eletrodomésticos
    "MLB263532", # Ferramentas
    "MLB1693"    # Computadores
]

# Lê tokens do arquivo .env
ML_ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN")
ML_REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN")
ML_CLIENT_ID = os.getenv("ML_CLIENT_ID")
ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")

def refresh_access_token():
    """
    Atualiza automaticamente o access_token quando expira,
    usando o refresh_token salvo no .env.
    """
    try:
        url = "https://api.mercadolibre.com/oauth/token"
        payload = {
            "grant_type": "refresh_token",
            "client_id": ML_CLIENT_ID,
            "client_secret": ML_CLIENT_SECRET,
            "refresh_token": ML_REFRESH_TOKEN
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            data = response.json()
            novo_token = data["access_token"]
            logger.info("✅ Novo access_token gerado com sucesso.")
            return novo_token
        else:
            logger.error(f"❌ Erro ao renovar token: {response.text}")
            return None
    except Exception as e:
        logger.error(f"❌ Erro inesperado ao renovar token: {e}")
        return None

async def buscar_produto_mercadolivre():
    """
    Busca produtos aleatórios no Mercado Livre via API oficial.
    Requer ACCESS_TOKEN válido no .env.
    """
    global ML_ACCESS_TOKEN

    if not ML_ACCESS_TOKEN:
        logger.warning("⚠️ Token de acesso do Mercado Livre não configurado.")
        return None

    categoria = random.choice(CATEGORIAS)
    url = f"https://api.mercadolibre.com/sites/MLB/search?category={categoria}&limit=10"

    headers = {
        "Authorization": f"Bearer {ML_ACCESS_TOKEN}"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        # Token expirado → renova automaticamente
        if response.status_code == 401:
            logger.warning("⚠️ Token expirado, tentando renovar...")
            novo_token = refresh_access_token()
            if novo_token:
                ML_ACCESS_TOKEN = novo_token
                headers["Authorization"] = f"Bearer {ML_ACCESS_TOKEN}"
                response = requests.get(url, headers=headers, timeout=10)
            else:
                logger.error("❌ Falha ao renovar o token.")
                return None

        if response.status_code != 200:
            logger.warning(f"⚠️ Erro da API Mercado Livre: {response.status_code}")
            return None

        data = response.json().get("results", [])
        if not data:
            logger.warning("⚠️ Nenhum produto encontrado na categoria.")
            return None

        item = random.choice(data)
        produto = {
            "titulo": item.get("title"),
            "preco": item.get("price"),
            "link": item.get("permalink")
        }

        logger.info(f"✅ Produto encontrado: {produto['titulo']} - R${produto['preco']}")
        return produto

    except Exception as e:
        logger.error(f"❌ Erro inesperado ao buscar produto: {e}")
        return None
