import os
import asyncio
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ---------------------------- LOGGING CONFIG ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------- VARIÁVEIS DE AMBIENTE ----------------------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")

if not all([TELEGRAM_TOKEN, GROUP_ID, SCRAPEOPS_API_KEY]):
    logger.error("❌ Faltando TELEGRAM_TOKEN, GROUP_ID ou SCRAPEOPS_API_KEY nas variáveis de ambiente!")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# ---------------------------- FUNÇÕES DE BUSCA ----------------------------

def scrapeops_get(url: str):
    """Faz uma requisição via ScrapeOps Proxy"""
    proxy_url = "https://proxy.scrapeops.io/v1/"
    params = {
        "api_key": SCRAPEOPS_API_KEY,
        "url": url,
    }
    try:
        r = requests.get(proxy_url, params=params, timeout=30)
        if r.status_code == 200:
            return r.text
        else:
            logger.warning(f"⚠️ Erro HTTP {r.status_code} para {url}")
            return None
    except Exception as e:
        logger.warning(f"⚠️ Falha na requisição para {url}: {e}")
        return None


def extrair_produtos(categoria: str):
    """Busca produtos reais e extrai promoções"""
    base_url = f"https://www.amazon.com.br/s?k={categoria}"
    html = scrapeops_get(base_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    produtos = []

    # Captura dos blocos de produto
    for item in soup.select("div.s-result-item[data-asin]"):
        asin = item.get("data-asin")
        if not asin:
            continue

        nome_tag = item.select_one("h2 a span")
        preco_tag = item.select_one("span.a-price-whole")

        if not nome_tag or not preco_tag:
            continue

        nome = nome_tag.text.strip()
        preco_texto = preco_tag.text.strip().replace(".", "").replace(",", ".")
        try:
            preco_atual = float(preco_texto)
        except:
            continue

        link = f"https://www.amazon.com.br/dp/{asin}?tag={AFFILIATE_TAG}"

        # Acessa página individual para tentar achar preço antigo
        html_produto = scrapeops_get(link)
        if not html_produto:
            continue

        produto_soup = BeautifulSoup(html_produto, "html.parser")

        preco_antigo_tag = produto_soup.select_one("span.a-text-price span.a-offscreen")
        if preco_antigo_tag:
            preco_antigo_texto = preco_antigo_tag.text.replace("R$", "").strip().replace(".", "").replace(",", ".")
            try:
                preco_antigo = float(preco_antigo_texto)
            except:
                continue

            desconto = round((preco_antigo - preco_atual) / preco_antigo * 100, 1)
            if desconto >= 15:  # Só envia promoções reais acima de 15%
                produtos.append({
                    "nome": nome,
                    "preco_atual": f"R$ {preco_atual:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "preco_antigo": f"R$ {preco_antigo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    "desconto": f"{desconto:.0f}%",
                    "link": link,
                    "categoria": categoria
                })

    return produtos

# ---------------------------- ENVIO TELEGRAM ----------------------------

async def enviar_oferta(oferta):
    """Envia uma oferta formatada para o grupo do Telegram"""
    mensagem = (
        f"🔥 <b>{oferta['categoria'].upper()}</b> 🔥\n\n"
        f"🛒 <i>{oferta['nome']}</i>\n\n"
        f"💰 <b>{oferta['preco_atual']}</b>  (de <strike>{oferta['preco_antigo']}</strike>)\n"
        f"💥 Desconto: <b>{oferta['desconto']}</b>\n\n"
        f"👉 <a href=\"{oferta['link']}\">COMPRE AGORA NA AMAZON</a>"
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
        logger.error(f"Erro ao enviar mensagem: {e}")

# ---------------------------- CICLO PRINCIPAL ----------------------------

async def job_buscar_e_enviar():
    categorias = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
    logger.info("🔄 Iniciando ciclo de busca real de ofertas...")
    for categoria in categorias:
        produtos = extrair_produtos(categoria)
        if not produtos:
            logger.warning(f"⚠️ Nenhuma promoção encontrada em {categoria}")
            continue

        logger.info(f"✅ {len(produtos)} ofertas válidas encontradas em {categoria}")
        for oferta in produtos:
            await enviar_oferta(oferta)
            await asyncio.sleep(10)

    logger.info("✅ Ciclo concluído!")

# ---------------------------- MAIN ----------------------------

async def main():
    logger.info("🤖 Iniciando bot Amazon Affiliate (promoções reais, ScrapeOps ativo)...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=5)
    await job_buscar_e_enviar()  # primeira execução imediata
    scheduler.start()
    try:
        await asyncio.Future()  # mantém o loop ativo
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
