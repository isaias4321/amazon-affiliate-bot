import os
import requests
import logging

# Configura o logger para exibir mensagens no console
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(message)s")

CLIENT_ID = os.getenv("ML_CLIENT_ID")
CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
REDIRECT_URI = os.getenv("ML_REDIRECT_URI")
CODE = os.getenv("ML_CODE")

if not all([CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, CODE]):
    logging.error("❌ Variáveis obrigatórias (CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, CODE) não configuradas!")
    exit()

logging.info("🔑 Gerando novo token de acesso do Mercado Livre...")

url = "https://api.mercadolibre.com/oauth/token"
data = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": CODE,
    "redirect_uri": REDIRECT_URI
}

try:
    response = requests.post(url, data=data)
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        logging.info("✅ TOKEN GERADO COM SUCESSO!\n")
        print("ACCESS_TOKEN =", access_token)
        print("REFRESH_TOKEN =", refresh_token)
        print("\n🚀 Copie e cole esses tokens nas variáveis de ambiente do Railway:")
        print("  - ML_ACCESS_TOKEN")
        print("  - ML_REFRESH_TOKEN")
    else:
        logging.warning(f"⚠️ Erro da API Mercado Livre: {response.status_code}")
        logging.warning(response.text)
except Exception as e:
    logging.error(f"❌ Erro inesperado ao tentar gerar o token: {e}")
