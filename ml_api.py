import os
import requests
import random
import logging
from mercadolivre_token import atualizar_token  # Importa o atualizador automático

# Configuração de log
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Categorias para busca aleatória
CATEGORIAS = [
    "eletronicos",
    "eletrodomesticos",
    "ferramentas",
    "pecas-de-computador"
]


def buscar_produto_mercadolivre():
    """
    Busca produtos no Mercado Livre usando a API oficial com token dinâmico.
    Se o token expirar, ele será atualizado automaticamente.
    """

    access_token = os.getenv("ML_ACCESS_TOKEN")

    # Se não houver token, tenta gerar automaticamente
    if not access_token:
        logger.warning("⚠️ Token de acesso do Mercado Livre não configurado, tentando atualizar...")
        access_token = atualizar_token()
        if not access_token:
            logger.error("❌ Não foi possível obter um token de acesso válido.")
            return None

    categoria = random.choice(CATEGORIAS)
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={categoria}"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "MercadoLivreBot/1.0"
    }

    try:
        logger.info(f"🤖 Buscando ofertas na plataforma: MERCADOLIVRE ({categoria})")
        response = requests.get(url, headers=headers, timeout=10)

        # Token expirado → tenta atualizar e refazer a requisição
        if response.status_code == 401:
            logger.warning("⚠️ Token expirado. Tentando atualizar automaticamente...")
            novo_token = atualizar_token()
            if novo_token:
                headers["Authorization"] = f"Bearer {novo_token}"
                response = requests.get(url, headers=headers, timeout=10)

        # Se ainda der erro 403 → sem permissão ou bloqueio temporário
        if response.status_code == 403:
            logger.warning("⚠️ Erro da API Mercado Livre: 403 (acesso bloqueado ou token inválido).")
            return None

        # Se outro erro HTTP
        if response.status_code != 200:
            logger.warning(f"⚠️ Erro da API Mercado Livre: {response.status_code}")
            return None

        data = response.json()
        results = data.get("results", [])

        if not results:
            logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
            return None

        # Escolhe produto aleatório
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
