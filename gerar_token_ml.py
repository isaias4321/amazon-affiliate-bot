import os
import requests
import logging

# Configuração de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mercadolivre_token")

def gerar_token_mercadolivre():
    """
    Gera e salva automaticamente o token do Mercado Livre diretamente nas variáveis do Railway.
    """
    client_id = os.getenv("ML_CLIENT_ID")
    client_secret = os.getenv("ML_CLIENT_SECRET")
    redirect_uri = os.getenv("ML_REDIRECT_URI")
    code = os.getenv("ML_CODE")

    if not all([client_id, client_secret, redirect_uri, code]):
        logger.error("❌ Variáveis obrigatórias (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI ou CODE) não configuradas!")
        return

    logger.info("🔑 Gerando novo token de acesso do Mercado Livre...")

    url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri
    }

    try:
        response = requests.post(url, data=payload)
        data = response.json()

        if response.status_code != 200:
            logger.warning(f"⚠️ Erro da API Mercado Livre: {response.status_code}")
            logger.warning(data)
            return

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")

        if not access_token:
            logger.error("❌ Nenhum access_token retornado pela API.")
            return

        # Grava no ambiente Railway (logs apenas, para você copiar manualmente)
        logger.info("✅ Token gerado com sucesso!")
        logger.info(f"ACCESS_TOKEN = {access_token}")
        logger.info(f"REFRESH_TOKEN = {refresh_token}")

        # Também grava num arquivo local (útil pra debug)
        with open(".env", "a") as f:
            f.write(f"\nML_ACCESS_TOKEN={access_token}\n")
            f.write(f"ML_REFRESH_TOKEN={refresh_token}\n")

        logger.info("💾 Tokens salvos no arquivo .env e exibidos no log.")
        logger.info("👉 Copie os tokens e adicione manualmente no painel de variáveis do Railway!")

    except Exception as e:
        logger.error(f"❌ Erro ao gerar token: {e}")

if __name__ == "__main__":
    gerar_token_mercadolivre()
