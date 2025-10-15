import aiohttp
import asyncio
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from colorama import init, Fore
import logging
import time

# Inicializa colorama
init(autoreset=True)

# FastAPI
app = FastAPI(title="Amazon Offers API", version="3.0")

# Logger colorido
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(message)s", datefmt="%H:%M:%S")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Função de scraping real
async def buscar_amazon(categoria: str):
    url = f"https://www.amazon.com.br/s?k={categoria.replace(' ', '+')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/119.0 Safari/537.36"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Erro HTTP {resp.status}")
            html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    itens = soup.select("div[data-asin][data-component-type='s-search-result']")

    resultados = []
    for item in itens[:5]:  # pega apenas os 5 primeiros
        titulo = item.select_one("h2 a span")
        preco = item.select_one(".a-price span.a-offscreen")
        link = item.select_one("h2 a")

        if not (titulo and preco and link):
            continue

        resultados.append({
            "titulo": titulo.text.strip(),
            "preco": preco.text.strip(),
            "link": "https://www.amazon.com.br" + link["href"]
        })

    return resultados


# Rota principal
@app.get("/buscar")
async def buscar(q: str):
    inicio = time.time()
    logger.info(Fore.CYAN + f"🔍 Buscando ofertas reais de: {q}")

    try:
        resultados = await buscar_amazon(q)
        tempo = round(time.time() - inicio, 2)

        if not resultados:
            logger.warning(Fore.YELLOW + f"⚠️ Nenhum produto encontrado para {q}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "no_results",
                    "categoria": q,
                    "tempo_resposta": f"{tempo}s",
                    "mensagem": "Nenhum produto encontrado",
                }
            )

        logger.info(Fore.GREEN + f"✅ {len(resultados)} ofertas encontradas em {tempo}s")
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "categoria": q,
                "tempo_resposta": f"{tempo}s",
                "quantidade": len(resultados),
                "produtos": resultados,
            },
        )

    except Exception as e:
        logger.error(Fore.RED + f"❌ Erro ao buscar {q}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "categoria": q,
                "mensagem": str(e),
            },
        )


@app.get("/")
async def root():
    return JSONResponse(
        status_code=200,
        content={
            "status": "online",
            "mensagem": "API de Ofertas Amazon funcionando 🚀",
            "exemplo": "/buscar?q=notebook",
        },
    )
