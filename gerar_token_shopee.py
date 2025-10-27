import os
import time
import hmac
import hashlib
import requests

# ⚙️ Configurações principais
PARTNER_ID = os.environ.get("SHOPEE_PARTNER_ID") or "18377860824"  # seu AppID
PARTNER_SECRET = os.environ.get("SHOPEE_PARTNER_SECRET") or "6DKXDSUSRPBNAFQN4P3MYDQPAHXY7CQU"
REDIRECT_URL = os.environ.get("SHOPEE_REDIRECT_URL") or "https://google.com"  # troque pelo seu redirect cadastrado

BASE_URL = "https://partner.shopeemobile.com"

def gerar_link_autorizacao():
    timestamp = int(time.time())
    path = "/api/v2/shop/auth_partner"
    sign_base = f"{PARTNER_ID}{path}{timestamp}"
    sign = hmac.new(PARTNER_SECRET.encode(), sign_base.encode(), hashlib.sha256).hexdigest()

    auth_url = (
        f"{BASE_URL}{path}?"
        f"partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}&redirect={REDIRECT_URL}"
    )
    print("🔗 Abra este link no navegador e autorize sua loja:")
    print(auth_url)
    print("\nApós autorizar, copie o parâmetro 'code' e cole abaixo para gerar o token.\n")

def gerar_token(code):
    timestamp = int(time.time())
    path = "/api/v2/auth/token/get"
    sign_base = f"{PARTNER_ID}{path}{timestamp}"
    sign = hmac.new(PARTNER_SECRET.encode(), sign_base.encode(), hashlib.sha256).hexdigest()

    url = f"{BASE_URL}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    payload = {"code": code, "shop_id": 0, "main_account_id": 0}

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        data = response.json()
        print("\n✅ Token gerado com sucesso!\n")
        print(data)
        print("\nCopie e salve:")
        print(f"SHOP_ID = {data['shop_id']}")
        print(f"ACCESS_TOKEN = {data['access_token']}")
        print(f"REFRESH_TOKEN = {data['refresh_token']}")
    else:
        print("❌ Erro ao gerar token:", response.text)

if __name__ == "__main__":
    print("=== SHOPEE API TOKEN GENERATOR ===\n")
    gerar_link_autorizacao()
    code = input("Cole o código 'code' que você recebeu na URL: ").strip()
    if code:
        gerar_token(code)
