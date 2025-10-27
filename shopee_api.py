# shopee_api.py
import os
import time
import hmac
import json
import random
import hashlib
import logging
import requests

logger = logging.getLogger("shopee_api")

PARTNER_ID = os.environ.get("SHOPEE_PARTNER_ID") or os.environ.get("SHOPEE_APP_ID")
PARTNER_SECRET = os.environ.get("SHOPEE_PARTNER_SECRET") or os.environ.get("SHOPEE_SECRET")
SHOP_ID = os.environ.get("SHOPEE_SHOP_ID")
ACCESS_TOKEN = os.environ.get("SHOPEE_ACCESS_TOKEN")

BASE_URL = "https://partner.shopeemobile.com"
TIMEOUT = 12

def _sign(path: str, timestamp: int, access_token: str, shop_id: str) -> str:
    """
    Shopee v2 signature:
    sign = HMAC_SHA256(secret, f"{partner_id}{path}{timestamp}{access_token}{shop_id}")
    """
    msg = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(PARTNER_SECRET.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()

def _call_api(path: str, params: dict):
    """
    Faz uma chamada GET para a OpenAPI v2 com assinatura.
    """
    if not (PARTNER_ID and PARTNER_SECRET and SHOP_ID and ACCESS_TOKEN):
        logger.warning("⚠️ Shopee API não configurada (PARTNER_ID/SECRET/SHOP_ID/ACCESS_TOKEN). Pulando.")
        return None

    ts = int(time.time())
    sign = _sign(path, ts, ACCESS_TOKEN, SHOP_ID)

    query = {
        "partner_id": PARTNER_ID,
        "timestamp": ts,
        "sign": sign,
        "access_token": ACCESS_TOKEN,
        "shop_id": SHOP_ID,
        **params,
    }

    url = f"{BASE_URL}{path}"
    resp = requests.get(url, params=query, timeout=TIMEOUT)
    if resp.status_code != 200:
        logger.warning(f"⚠️ Shopee API HTTP {resp.status_code}: {resp.text[:300]}")
        return None

    data = resp.json()
    if data.get("error"):
        logger.warning(f"⚠️ Shopee API error: {data.get('message') or data.get('error')}")
        return None
    return data

def _format_price(raw) -> str:
    """
    Shopee costuma devolver preço em 'price' *ou* em micros (ex.: 123450000 -> 1.234,50).
    Tentamos detectar automaticamente.
    """
    if raw is None:
        return "Indisponível"
    try:
        v = float(raw)
        # heurística: se muito grande, assume micros (1e6)
        if v > 1e6:
            v = v / 1_000_000.0
        elif v > 1e3 and v % 100 == 0:
            # alguns retornos vêm em centavos * 100
            v = v / 100.0
        return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "Indisponível"

async def buscar_produto_shopee():
    """
    Pega uma lista de itens da loja via OpenAPI v2 e retorna um item aleatório no formato:
    { 'titulo': str, 'preco': str, 'link': str }
    Se não conseguir, retorna None (o bot tenta outra plataforma).
    """
    if not (PARTNER_ID and PARTNER_SECRET and SHOP_ID and ACCESS_TOKEN):
        logger.warning("⚠️ Credenciais Shopee ausentes. Retornando None.")
        return None

    # 1) listar itens da loja
    path_list = "/api/v2/product/get_item_list"
    data = _call_api(
        path_list,
        {
            "item_status": "NORMAL",   # itens ativos
            "page_size": 50,
            "offset": 0,
        },
    )

    if not data or "response" not in data or "item" not in data["response"] or not data["response"]["item"]:
        logger.warning("⚠️ Nenhum item retornado pela Shopee.")
        return None

    items = data["response"]["item"]
    item = random.choice(items)
    item_id = str(item["item_id"])

    # 2) buscar info base dos itens
    path_info = "/api/v2/product/get_item_base_info"
    data2 = _call_api(
        path_info,
        {
            "item_id_list": item_id,
        },
    )

    if not data2 or "response" not in data2 or "item_list" not in data2["response"] or not data2["response"]["item_list"]:
        logger.warning("⚠️ Não foi possível obter detalhes do item.")
        return None

    info = data2["response"]["item_list"][0]
    title = info.get("item_name") or "Produto Shopee"
    # tenta vários campos de preço que aparecem em diferentes respostas
    price = info.get("price") or info.get("original_price") or info.get("price_info", [{}])[0].get("current_price")
    preco_fmt = _format_price(price)

    # Link público do item no padrão /product/<shop_id>/<item_id>
    link = f"https://shopee.com.br/product/{SHOP_ID}/{item_id}"

    produto = {
        "titulo": title.strip(),
        "preco": preco_fmt,
        "link": link,
    }
    logger.info(f"✅ Shopee produto: {produto['titulo']} - R$ {produto['preco']}")
    return produto
