import requests
import time

CLIENT_ID = "7518422397227053"
CLIENT_SECRET = "vhfFTrUxj6YOaQJl82nbo4KGxo4IhlWG"
REDIRECT_URI = "https://example.com"

print("🔗 Abra o link abaixo e copie o código que aparecer na URL:")
print(f"https://auth.mercadolivre.com.br/authorization?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}")
print()
code = input("👉 Cole aqui o código (começando com TG-...): ").strip()

print("\n⏳ Gerando token...")
url = "https://api.mercadolibre.com/oauth/token"
data = {
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": code,
    "redirect_uri": REDIRECT_URI
}

response = requests.post(url, data=data)

if response.status_code == 200:
    tokens = response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    print("\n✅ TOKEN GERADO COM SUCESSO!")
    print(f"ACCESS_TOKEN: {access_token}")
    print(f"REFRESH_TOKEN: {refresh_token}")
else:
    print("\n❌ Erro ao gerar token:")
    print(response.status_code, response.text)

time.sleep(5)
