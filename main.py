import os
import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.constants import ParseMode

# =============================
# 🔧 CONFIGURAÇÕES DO BOT
# =============================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A")
GROUP_ID = int(os.getenv("GROUP_ID", "-4983279500"))
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY", "3694ad1e-583c-4a39-bdf9-9de5674814ee")

# Configuração do logger
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)

# =============================
# 🧠 FUNÇÃO DE BUSCA NA AMAZON
# =============================
def buscar_ofertas(categoria: str):
    """Busca ofertas reais com desconto >= 15% na Amazon Brasil via ScrapeOps proxy."""
    logger.info(f"🔎 Buscando ofertas em '{categoria}'...")

    base_url = "https://www.amazon.com.br/s"
    params = {"k": categoria, "tag": AFFILIATE_TAG}

    proxy_url = "https://proxy.scrapeops.io/v1/"
    payload = {
        "api_key": SCRAPEOPS_API_KEY,
        "url": f"{base_url}?k={categoria}&tag={AFFILIATE_TAG}"
    }

    try:
        response = requests.get(proxy_url, params=payload, timeout=30)
        if response.status_code != 200:
            logger.warning(f"⚠️ Erro HTTP {response.status_code} em {categoria}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        produtos = soup.select("div[data-component-type='s-search-result']")
        resultados = []

        for p in produtos:
            nome = p.select_one("h2 a span")
            preco_atual = p.select_one(".a-price .a-offscreen")
            preco_antigo = p.select_one(".a-text-price .a-offscreen")

            if not nome or not preco_atual:
                continue

            nome = nome.text.strip()
            preco_atual_val = float(preco_atual.text.replace("R$", "").replace(".", "").replace(",", ".").strip())

            desconto = None
            if preco_antigo:
                preco_antigo_val = float(preco_antigo.text.replace("R$", "").replace(".", "").replace(",", ".").strip())
                if preco_antigo_val > preco_atual_val:
                    porcentagem = int(100 - (preco_atual_val / preco_antigo_val * 100))
                    if porcentagem >= 15:
                        desconto = f"{porcentagem}%"
            else:
                continue

            if desconto:
                link_tag = p.select_one("h2 a")
                link = "https://www.amazon.com.br" + link_tag["href"] if link_tag else "https://www.amazon.com.br"
                resultados.append({
                    "nome": nome,
                    "preco_atual": f"R$ {preco_atual_val:.2f}",
                    "preco_antigo": f"R$ {preco_antigo_val:.2f}",
                    "desconto": desconto,
                    "link": link
                })

        logger.info(f"🔍 {len(resultados)} ofertas encontradas em {categoria}")
        return resultados

    except Exception as e:
        logger.error(f"❌ Erro ao buscar {categoria}: {e}")
        return []

# =============================
# ✉️ ENVIO DAS OFERTAS
# =============================
async def enviar_oferta(oferta):
    """Envia mensagem formatada ao grupo Telegram."""
    nome = oferta["nome"]
    preco_atual = oferta["preco_atual"]
    preco_antigo = oferta["preco_antigo"]
    desconto = oferta["desconto"]
    link = oferta["link"]

    msg = (
        f"🔥 *{nome}*\n\n"
        f"💰 Preço atual: *{preco_atual}*\n"
        f"🏷️ Preço anterior: {preco_antigo}\n"
        f"💥 Desconto: *{desconto} OFF*\n\n"
        f"➡️ [Ver na Amazon]({link})"
    )

    try:
        await bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=False)
        logger.info(f"✅ Oferta enviada: {nome}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar oferta: {e}")

# =============================
# 🕒 LOOP PRINCIPAL
# =============================
async def job_buscar_e_enviar():
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca...")

    for cat in categorias:
        ofertas = buscar_ofertas(cat)
        for oferta in ofertas:
            await enviar_oferta(oferta)
            await asyncio.sleep(5)  # evita flood no Telegram
        await asyncio.sleep(2)

    logger.info("✅ Ciclo concluído!")

# =============================
# 🚀 MAIN LOOP
# =============================
async def main():
    logger.info("🤖 Iniciando bot Amazon Ofertas Brasil (loop automático a cada 5m)...")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=5)
    scheduler.start()

    await job_buscar_e_enviar()

    try:
        await asyncio.Future()  # mantém o processo ativo
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("🛑 Bot encerrado com segurança.")

if __name__ == "__main__":
    asyncio.run(main())
