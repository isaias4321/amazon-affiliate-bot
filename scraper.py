import logging
import requests
from bs4 import BeautifulSoup

AFFILIATE_TAG = "isaias06f-20"
SEARCH_TERMS = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
HEADERS = {"User-Agent": "Mozilla/5.0"}

async def buscar_ofertas_e_enviar(bot, group_id):
    logging.info("🔎 Iniciando busca de ofertas...")
    total_ofertas = 0

    for termo in SEARCH_TERMS:
        try:
            url = f"https://www.amazon.com.br/s?k={termo}&tag={AFFILIATE_TAG}"
            resp = requests.get(url, headers=HEADERS, timeout=10)

            if resp.status_code != 200:
                logging.warning(f"⚠️ Erro ao buscar {termo}: {resp.status_code}")
                continue

            soup = BeautifulSoup(resp.text, "lxml")
            produtos = soup.select(".s-result-item")

            ofertas = []
            for p in produtos:
                nome = p.select_one("h2 a span")
                preco = p.select_one(".a-price-whole")
                link = p.select_one("h2 a")
                if nome and preco and link:
                    ofertas.append(f"💥 {nome.text.strip()} - R$ {preco.text.strip()}\nhttps://www.amazon.com.br{link['href']}")

            if ofertas:
                total_ofertas += len(ofertas)
                mensagem = f"🔥 Ofertas encontradas para *{termo}*:\n\n" + "\n\n".join(ofertas[:5])
                await bot.send_message(chat_id=group_id, text=mensagem, parse_mode="Markdown")
                logging.info(f"✅ {len(ofertas)} ofertas enviadas em {termo}")
            else:
                logging.info(f"🔍 0 ofertas encontradas em {termo}")
        except Exception as e:
            logging.error(f"Erro ao processar {termo}: {e}")

    if total_ofertas == 0:
        logging.info("⚠️ Nenhuma oferta encontrada.")