import aiohttp
import sqlite3
from fastapi import FastAPI, Query
from bs4 import BeautifulSoup
import time

app = FastAPI(title="Amazon Scraper API")

AFILIADO = "isaias06f-20"
CACHE_TEMPO = 3600  # 1 hora

conn = sqlite3.connect("cache.db", check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    termo TEXT PRIMARY KEY,
    titulo TEXT,
    preco TEXT,
    imagem TEXT,
    link TEXT,
    timestamp REAL
)
""")
conn.commit()


async def buscar_amazon(termo: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }
    url = f"https://www.amazon.com.br/s?k={termo.replace(' ', '+')}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    item = soup.select_one("div[data-component-type='s-search-result']")
    if not item:
        return None

    titulo = item.h2.text.strip() if item.h2 else "Sem título"
    link_tag = item.select_one("a.a-link-normal")
    link = f"https://www.amazon.com.br{link_tag['href']}" if link_tag else None
    imagem_tag = item.select_one("img.s-image")
    imagem = imagem_tag["src"] if imagem_tag else None
    preco_span = item.select_one("span.a-price > span.a-offscreen")
    preco = preco_span.text.strip() if preco_span else "Indisponível"

    if link and AFILIADO not in link:
        sep = "&" if "?" in link else "?"
        link = f"{link}{sep}tag={AFILIADO}"

    return {"titulo": titulo, "preco": preco, "imagem": imagem, "link": link}


@app.get("/buscar")
async def buscar_produto(q: str = Query(..., description="Termo de busca")):
    cur = conn.cursor()
    cur.execute("SELECT * FROM produtos WHERE termo=?", (q,))
    row = cur.fetchone()

    if row and (time.time() - row[-1]) < CACHE_TEMPO:
        return {
            "titulo": row[1],
            "preco": row[2],
            "imagem": row[3],
            "link": row[4],
            "cache": True
        }

    produto = await buscar_amazon(q)
    if not produto:
        return {"erro": "Nenhum produto encontrado"}

    conn.execute(
        "REPLACE INTO produtos VALUES (?, ?, ?, ?, ?, ?)",
        (q, produto["titulo"], produto["preco"], produto["imagem"], produto["link"], time.time())
    )
    conn.commit()

    return {**produto, "cache": False}
