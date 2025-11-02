# =======================================
# 🌐 PROXY API — Mercado Livre + Shopee
# =======================================
from flask import Flask, request, jsonify
import requests
import hmac
import hashlib
import time
import os

app = Flask(__name__)

# ============================
# 🔧 CONFIGURAÇÕES
# ============================
SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_APP_SECRET = os.getenv("SHOPEE_APP_SECRET")


# ============================
# 🟡 MERCADO LIVRE
# ============================
@app.route("/proxy/ml")
def proxy_ml():
    termo = request.args.get("q", "celulares")
    try:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={termo}&limit=5&sort=price_asc&condition=new"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return jsonify({"error": f"HTTP {resp.status_code}"}), resp.status_code
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================
# 🟠 SHOPEE
# ============================
@app.route("/proxy/shopee")
def proxy_shopee():
    termo = request.args.get("q", "celulares")
    timestamp = int(time.time())
    api_path = "/api/v1/offer/product_offer"

    if not SHOPEE_APP_ID or not SHOPEE_APP_SECRET:
        return jsonify({"error": "Shopee não configurado"}), 400

    # Assinatura HMAC
    base_string = f"{SHOPEE_APP_ID}{api_path}{timestamp}"
    sign = hmac.new(
        SHOPEE_APP_SECRET.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    url = f"https://open-api.affiliate.shopee.com.br{api_path}"
    headers = {
        "Content-Type": "application/json",
        "X-Appid": str(SHOPEE_APP_ID),
        "X-Timestamp": str(timestamp),
        "X-Sign": sign,
    }
    payload = {"page_size": 5, "page": 1, "keyword": termo}

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code != 200:
            return jsonify({"error": f"HTTP {resp.status_code}"}), resp.status_code
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================
# 🩵 ROOT TEST
# ============================
@app.route("/")
def index():
    return jsonify({
        "status": "ok",
        "message": "Proxy ativo ✅",
        "endpoints": ["/proxy/ml?q=termo", "/proxy/shopee?q=termo"]
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
