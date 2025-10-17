import os
import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# =============================
# 🔧 CONFIGURAÇÕES GERAIS
# =============================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8463817884:AAE23cMr1605qbMV4c79cMcr8F5dn0ETqRo")
GROUP_ID = int(os.getenv("GROUP_ID", "-1003140787649"))
AXESSO_API_KEY = os.getenv("AXESSO_API_KEY", "fb2f7fd38c57470489d000c1c7aa8cd6")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")

# Categorias que serão buscadas
CATEGORIES = ["eletrodomesticos", "computers", "tools"]

# Configurar logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Inicializar o bot
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# =============================
# 🔍 FUNÇÃO: Buscar Ofertas
# =============================
async def buscar_ofertas(categoria):
    """Busca ofertas usando Axesso API; fallback com scraping da Amazon"""
    logging.info(f"🔍 Buscando ofertas na categoria '{categoria}'...")

    base_url = "https://api.axesso.de/amz/amazon-best-sellers-list"
    params = {"url": f"https://www.amazon.com.br/s?k={categoria}"}
    headers = {"x-api-key": AXESSO_API_KEY}

    try:
        response = requests.get(base_url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("countProducts", 0) > 0:
                produtos = data.get("products", [])
                logging.info(f"✅ {len(produtos)} ofertas encontradas em {categoria} via Axesso API.")
                return produtos
            else:
                logging.warning(f"⚠️ Nenhuma oferta encontrada na API para '{categoria}'.")
                return []
        elif response.status_code == 401:
            logging.warning(f"⚠️ Erro 401 — chave API inválida para '{categoria}', usando scraping como fallback...")
            return await scraping_fallback(categoria)
        else:
            logging.error(f"❌ Erro {response.status_code} ao buscar '{categoria}'")
            return await scraping_fallback(categoria)
    except Exception as e:
        logging.error(f"❌ Erro inesperado em '{categoria}': {e}")
        return await scraping_fallback(categoria)

# =============================
# 🕵️ FUNÇÃO: Scraping Fallback
# =============================
async def scraping_fallback(categoria):
    """Busca produtos via scraping direto da Amazon (fallback)"""
    try:
        logging.info(f"🕵️ Usando fallback scraping para '{categoria}'...")
        url = f"https://www.amazon.com.br/s?k={categoria}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            logging.error(f"❌ Falha ao acessar Amazon para {categoria}")
            return []

        try:
            soup = BeautifulSoup(response.text, "lxml")
        except Exception:
            soup = BeautifulSoup(response.text, "html.parser")

        produtos = []
        for item in soup.select(".s-result-item"):
            titulo = item.select_one("h2 a span")
            preco = item.select_one(".a-price span.a-offscreen")
            link = item.select_one("h2 a")

            if titulo and preco and link:
                produtos.append({
                    "productTitle": titulo.text.strip(),
                    "productRating": "",
                    "countReview": "",
                    "url": f"https://www.amazon.com.br{link['href']}",
                })
        logging.info(f"✅ {len(produtos)} produtos coletados via fallback para '{categoria}'")
        return produtos

    except Exception as e:
        logging.error(f"❌ Erro no fallback '{categoria}': {e}")
        return []

# =============================
# 💬 ENVIAR MENSAGEM PARA TELEGRAM
# =============================
async def enviar_mensagem(bot, produto):
    try:
        nome = produto.get("productTitle", "Produto sem nome")
        url = produto.get("url", "")
        msg = (
            f"🔥 *{nome}*\n"
            f"[Ver na Amazon](https://www.amazon.com.br{url})\n"
            f"🛒 #{produto.get('productRating', '⭐️Sem avaliação')}"
        )

        await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"⚠️ Erro ao enviar mensagem para Telegram: {e}")

# =============================
# 🔁 CICLO PRINCIPAL
# =============================
async def ciclo_de_busca():
    logging.info("🔄 Iniciando ciclo de busca de ofertas...")
    ofertas_encontradas = False

    for categoria in CATEGORIES:
        produtos = await buscar_ofertas(categoria)
        if produtos:
            ofertas_encontradas = True
            for produto in produtos[:3]:  # limita 3 por categoria
                await enviar_mensagem(bot, produto)
        else:
            logging.info(f"⚠️ Nenhuma oferta válida encontrada em {categoria}.")

    if not ofertas_encontradas:
        logging.info("⚠️ Nenhuma oferta encontrada neste ciclo.")
    else:
        logging.info("✅ Ciclo concluído e ofertas enviadas!")

# =============================
# 🚀 MAIN
# =============================
async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(ciclo_de_busca, "interval", minutes=2)
    scheduler.start()

    logging.info("🤖 Iniciando bot *Amazon Ofertas Brasil* (2 em 2 minutos)...")
    await ciclo_de_busca()

    # Mantém o bot rodando
    while True:
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
