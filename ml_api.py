import os
import requests
import random
import logging
from mercadolivre_token import atualizar_token  # Importa o atualizador automático

# Configuração de log
logger = logging.getLogger("ml_api")
logging.basicConfig(level=logging.INFO)

# Categorias de busca
CATEGORIAS = [
    "eletronicos",
    "eletrodomesticos",
    "ferramentas",
    "pecas-de-computador"
]


async def buscar_produto_mercadolivre():
    """
    Busca produtos do Mercado Livre via API oficial.
    Faz fallback automático (sem token) se houver erro 403.
    """

    categoria = random.choice(CATEGORIAS)
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={categoria}"

    access_token = os.getenv("ML_ACCESS_TOKEN")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "MercadoLivreBot/1.0"
    }

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    else:
        logger.warning("⚠️ Token de acesso do Mercado Livre não configurado.")

    try:
        logger.info(f"🤖 Buscando ofertas na plataforma: MERCADOLIVRE ({categoria})")
        response = requests.get(url, headers=headers, timeout=10)

        # Token expirado → tenta atualizar automaticamente
        if response.status_code == 401:
            logger.warning("⚠️ Token expirado. Tentando atualizar automaticamente...")
            novo_token = atualizar_token()
            if novo_token:
                headers["Authorization"] = f"Bearer {novo_token}"
                response = requests.get(url, headers=headers, timeout=10)

        # 403 → tenta sem token
        if response.status_code == 403:
            logger.warning("⚠️ Erro 403. Tentando novamente sem token (modo público)...")
            headers.pop("Authorization", None)
            response = requests.get(url, headers=headers, timeout=10)

        # Outros erros
        if response.status_code != 200:
            logger.warning(f"⚠️ Erro da API Mercado Livre: {response.status_code}")
            return None

        data = response.json()
        results = data.get("results", [])

        if not results:
            logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
            return None

        produto = random.choice(results)
        titulo = produto.get("title", "Produto sem título")
        preco = produto.get("price", "Preço não informado")
        link = produto.get("permalink", "Sem link")

        logger.info(f"✅ Produto encontrado: {titulo} - R${preco}")

        return {
            "titulo": titulo,
            "preco": preco,
            "link": link
        }

    except Exception as e:
        logger.error(f"❌ Erro inesperado ao buscar produto: {e}")
        return None
