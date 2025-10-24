import requests
import os

# 🔧 CONFIGURAÇÕES - substitua pelos seus dados:
CLIENT_ID = "7518422397227053"
CLIENT_SECRET = "vhfFTrUxj6YOaQJl82nbo4KGxo4IhlWG"
REDIRECT_URI = "https://example.com"
CODE = "TG-68fb8d7c6bc7d90001ed02c0-2530199814"

url = "https://api.mercadolibre.com/oauth/token"
data = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": CODE,
    "redirect_uri": REDIRECT_URI
}

print("🔄 Solicitando token de acesso ao Mercado Livre...")

response = requests.post(url, data=data)

if response.status_code == 200:
    tokens = response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    print("\n✅ Token gerado com sucesso!")
    print(f"ACCESS_TOKEN: {access_token}")
    print(f"REFRESH_TOKEN: {refresh_token}")
    print(f"⏳ Expira em: {tokens['expires_in']} segundos")

    # Cria ou atualiza o arquivo .env automaticamente
    with open(".env", "a") as env_file:
        env_file.write(f"\nML_ACCESS_TOKEN={access_token}\n")
        env_file.write(f"ML_REFRESH_TOKEN={refresh_token}\n")

    print("\n💾 Tokens salvos no arquivo .env com sucesso!")

else:
    print(f"\n❌ Erro {response.status_code}: {response.text}")
