import os
import aiohttp
import asyncio
import logging
import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# -------------------------------
# 1️⃣ Inicialização e Logging
# -------------------------------
load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AmazonAffiliateBot")

# -------------------------------
# 2️⃣ Variáveis de Ambiente
# -------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY", "3694ad1e-583c-4a39-bdf9-9de5674814ee")

if not TELEGRAM_TOKEN or not GROUP_CHAT_ID:
    logger.error("❌ Faltando TELEGRAM_TOKEN ou GROUP_CHAT_ID no ambiente!")
    raise SystemExit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# -------------------------------
# 3️⃣ Função de Busca com Fallback
# -------------------------------
SCRAPEOPS_PROXY = "https://proxy.scrapeops.io/v1/"

async def fetch_amazon_html(term: str) -> str | None:
    """
    Busca HTML da página da Amazon via ScrapeOps (com fallback direto).
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    params = {"api_key": SCRAPEOPS_API_KEY, "url": f"https://www.amazon.com.br/s?k={term}"}

    for attempt in range(2):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(SCRAPEOPS_PROXY, params=params, headers=headers, timeout=20) as resp:
                    html = await resp.text()
                    logger.info(f"🛰️ ScrapeOps {resp.status} — {term} (tentativa {attempt + 1})")

                    if resp.status == 200 and "Amazon.com.br" in html:
                        return html
                    await asyncio.sleep(2)
        except Exception as e:
            logger.warning(f"⚠️ Erro ScrapeOps ({term}): {e}")
            await asyncio.sleep(2)

    # 🔁 Fallback: conexão direta
    logger.warning(f"🌐 Usando modo direto para '{term}'...")
    try:
        r = requests.get(f"https://www.amazon.com.br/s?k={term}", headers=headers, timeout=20)
        if r.status_code == 200:
            return r.text
        logger.warning(f"HTTP {r.status_code} no fallback direto para '{term}'")
    except Exception as e:
        logger.error(f"Erro direto para '{term}': {e}")
    return None

# -------------------------------
# 4️⃣ Simulação de Produtos (Temporário)
# -------------------------------
def extrair_ofertas_fake() -> list[dict]:
    """
    Simula produtos para demonstração.
    """
    exemplos = [
        {
            "nome": "Notebook Acer Aspire 5 (R$ 500 de desconto)",
            "preco": "R$ 2.999,00",
            "link": f"https://www.amazon.com.br/dp/B0CRFYR38G?tag={AFFILIATE_TAG}",
            "categoria": "Informática",
        },
        {
            "nome": "Smartphone Samsung Galaxy A15 (30% OFF)",
            "preco": "R$ 999,90",
            "link": f"https://www.amazon.com.br/dp/B0D3X95R51?tag={AFFILIATE_TAG}",
            "categoria": "Celulares",
        },
        {
            "nome": "Fone Bluetooth JBL Tune 510BT (20% OFF)",
            "preco": "R$ 299,90",
            "link": f"https://www.amazon.com.br/dp/B08W5FXXP8?tag={AFFILIATE_TAG}",
            "categoria": "Áudio",
        },
    ]
    return exemplos

# -------------------------------
# 5️⃣ Envio Telegram
# -------------------------------
async def enviar_oferta(oferta: dict):
    msg = (
        f"🔥 <b>OFERTA AMAZON - {oferta['categoria']}</b> 🔥\n\n"
        f"📦 <i>{oferta['nome']}</i>\n"
        f"💰 <b>{oferta['preco']}</b>\n\n"
        f"➡️ <a href='{oferta['link']}'>COMPRAR NA AMAZON</a>"
    )
    try:
        await bot.send_message(GROUP_CHAT_ID, msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        logger.info(f"✅ Enviado: {oferta['nome']}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar oferta: {e}")

# -------------------------------
# 6️⃣ Agendador Principal
# -------------------------------
async def job_buscar_e_enviar():
    termos = ["notebook", "celular", "fone bluetooth", "tv", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca...")

    for termo in termos:
        html = await fetch_amazon_html(termo)
        if not html:
            logger.warning(f"⚠️ Falha ao buscar '{termo}'")
            continue

        ofertas = extrair_ofertas_fake()
        for o in ofertas:
            await enviar_oferta(o)
            await asyncio.sleep(5)
    logger.info("✅ Ciclo concluído!")

# -------------------------------
# 7️⃣ Loop Assíncrono Principal
# -------------------------------
async def main():
    logger.info("🤖 Iniciando bot Amazon Affiliate (versão moderna)...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=3)
    scheduler.start()

    await job_buscar_e_enviar()

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
