import os
import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# -----------------------------------------------------
# 1. Configuração do logging
# -----------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 2. Variáveis de ambiente
# -----------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")

if not all([TELEGRAM_TOKEN, GROUP_CHAT_ID, AFFILIATE_TAG, SCRAPEOPS_API_KEY]):
    logger.error("❌ Algumas variáveis de ambiente estão faltando. Verifique o arquivo .env.")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# -----------------------------------------------------
# 3. Função de busca de produtos na Amazon via ScrapeOps
# -----------------------------------------------------
def buscar_produtos_amazon(categoria):
    base_url = "https://proxy.scrapeops.io/v1/"
    target_url = f"https://www.amazon.com.br/s?k={categoria}"

    params = {
        "api_key": SCRAPEOPS_API_KEY,
        "url": target_url
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)
        if response.status_code != 200:
            logger.warning(f"⚠️ Erro HTTP {response.status_code} ao buscar {categoria}")
            return []

        soup = BeautifulSoup(response.text, "html.parser")

        produtos = []
        resultados = soup.select("div[data-component-type='s-search-result']")

        for item in resultados[:5]:  # Limita a 5 resultados
            nome = item.select_one("h2 a span")
            preco_atual = item.select_one(".a-price-whole")
            preco_antigo = item.select_one(".a-text-price .a-offscreen")
            link_tag = item.select_one("h2 a")

            if not nome or not link_tag or not preco_atual:
                continue

            nome = nome.text.strip()
            link = "https://www.amazon.com.br" + link_tag["href"].split("?")[0]
            preco_atual = preco_atual.text.strip()
            preco_antigo = preco_antigo.text.strip() if preco_antigo else None

            # Calcula desconto (se houver preço antigo)
            desconto = None
            if preco_antigo:
                try:
                    preco1 = float(preco_antigo.replace("R$", "").replace(".", "").replace(",", "."))
                    preco2 = float(preco_atual.replace("R$", "").replace(".", "").replace(",", "."))
                    desconto = round(100 - (preco2 / preco1 * 100))
                except:
                    desconto = None

            produtos.append({
                "nome": nome,
                "preco_atual": f"R$ {preco_atual}",
                "preco_antigo": f"R$ {preco_antigo}" if preco_antigo else None,
                "desconto": f"{desconto}%" if desconto else None,
                "link": f"{link}?tag={AFFILIATE_TAG}",
                "categoria": categoria
            })

        return produtos

    except Exception as e:
        logger.error(f"❌ Erro ao buscar produtos da categoria {categoria}: {e}")
        return []

# -----------------------------------------------------
# 4. Envio das ofertas no Telegram
# -----------------------------------------------------
async def enviar_oferta(oferta):
    msg = f"🔥 <b>Oferta Amazon - {oferta['categoria'].capitalize()}</b> 🔥\n\n"
    msg += f"📦 <b>{oferta['nome']}</b>\n"
    msg += f"💰 <b>{oferta['preco_atual']}</b>\n"
    if oferta["preco_antigo"]:
        msg += f"🪶 De: <strike>{oferta['preco_antigo']}</strike>\n"
    if oferta["desconto"]:
        msg += f"💥 Desconto: {oferta['desconto']}\n"
    msg += f"🔗 <a href='{oferta['link']}'>Compre agora na Amazon</a>"

    try:
        await bot.send_message(GROUP_CHAT_ID, msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        logger.info(f"✅ Oferta enviada: {oferta['nome']}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar oferta: {e}")

# -----------------------------------------------------
# 5. Loop principal
# -----------------------------------------------------
async def job_buscar_e_enviar():
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca...")

    for categoria in categorias:
        produtos = buscar_produtos_amazon(categoria)
        for produto in produtos:
            await enviar_oferta(produto)
            await asyncio.sleep(5)

    logger.info("✅ Ciclo concluído!")

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=5)
    scheduler.start()
    await job_buscar_e_enviar()
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
