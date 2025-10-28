import os
import time
import hmac
import hashlib
import json
import logging
from typing import List, Dict
import httpx

logger = logging.getLogger(__name__)

PARTNER_ID = os.getenv("SHOPEE_PARTNER_ID", "").strip()
PARTNER_KEY = os.getenv("SHOPEE_PARTNER_KEY", "").strip()
SHOP_ID = os.getenv("SHOPEE_SHOP_ID", "").strip()

API_BASE = "https://partner.shopeemobile.com/api/v2"

def _can_use_shopee() -> bool:
    return bool(PARTNER_ID and PARTNER_KEY and SHOP_ID)

def _sign(path: str, timestamp: int, body: str) -> str:
    # assinatura: base = f"{PARTNER_ID}{path}{timestamp}{PARTNER_KEY}{body}"
    # doc varia, alguns exemplos usam partner_id + path + timestamp + access_token/ shop_id
    base = f"{PARTNER_ID}{path}{timestamp}{SHOP_ID}{body}".encode("utf-8")
    return hmac.new(PARTNER_KEY.encode("utf-8"), base, hashlib.sha256).hexdigest()

async def _search_placeholder(keyword: str, limit: int = 2) -> List[Dict]:
    """
    Placeholder usando endpoint público (quando OpenAPI não disponível).
    Para evitar 403, aqui apenas devolvemos vazio se não houver credenciais válidas.
    """
    return []

async def _get_trending_from_openapi(limit: int = 2) -> List[Dict]:
    """
    Exemplo simplificado chamando um endpoint de listagem da OpenAPI (quando disponível na sua conta).
    Como não sabemos o escopo habilitado, retornamos vazio se falhar.
    """
    path = "/product/get_item_list"
    if not _can_use_shopee():
        return []

    ts = int(time.time())
    body = json.dumps({"shop_id": int(SHOP_ID), "page_size": limit, "page_no": 1})
    sign = _sign(path, ts, body)

    url = f"{API_BASE}{path}"
    headers = {"Content-Type": "application/json"}
    params = {
        "partner_id": int(PARTNER_ID),
        "timestamp": ts,
        "sign": sign,
        "shop_id": int(SHOP_ID)
    }

    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, params=params, content=body, headers=headers)
            if resp.status_code != 200:
                logger.warning(f"Shopee API {resp.status_code}: {resp.text[:200]}")
                return []
            data = resp.json()
            items = []
            for it in (data.get("response") or {}).get("item_list", [])[:limit]:
                title = it.get("item_name") or "Produto Shopee"
                itemid = it.get("item_id")
                link = f"https://shopee.com.br/product/{SHOP_ID}/{itemid}" if itemid else None
                if link:
                    items.append({
                        "fonte": "SHOPEE",
                        "titulo": title,
                        "preco": "—",
                        "link": link,
                        "imagem": None
                    })
            return items
        except Exception as e:
            logger.exception(f"Erro Shopee OpenAPI: {e}")
            return []

async def buscar_ofertas_shopee(categorias: List[str], max_itens: int = 2) -> List[Dict]:
    if not _can_use_shopee():
        # sem credenciais completas: silencia Shopee
        return []

    # tenta OpenAPI (melhor caminho)
    items = await _get_trending_from_openapi(limit=max_itens)
    if items:
        return items

    # fallback (placeholder) para evitar travar o bot
    out = []
    for cat in categorias:
        res = await _search_placeholder(cat, limit=max_itens)
        out.extend(res)
    return out[:max_itens * len(categorias)]
