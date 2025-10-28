import os
import time
import json
import hmac
import base64
import hashlib
from typing import List, Dict
import httpx
import logging

logger = logging.getLogger(__name__)

# PA-API 5
ACCESS_KEY = os.getenv("AMAZON_ACCESS_KEY", "").strip()
SECRET_KEY = os.getenv("AMAZON_SECRET_KEY", "").strip()
ASSOC_TAG  = os.getenv("AMAZON_ASSOCIATE_TAG", "").strip()
HOST       = os.getenv("AMAZON_HOST", "webservices.amazon.com.br").strip()
REGION     = os.getenv("AMAZON_REGION", "us-east-1").strip()

# Endpoints PA-API 5
ENDPOINT = f"https://{HOST}/paapi5/searchitems"

# Assinatura V4 (PA-API usa SigV4 em HTTP + JSON)
def _sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

def _get_signature_key(key, dateStamp, regionName, serviceName):
    kDate = _sign(("AWS4" + key).encode("utf-8"), dateStamp)
    kRegion = _sign(kDate, regionName)
    kService = _sign(kRegion, serviceName)
    kSigning = _sign(kService, "aws4_request")
    return kSigning

async def _paapi_search(keywords: str, max_results: int = 2) -> List[Dict]:
    if not (ACCESS_KEY and SECRET_KEY and ASSOC_TAG):
        logger.warning("Amazon PA-API não configurada. Pulei Amazon.")
        return []

    payload = {
        "Keywords": keywords,
        "Resources": [
            "Images.Primary.Large",
            "ItemInfo.Title",
            "Offers.Listings.Price"
        ],
        "PartnerTag": ASSOC_TAG,
        "PartnerType": "Associates",
        "Marketplace": "www.amazon.com.br",
        "ItemCount": max_results
    }
    request_payload = json.dumps(payload)

    # Cabeçalhos para SigV4
    method = "POST"
    service = "ProductAdvertisingAPI"
    content_type = "application/json; charset=UTF-8"
    amz_target = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"

    t = time.gmtime()
    amz_date = time.strftime("%Y%m%dT%H%M%SZ", t)
    datestamp = time.strftime("%Y%m%d", t)

    canonical_uri = "/paapi5/searchitems"
    canonical_querystring = ""
    canonical_headers = f"content-encoding:amz-1.0\ncontent-type:{content_type}\nhost:{HOST}\nx-amz-date:{amz_date}\nx-amz-target:{amz_target}\n"
    signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"
    payload_hash = hashlib.sha256(request_payload.encode("utf-8")).hexdigest()
    canonical_request = "\n".join([method, canonical_uri, canonical_querystring, canonical_headers, signed_headers, payload_hash])

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{datestamp}/{REGION}/{service}/aws4_request"
    string_to_sign = "\n".join([algorithm, amz_date, credential_scope, hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()])

    signing_key = _get_signature_key(SECRET_KEY, datestamp, REGION, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    headers = {
        "Content-Encoding": "amz-1.0",
        "Content-Type": content_type,
        "X-Amz-Date": amz_date,
        "X-Amz-Target": amz_target,
        "Authorization": f"{algorithm} Credential={ACCESS_KEY}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}",
        "Host": HOST
    }

    items: List[Dict] = []
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(ENDPOINT, headers=headers, content=request_payload)
            if resp.status_code != 200:
                logger.warning(f"Amazon API {resp.status_code}: {resp.text[:300]}")
                return []

            data = resp.json()
            for it in (data.get("SearchResult", {}) or {}).get("Items", []):
                title = (((it.get("ItemInfo") or {}).get("Title") or {}).get("DisplayValue")) or "Produto Amazon"
                url   = it.get("DetailPageURL")
                price = None
                try:
                    price = it["Offers"]["Listings"][0]["Price"]["DisplayAmount"]
                except Exception:
                    pass
                img = None
                try:
                    img = it["Images"]["Primary"]["Large"]["URL"]
                except Exception:
                    pass

                if url:
                    items.append({
                        "fonte": "AMAZON",
                        "titulo": title,
                        "preco": price or "—",
                        "link": url,
                        "imagem": img
                    })
        except Exception as e:
            logger.exception(f"Falha PA-API: {e}")
    return items

async def buscar_ofertas_amazon(categorias: List[str], max_itens: int = 2) -> List[Dict]:
    resultados: List[Dict] = []
    for cat in categorias:
        # keywords simples por categoria
        kw = {
            "eletronicos": "eletrônicos ofertas",
            "pecas de computador": "hardware pc ofertas",
            "eletrodomesticos": "eletrodomésticos ofertas",
            "ferramentas": "ferramentas elétricas ofertas"
        }.get(cat.lower(), cat)
        items = await _paapi_search(kw, max_results=max_itens)
        resultados.extend(items)
    return resultados[:max_itens * len(categorias)]
