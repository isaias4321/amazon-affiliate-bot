import os
import re
import time
import logging
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# =========================
# 🔧 CONFIGURAÇÕES GERAIS
# =========================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AmazonBot")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")

if not TELEGRAM_TOKEN or not GROUP_CHAT_ID or not SCRAPEOPS_API_KEY:
    logger.error("❌ Faltando TELEGRAM_TOKEN, GROUP_CHAT_ID ou SCRAPEOPS_API_KEY.")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# =========================
# 🛒 CATEGORIAS
# =========================
CATEGORIAS = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]

# =========================
# 🔍 FUNÇÃO DE BUSCA
# =========================
def buscar_ofertas(categoria):
    """Busca produtos no ScrapeOps com heurística de desconto."""
    try:
        target_url = f"https://www.amazon.com.br/s?k={categoria}"
        api_url = f"https://proxy.scrapeops.io/v1/?api_key={SCRAPEOPS_API_KEY}&url={target_url}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept-Language": "pt-BR,pt;q=0.9",
        }

        resp = requests.get(api_url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.warning(f"⚠️ Erro {resp.status_code} ao buscar {categoria}")
            return []

        logger.info(f"✅ HTML recebido para '{categoria}' ({resp.status_code} OK)")
        soup = BeautifulSoup(resp.text, "html.parser")

        produtos = []
        blocos = soup.find_all("div", {"data-component-type": "s-search-result"})

        for bloco in blocos:
            titulo_elem = bloco.find("span", class_="a-text-normal")
            preco_elem = bloco.find("span", class_="a-price-whole")
            link_elem = bloco.find("a", class_="a-link-normal", href=True)

            if not (titulo_elem and preco_elem and link_elem):
                continue

            titulo = titulo_elem.get_text(strip=True)
            preco = preco_elem.get_text(strip=True).replace(".", "")
            link = f"https://www.amazon.com.br{link_elem['href'].split('?')[0]}?tag={AFFILIATE_TAG}"

            # 🎯 Heurística de desconto
            if re.search(r"(\d{1,2}%|\boff\b|promo|desconto|oferta)", titulo, re.I):
                produtos.append({
                    "titulo": titulo,
                    "preco": f"R$ {preco}",
                    "categoria": categoria,
                    "link": link
                })
            else:
                try:
                    preco_num = float(preco.replace(",", "."))
                    if preco_num < 400:  # valor “baixo” típico de promoção
                        produtos.append({
                            "titulo": titulo,
                            "preco": f"R$ {preco}",
                            "categoria": categoria,
                            "link": link
                        })
                except ValueError:
                    continue

        if not produtos:
            logger.warning(f"⚠️ Nenhuma promoção encontrada em {categoria}")
        return produtos[:5]  # limita para evitar flood

    except Exception as e:
        logger.error(f"❌ Erro ao buscar ofertas de {categoria}: {e}")
        return []

# =========================
# 💬 ENVIO TELEGRAM
# =========================
async def enviar_oferta(oferta):
    """Envia a oferta formatada para o grupo."""
    msg = (
        f"🔥 <b>OFERTA AMAZON ({oferta['categoria'].upper()})</b>\n\n"
        f"🛍️ <i>{oferta['titulo']}</i>\n"
        f"💰 <b>{oferta['preco']}</b>\n\n"
        f"➡️ <a href='{oferta['link']}'>Ver na Amazon</a>"
    )
    try:
        await bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=msg,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        logger.info(f"✅ Enviada: {oferta['titulo']}")
    except Exception as e:
        logger.error(f"Erro ao enviar oferta: {e}")

# =========================
# 🕓 AGENDADOR
# =========================
async def job_buscar_e_enviar():
    logger.info("🔄 Iniciando ciclo de busca real de ofertas...")
    for cat in CATEGORIAS:
        ofertas = buscar_ofertas(cat)
        for oferta in ofertas:
            await enviar_oferta(oferta)
            await asyncio.sleep(8)
    logger.info("✅ Ciclo concluído!")

async def main():
    logger.info("🤖 Iniciando bot Amazon Affiliate (promoções reais, ScrapeOps ativo)...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=10)
    scheduler.start()
    await job_buscar_e_enviar()
    await asyncio.Future()  # mantém rodando

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
