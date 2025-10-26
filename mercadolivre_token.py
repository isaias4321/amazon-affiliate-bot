import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Variáveis do ambiente (Railway)
CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ML_REFRESH_TOKEN")

def atualizar_token():
    """
    Atualiza automaticamente o token de acesso do Mercado Livre
    usando o refresh_token salvo no Railway.
    """
    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        logger.warning("⚠️ Variáveis do Mercado Livre não configuradas corretamente.")
        return None

    logger.info("🔄 Atualizando token de acesso do Mercado Livre...")

    url = "https://api.mercadolibre.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN
    }

    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            tokens = response.json()
            novo_access = tokens.get("access_token")
            novo_refresh = tokens.get("refresh_token")

            logger.info("✅ Token atualizado com sucesso!")
            logger.info(f"Novo Access Token: {novo_access[:30]}...")

            print("\n🚀 Atualize no Railway:")
            print(f"ML_ACCESS_TOKEN={novo_access}")
            print(f"ML_REFRESH_TOKEN={novo_refresh}\n")

            return novo_access
        else:
            logger.warning(f"⚠️ Erro ao atualizar token: {response.status_code}")
            logger.warning(response.text)
            return None

    except Exception as e:
        logger.error(f"❌ Erro ao tentar atualizar token: {e}")
        return None
