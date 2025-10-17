import asyncio
import logging
import os
import re
import aiohttp
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot

# === CONFIGURAÇÕES ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8463817884:AAE23cMr1605qbMV4c79cMcr8F5dn0ETqRo")
GROUP_ID = int(os.getenv("GROUP_ID", "-1003140787649"))
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === URL BASE ===
AMAZON_BASE = "https://www.amazon.com.br/s?k={query}&s=price-asc-rank"

# === FUNÇÃO DE SCRAPING ===
async def buscar_ofertas_categoria(session, categoria):
    url = AMAZON_BASE.format(query=categoria.replace(" ", "+"))
    logging.info(f"🔍 Buscando ofertas em '{categoria}'...")
    produtos = []

    try:
        async with session.get(url, headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status != 200:
                logging.warning(f"⚠️ Falha ao acessar Amazon para {categoria} (HTTP {resp.status})")
                return []

            html = await resp.text()
            soup = BeautifulSoup(html, "html.parser")

            itens = soup.select("div[data-component-type='s-search-result']")
            for item in itens:
                nome_el = item.select_one("h2 a span")
                preco_el = item.select_one(".a-price span.a-offscreen")
                link_el = item.select_one("h2 a")
                desconto_el = item.select_one(".a-text-price")

                if not (nome_el and preco_el and link_el):
                    continue

                nome = nome_el.text.strip()
                preco = preco_el.text.strip()
                link = "https://www.amazon.com.br" + link_el["href"]

                # Tenta detectar desconto
                desconto_texto = item.select_one(".a-row.a-size-base.a-color-secondary span")
                desconto = 0
                if desconto_texto:
                    match = re.search(r"(\d+)%", desconto_texto.text)
                    if match:
                        desconto = int(match.group(1))

                if desconto >= 15:
                    produtos.append({
                        "nome": nome,
                        "preco": preco,
                        "desconto": desconto,
                        "link": f"{link}?tag={AFFILIATE_TAG}"
                    })

            logging.info(f"✅ {len(produtos)} produtos coletados via scraping para '{categoria}'")
            return produtos

    except Exception as e:
        logging.error(f"❌ Erro ao buscar {categoria}: {e}")
        return []

# === CICLO DE BUSCA ===
async def ciclo_de_busca(bot):
    categorias = ["eletrodomésticos", "processador", "ferramenta"]

    async with aiohttp.ClientSession() as session:
        todas_ofertas = []
        for categoria in categorias:
            ofertas = await buscar_ofertas_categoria(session, categoria)
            todas_ofertas.extend(ofertas)

        if not todas_ofertas:
            logging.info("⚠️ Nenhuma oferta válida encontrada neste ciclo.")
            return

        for oferta in todas_ofertas:
            msg = (
                f"🔥 *{oferta['nome']}*\n"
                f"💰 Preço: {oferta['preco']}\n"
                f"📉 Desconto: {oferta['desconto']}%\n"
                f"🔗 [Ver na Amazon]({oferta['link']})"
            )
            await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=False)

        logging.info(f"📢 {len(todas_ofertas)} ofertas enviadas para o grupo!")

# === MAIN ===
async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    scheduler = AsyncIOScheduler()

    scheduler.add_job(lambda: asyncio.create_task(ciclo_de_busca(bot)), "interval", minutes=2)
    scheduler.start()

    logging.info("🤖 Iniciando bot *Amazon Ofertas Brasil* (modo scraping, 2 em 2 minutos)...")

    # Executa o primeiro ciclo imediatamente
    await ciclo_de_busca(bot)

    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
