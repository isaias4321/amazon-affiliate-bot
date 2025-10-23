import aiohttp
import random
import logging

# Links afiliados válidos (adicione os seus)
AFFILIATED_LINKS = [
    "https://s.shopee.com.br/1gACNJP1z9",
    "https://s.shopee.com.br/8pdMudgZun",
    "https://s.shopee.com.br/20n2m66Bj1"
]

CATEGORIAS = [
    "relógio", "teclado", "fone de ouvido", "camiseta",
    "sapato", "smartwatch", "ferramenta", "roupa feminina"
]

logger = logging.getLogger(__name__)

async def buscar_produto_shopee():
    """Busca produtos aleatórios da Shopee"""
    categoria = random.choice(CATEGORIAS)
    url = f"https://shopee.com.br/api/v4/search/search_items?by=relevancy&limit=50&match_id=11059978&keyword={categoria}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Shopee retornou status {resp.status}")
                    return None

                data = await resp.json()
                items = data.get("items", [])
                if not items:
                    return None

                produto = random.choice(items)
                nome = produto.get("item_basic", {}).get("name", "Produto Shopee")
                preco = produto.get("item_basic", {}).get("price", 0) / 100000
                imagem = f"https://down-br.img.susercontent.com/file/{produto.get('item_basic', {}).get('image')}"
                link_afiliado = random.choice(AFFILIATED_LINKS)

                return {
                    "loja": "Shopee",
                    "titulo": nome,
                    "preco": f"R$ {preco:.2f}",
                    "imagem": imagem,
                    "link": link_afiliado
                }

    except Exception as e:
        logger.error(f"❌ Erro ao buscar produto Shopee: {e}")
        return None
