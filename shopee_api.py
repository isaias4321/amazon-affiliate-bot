import os
import time
import hmac
import hashlib
import requests
import logging

logger = logging.getLogger(__name__)

PARTNER_ID = os.getenv("SHOPEE_PARTNER_ID")
PARTNER_KEY = os.getenv("SHOPEE_PARTNER_KEY")
BASE_URL = "https://partner.shopeemobile.com/api/v2"

def gerar_assinatura(url_path: str, timestamp: int):
    base_string = f"{PARTNER_ID}{url_path}{timestamp}"
    return hmac.new(
        bytes(PARTNER_KEY, "utf-8"),
        bytes(base_string, "utf-8"),
        hashlib.sha256
    ).hexdigest()

async def buscar_produto_shopee():
    try:
        timestamp = int(time.time())
        url_path = "/public/get_shops_by_partner"
        sign = gerar_assinatura(url_path, timestamp)

        url = f"{BASE_URL}{url_path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if "shops" in data:
                shop = data["shops"][0]
                return {
                    "titulo": f"Loja: {shop.get('shop_name', 'Desconhecida')}",
                    "preco": "—",
                    "link": f"https://shopee.com.br/shop/{shop['shopid']}"
                }
            else:
                logger.warning("⚠️ Nenhum dado retornado pela API Shopee.")
                return None
        else:
            logger.warning(f"⚠️ Erro da API Shopee: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao buscar produto na Shopee: {e}")
        return None
