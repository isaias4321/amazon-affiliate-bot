import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==============================
# 🔧 CONFIGURAÇÕES DO BOT
# ==============================
TELEGRAM_TOKEN = "8463817884:AAG1cuPG4l77RFy8l95WsCjj9tp88dRDomE"
GROUP_ID = -1003140787649
AFFILIATE_TAG = "isaias06f-20"
CATEGORIES = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]

# ==============================
# ⚙️ LOGGING
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ==============================
# 🔍 FUNÇÃO DE BUSCA DE OFERTAS
# ==============================
async def buscar_ofertas(categoria):
    logging.info(f"🔍 Buscando ofertas em '{categoria}'...")
    url = f"https://www.amazon.com.br/s?k={categoria}&i=aps&sort=price-asc-rank"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        logging.info(f"✅ HTML recebido para '{categoria}' ({response.status_code} OK)")

        soup = BeautifulSoup(response.text, "lxml")
        produtos = soup.select("div[data-component-type='s-search-result']")
        ofertas = []

        for p in produtos:
            nome = p.select_one("h2 a span")
            preco = p.select_one(".a-price span.a-offscreen")
            link = p.select_one("h2 a")

            if not nome or not preco or not link:
                continue

            nome = nome.get_text(strip=True)
            preco = preco.get_text(strip=True)
            link = "https://www.amazon.com.br" + link["href"].split("?")[0]
            link_afiliado = f"{link}?tag={AFFILIATE_TAG}"

            ofertas.append((nome, preco, link_afiliado))

        logging.info(f"🔍 {len(ofertas)} ofertas encontradas em {categoria}")
        return ofertas

    except Exception as e:
        logging.error(f"❌ Erro ao buscar {categoria}: {e}")
        return []

# ==============================
# 💬 ENVIO DAS OFERTAS
# ==============================
async def enviar_ofertas(bot, ofertas):
    if not ofertas:
        logging.info("⚠️ Nenhuma oferta válida encontrada.")
        return

    for nome, preco, link in ofertas:
        msg = (
            f"🔥 *{nome}*\n"
            f"💰 {preco}\n"
            f"[🛒 Ver oferta na Amazon]({link})"
        )
        try:
            await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception as e:
            logging.error(f"❌ Erro ao enviar mensagem: {e}")
        await asyncio.sleep(1)  # evita flood

# ==============================
# ♻️ CICLO DE BUSCA E ENVIO
# ==============================
async def ciclo_de_busca(bot):
    logging.info("🔄 Iniciando ciclo de busca de ofertas...")
    for categoria in CATEGORIES:
        ofertas = await buscar_ofertas(categoria)
        if ofertas:
            await enviar_ofertas(bot, ofertas)
        else:
            logging.info(f"⚠️ Nenhuma oferta válida encontrada em {categoria}.")
        await asyncio.sleep(2)
    logging.info("✅ Ciclo concluído!")

# ==============================
# 🚀 INÍCIO DO BOT
# ==============================
async def main():
    bot = Bot(token=TELEGRAM_TOKEN)
    scheduler = AsyncIOScheduler(timezone="UTC")

    # executa o ciclo imediatamente e depois a cada 2 minutos
    scheduler.add_job(lambda: asyncio.create_task(ciclo_de_busca(bot)), "interval", minutes=2)
    scheduler.start()

    logging.info("🤖 Iniciando bot Amazon Ofertas Brasil (a cada 2 minutos)...")

    # mantém o processo ativo no Railway
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
