import aiohttp
import random
import logging

logger = logging.getLogger(__name__)

# Categorias que o bot vai buscar
CATEGORIAS = {
    "Eletrônicos": "MLB1648",
    "Eletrodomésticos": "MLB5726",
    "Ferramentas": "MLB263532",
    "Peças de Computador": "MLB1649"
}

# Cabeçalhos para simular um navegador real (evita erro 403)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/118.0.5993.118 Safari/537.36"
    ),
    "Accept": "application/json"
}


async def buscar_produto_mercadolivre():
    """Busca produtos aleatórios no Mercado Livre (API pública com User-Agent)."""
    categoria_nome, categoria_id = random.choice(list(CATEGORIAS.items()))
    url = f"https://api.mercadolibre.com/sites/MLB/search?category={categoria_id}&limit=50"

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, timeout=15) as resp:
                if resp.status != 200:
                    logger.warning(f"⚠️ Mercado Livre retornou status {resp.status}")
                    return None

                data = await resp.json()
                results = data.get("results", [])
                if not results:
                    logger.warning("⚠️ Nenhum produto encontrado no Mercado Livre")
                    return None

                produto = random.choice(results)
                return {
                    "loja": "Mercado Livre",
                    "titulo": produto.get("title"),
                    "preco": f"R$ {produto.get('price', 0):.2f}",
                    "imagem": produto.get("thumbnail"),
                    "link": produto.get("permalink"),
                    "categoria": categoria_nome
                }

    except Exception as e:
        logger.error(f"❌ Erro ao buscar produto no Mercado Livre: {e}")
        return None
