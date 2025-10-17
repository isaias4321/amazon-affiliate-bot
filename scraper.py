import requests
import logging
from bs4 import BeautifulSoup
from telegram import Bot

# === BUSCA COM A API AXESSO ===
def buscar_ofertas_categoria(categoria: str, api_key: str):
    try:
        url = "http://api.axesso.de/amz/amazon-best-sellers-list"
        params = {
            "url": f"https://www.amazon.com.br/gp/bestsellers/{categoria}",
            "page": 1
        }
        headers = {"x-api-key": api_key}
        response = requests.get(url, params=params, headers=headers, timeout=30)

        if response.status_code == 401:
            logging.warning(f"⚠️ Erro 401 — chave API inválida para '{categoria}', usando scraping como fallback...")
            return buscar_ofertas_fallback(categoria)

        if response.status_code != 200:
            logging.error(f"❌ Erro {response.status_code} ao buscar categoria {categoria}")
            return []

        data = response.json()
        produtos = data.get("products", [])
        ofertas = []

        for produto in produtos:
            nome = produto.get("productTitle")
            rating = produto.get("productRating", "N/A")
            reviews = produto.get("countReview", 0)
            link = "https://www.amazon.com.br" + produto.get("url", "")

            ofertas.append({
                "nome": nome,
                "avaliacao": rating,
                "reviews": reviews,
                "link": link
            })

        return ofertas

    except Exception as e:
        logging.error(f"❌ Erro ao buscar '{categoria}': {e}")
        return []


# === FALLBACK — scraping direto da Amazon caso a API falhe ===
def buscar_ofertas_fallback(categoria: str):
    try:
        logging.info(f"🕵️ Usando fallback scraping para '{categoria}'...")
        url = f"https://www.amazon.com.br/s?k={categoria}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logging.error(f"❌ Falha ao acessar Amazon para {categoria}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        items = soup.select(".s-result-item h2 a")
        ofertas = []

        for item in items[:10]:
            nome = item.get_text(strip=True)
            link = "https://www.amazon.com.br" + item.get("href")
            ofertas.append({
                "nome": nome,
                "avaliacao": "N/A",
                "reviews": 0,
                "link": link
            })

        return ofertas

    except Exception as e:
        logging.error(f"❌ Erro no fallback '{categoria}': {e}")
        return []


# === FUNÇÃO PRINCIPAL — envia as ofertas ===
async def buscar_ofertas_e_enviar(bot: Bot, chat_id: str, categorias: list, api_key: str):
    ofertas_totais = []

    for categoria in categorias:
        logging.info(f"🔍 Buscando ofertas na categoria '{categoria}'...")
        ofertas = buscar_ofertas_categoria(categoria, api_key)
        if ofertas:
            ofertas_totais.extend(ofertas)

    if not ofertas_totais:
        logging.info("⚠️ Nenhuma oferta encontrada neste ciclo.")
        return

    for oferta in ofertas_totais[:10]:
        msg = (
            f"🔥 *{oferta['nome']}*\n"
            f"⭐ Avaliação: {oferta['avaliacao']}\n"
            f"💬 Reviews: {oferta['reviews']}\n"
            f"🔗 [Ver na Amazon]({oferta['link']})"
        )
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=msg,
                parse_mode="Markdown",
                disable_web_page_preview=False
            )
        except Exception as e:
            logging.error(f"❌ Erro ao enviar mensagem: {e}")
