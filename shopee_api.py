import os
import time
import hmac
import hashlib
import requests
import logging
import random

logger = logging.getLogger(__name__)

# 🔧 Credenciais da Shopee (configure no Railway)
PARTNER_ID = os.getenv("SHOPEE_PARTNER_ID")
PARTNER_KEY = os.getenv("SHOPEE_PARTNER_KEY")
BASE_URL = "https://partner.shopeemobile.com/api/v2"

# 🧮 Função para gerar assinatura HMAC exigida pela Shopee
def gerar_assinatura(url_path: str, timestamp: int):
    base_string = f"{PARTNER_ID}{url_path}{timestamp}"
    sign = hmac.new(
        bytes(PARTNER_KEY, "utf-8"),
        bytes(base_string, "utf-8"),
        hashlib.sha256
    ).hexdigest()
    return sign


# 🛍️ Buscar produtos reais da Shopee
async def buscar_produto_shopee():
    try:
        timestamp = int(time.time())
        url_path = "/public/get_shops_by_partner"
        sign = gerar_assinatura(url_path, timestamp)

        # Primeiro, busca uma loja aleatória associada ao parceiro
        url = f"{BASE_URL}{url_path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
        response = requests.get(url)
        if response.status_code != 200:
            logger.warning(f"⚠️ Erro da API Shopee: {response.status_code}")
            return None

        lojas = response.json().get("shops", [])
        if not lojas:
            logger.warning("⚠️ Nenhuma loja retornada pela Shopee.")
            return None

        loja = random.choice(lojas)
        shop_id = loja["shopid"]

        # Agora, busca produtos dessa loja
        url_path = "/product/get_item_list"
        timestamp = int(time.time())
        sign = gerar_assinatura(url_path, timestamp)
        url = f"{BASE_URL}{url_path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}&shop_id={shop_id}&page_size=5"

        produtos_resp = requests.get(url)
        if produtos_resp.status_code != 200:
            logger.warning(f"⚠️ Erro ao buscar produtos: {produtos_resp.status_code}")
            return None

        data = produtos_resp.json()
        items = data.get("response", {}).get("item", [])
        if not items:
            logger.warning("⚠️ Nenhum produto encontrado nesta loja.")
            return None

        produto = random.choice(items)
        titulo = produto.get("item_name", "Produto sem nome")
        item_id = produto.get("item_id")

        return {
            "titulo": titulo,
            "preco": "Consultar na Shopee",
            "link": f"https://shopee.com.br/product/{shop_id}/{item_id}"
        }

    except Exception as e:
        logger.error(f"❌ Erro ao buscar produto na Shopee: {e}")
        return None
