import os
import requests
import random
import logging
from mercadolivre_token import atualizar_token  # Importa o atualizador automático

# Configuração de log
logger = logging.getLogger("ml_api")
logging.basicConfig(level=logging.INFO)

# Categorias para sortear buscas
CATEGORIAS = [
    "eletronicos",
    "eletrodomesticos",
    "ferramentas",
    "pecas-de-computador",
    "informatica",
    "acessorios",
    "smartphones"
]


async def buscar_produto_mercadolivre():
    """
    Busca produtos do Mercado Livre via API oficial.
    Evita bloqueios 403 e tenta modo público se necessário.
    """

    categoria = random.choice(CATEGORIAS)
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={categoria}"

    access_token = os.getenv("ML_ACCESS_TOKEN")

    # Headers "disfarçados" de navegador real
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/126.0.0.0 Safari/537.36"
        ),
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

        # Se ainda 403 → tenta modo público
        if response.status_code == 403:
            logger.warning("⚠️ Erro 403. Tentando novamente sem token (modo público)...")
            headers.pop("Authorization", None)
            response = requests.get(url, headers=headers, timeout=10)

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
