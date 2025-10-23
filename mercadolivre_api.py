import aiohttp
import random
import logging

CATEGORIAS = [
    "smartphone", "notebook", "fones de ouvido",
    "teclado gamer", "mouse gamer", "relógio inteligente",
    "ferramentas", "acessórios femininos"
]

ML_AFF_ID = "im20250701092308"
logger = logging.getLogger(__name__)

async def buscar_produto_ml():
    """Busca produtos reais do Mercado Livre via API pública."""
    categoria = random.choice(CATEGORIAS)
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={categoria}&limit=50"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Mercado Livre retornou status {resp.status}")
                    return None

                data = await resp.json()
                produtos = data.get("results", [])
                if not produtos:
                    return None

                produto = random.choice(produtos)
                nome = produto.get("title", "Produto Mercado Livre")
                preco = produto.get("price", 0)
                imagem = produto.get("thumbnail", "")
                link = f"{produto.get('permalink', '')}?utm_source={ML_AFF_ID}"

                return {
                    "loja": "Mercado Livre",
                    "titulo": nome,
                    "preco": f"R$ {preco:.2f}",
                    "imagem": imagem,
                    "link": link
                }

    except Exception as e:
        logger.error(f"❌ Erro ao buscar produto Mercado Livre: {e}")
        return None
