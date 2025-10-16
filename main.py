import os
import asyncio
import logging
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# -----------------------------------------------------
# 1️⃣ CONFIGURAÇÃO DE LOGS COLORIDOS
# -----------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 2️⃣ VARIÁVEIS DE AMBIENTE
# -----------------------------------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY", "3694ad1e-583c-4a39-bdf9-9de5674814ee")

if not TELEGRAM_TOKEN or not GROUP_ID:
    logger.error("❌ Faltando TELEGRAM_TOKEN ou GROUP_ID nas variáveis de ambiente!")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# -----------------------------------------------------
# 3️⃣ FUNÇÃO DE RASPAGEM COM SCRAPEOPS
# -----------------------------------------------------
def buscar_html_amazon(query: str) -> str | None:
    """
    Faz a busca real na Amazon via ScrapeOps Proxy API.
    Retorna o HTML da página de busca.
    """
    url_base = "https://www.amazon.com.br/s"
    params = {"k": query}

    proxy_url = "https://proxy.scrapeops.io/v1/"
    try:
        resp = requests.get(
            proxy_url,
            params={
                "api_key": SCRAPEOPS_API_KEY,
                "url": f"{url_base}?k={query}",
            },
            timeout=20
        )

        if resp.status_code == 200:
            logger.info(f"✅ HTML recebido para '{query}' (200 OK)")
            return resp.text
        else:
            logger.warning(f"⚠️ Erro HTTP {resp.status_code} ao buscar '{query}'")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ScrapeOps '{query}': {e}")
        return None

# -----------------------------------------------------
# 4️⃣ EXTRAÇÃO DE OFERTAS REAIS
# -----------------------------------------------------
def extrair_ofertas_real(html: str, categoria: str) -> list[dict]:
    """
    Extrai os produtos e monta links válidos com a tag de afiliado.
    """
    soup = BeautifulSoup(html, "html.parser")
    itens = soup.select("div.s-result-item[data-asin]")
    ofertas = []

    for item in itens[:5]:
        nome = item.select_one("h2 a span")
        preco = item.select_one("span.a-price span.a-offscreen")
        link = item.select_one("h2 a")

        if not nome or not link:
            continue

        titulo = nome.text.strip()
        preco_txt = preco.text.strip() if preco else "Preço indisponível"

        raw_link = link.get("href")

        # Monta link válido completo
        if raw_link:
            if raw_link.startswith("/"):
                raw_link = urljoin("https://www.amazon.com.br", raw_link)

            if "tag=" not in raw_link:
                separator = "&" if "?" in raw_link else "?"
                raw_link = f"{raw_link}{separator}tag={AFFILIATE_TAG}"

            link_final = raw_link
        else:
            link_final = "https://www.amazon.com.br"

        ofertas.append({
            "nome": titulo,
            "preco": preco_txt,
            "link": link_final,
            "categoria": categoria.capitalize(),
        })

    return ofertas

# -----------------------------------------------------
# 5️⃣ ENVIO PARA O TELEGRAM
# -----------------------------------------------------
async def enviar_oferta_telegram(oferta: dict):
    """
    Envia mensagem formatada para o grupo.
    """
    mensagem = (
        f"🔥 <b>{oferta['categoria']} - Oferta Amazon</b>\n\n"
        f"🛒 <i>{oferta['nome']}</i>\n"
        f"💰 {oferta['preco']}\n\n"
        f"➡️ <a href=\"{oferta['link']}\">Ver na Amazon</a>"
    )

    try:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=mensagem,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False
        )
        logger.info(f"✅ Enviado: {oferta['nome']}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar para Telegram: {e}")

# -----------------------------------------------------
# 6️⃣ CICLO PRINCIPAL
# -----------------------------------------------------
async def job_buscar_e_enviar():
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca...")

    for categoria in categorias:
        html = buscar_html_amazon(categoria)
        if not html:
            continue

        ofertas = extrair_ofertas_real(html, categoria)
        if ofertas:
            for oferta in ofertas:
                await enviar_oferta_telegram(oferta)
                await asyncio.sleep(10)
        else:
            logger.warning(f"⚠️ Nenhuma oferta encontrada em {categoria}")

    logger.info("✅ Ciclo concluído!\n")

# -----------------------------------------------------
# 7️⃣ MAIN LOOP
# -----------------------------------------------------
async def main():
    logger.info("🤖 Iniciando bot Amazon Affiliate com ScrapeOps (versão 2025)...")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=5)

    await job_buscar_e_enviar()  # executa a primeira imediatamente
    scheduler.start()

    try:
        await asyncio.Future()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("🛑 Bot finalizado manualmente.")

if __name__ == "__main__":
    asyncio.run(main())
