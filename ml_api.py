import os
import requests
import random
import logging
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

# Configura o log
logger = logging.getLogger(__name__)

# Tokens e credenciais da API Mercado Livre
CLIENT_ID = os.getenv("ML_CLIENT_ID", "7518422397227053")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET", "vhfFTrUxj6YOaQJl82nbo4KGxo4IhlWG")
ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN")
REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN")

# Categorias principais
CATEGORIAS = [
    "MLB1648",   # Eletrônicos
    "MLB5726",   # Eletrodomésticos
    "MLB5672",   # Ferramentas
    "MLB1649"    # Informática
]


def renovar_token():
    """
    Atualiza o access_token automaticamente usando o refresh_token.
    """
    global ACCESS_TOKEN

    try:
        response = requests.post(
            "https://api.mercadolibre.com/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": REFRESH_TOKEN,
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            ACCESS_TOKEN = data["access_token"]
            logger.info("🔄 Token do Mercado Livre renovado com sucesso.")
            return True
        else:
            logger.warning(f"⚠️ Falha ao renovar token: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao renovar token: {e}")
        return False


async def buscar_produto_mercadolivre():
    """
    Busca um produto aleatório em uma das categorias definidas no Mercado Livre.
    Usa autenticação via token para evitar bloqueio (403).
    """
    categoria = random.choice(CATEGORIAS)
    url = f"https://api.mercadolibre.com/sites/MLB/search?category={categoria}&limit=20"

    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 401:
            # Token expirado → tenta renovar e repetir
            logger.warning("🔑 Token expirado, tentando renovar...")
            if renovar_token():
                headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                response = requests.get(url, headers=headers, timeout=10)
            else:
                return None

        if response.status_code != 200:
            logger.warning(f"⚠️ Mercado Livre retornou status {response.status_code}")
            return None

        data = response.json()
        results = data.get("results", [])

        if not results:
            logger.warning("⚠️ Nenhum produto encontrado no Mercado Livre.")
            return None

        produto = random.choice(results)

        titulo = produto.get("title", "Produto sem título")
        preco = produto.get("price", "N/A")
        link = produto.get("permalink", "Sem link")

        resultado = {
            "titulo": titulo,
            "preco": f"R$ {preco}",
            "link": link
        }

        logger.info(f"✅ Produto encontrado: {titulo} - {resultado['preco']}")
        return resultado

    except Exception as e:
        logger.error(f"❌ Erro inesperado ao buscar produto Mercado Livre: {e}")
        return None
