import os
import asyncio
import logging
import random
import aiohttp
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# ---------------- CONFIG ----------------
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SCRAPEOPS_API_KEY = os.getenv("SCRAPEOPS_API_KEY")
INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", "30"))
MIN_DISCOUNT_PERCENT = int(os.getenv("MIN_DISCOUNT_PERCENT", "10"))  # só envia >= X% (0 desativa)
DEBUG_SAVE_HTML = True  # salva HTML quando parsing falhar

SCRAPEOPS_PROXY = "https://proxy.scrapeops.io/v1/"

CATEGORIES = ["notebook", "celular", "processador", "ferramenta", "eletrodoméstico"]
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121 Safari/537.36",
]

# ---------------- LOG ----------------
os.makedirs("logs/html_debug", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if not all([TELEGRAM_TOKEN, GROUP_CHAT_ID, AFFILIATE_TAG, SCRAPEOPS_API_KEY]):
    logger.error("❌ Variáveis faltando. Defina TELEGRAM_TOKEN, GROUP_CHAT_ID, AFFILIATE_TAG, SCRAPEOPS_API_KEY.")
    raise SystemExit("Configuração incompleta")

bot = Bot(token=TELEGRAM_TOKEN)
executor = ThreadPoolExecutor(max_workers=3)

# ---------------- HELPERS ----------------

def safe_float_from_price(s: str):
    if not s:
        return None
    try:
        tmp = s.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
        return float(tmp)
    except Exception:
        try:
            nums = ''.join(ch for ch in s if ch.isdigit() or ch in ",.")
            return float(nums.replace(".", "").replace(",", "."))
        except Exception:
            return None

def add_affiliate_tag(url: str) -> str:
    if not url:
        return url
    if "tag=" in url:
        return url
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}tag={AFFILIATE_TAG}"

def save_debug_html(term: str, html: str, source: str):
    """Salva HTML para análise caso parsing falhe."""
    if not DEBUG_SAVE_HTML or not html:
        return
    filename = f"logs/html_debug/{term}_{source}_{datetime.now().strftime('%H-%M-%S')}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"💾 HTML salvo para debug: {filename}")

def parse_products_from_html(html: str, categoria: str, limit: int = 5):
    soup = BeautifulSoup(html, "html.parser")
    resultados = soup.select("div[data-component-type='s-search-result']")
    produtos = []

    for item in resultados[:limit]:
        title_el = item.select_one("h2 a span")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)

        link_el = item.select_one("h2 a")
        if not link_el or not link_el.get("href"):
            continue
        link = "https://www.amazon.com.br" + link_el["href"].split("?")[0]

        price_whole = item.select_one(".a-price .a-price-whole")
        price_fraction = item.select_one(".a-price .a-price-fraction")
        price_offscreen = item.select_one(".a-price .a-offscreen")
        if price_offscreen:
            price_text = price_offscreen.get_text(strip=True)
        elif price_whole:
            frac = price_fraction.get_text(strip=True) if price_fraction else "00"
            price_text = f"R$ {price_whole.get_text(strip=True)},{frac}"
        else:
            price_text = None

        old_price_el = item.select_one(".a-text-price .a-offscreen")
        old_price_text = old_price_el.get_text(strip=True) if old_price_el else None

        preco_novo = safe_float_from_price(price_text)
        preco_velho = safe_float_from_price(old_price_text)
        desconto_pct = None
        if preco_novo and preco_velho and preco_velho > 0:
            try:
                desconto_pct = int(round((1 - preco_novo / preco_velho) * 100))
            except Exception:
                desconto_pct = None

        produtos.append({
            "titulo": title,
            "preco_atual_str": price_text,
            "preco_antigo_str": old_price_text,
            "preco_atual": preco_novo,
            "preco_antigo": preco_velho,
            "desconto_pct": desconto_pct,
            "link": add_affiliate_tag(link),
            "categoria": categoria
        })
    return produtos

# ---------------- FETCHERS ----------------

async def fetch_via_scrapeops(term: str):
    params = {
        "api_key": SCRAPEOPS_API_KEY,
        "url": f"https://www.amazon.com.br/s?k={term}",
        "country": "br",
        "render_js": "false"
    }
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    async with aiohttp.ClientSession() as session:
        for attempt in range(1, 4):
            try:
                async with session.get(SCRAPEOPS_PROXY, params=params, headers=headers, timeout=30) as resp:
                    text = await resp.text()
                    logger.info(f"ScrapeOps {resp.status} para '{term}' (tentativa {attempt})")
                    if resp.status == 200 and len(text) > 1000:
                        products = parse_products_from_html(text, term)
                        if products:
                            return products
                        else:
                            save_debug_html(term, text, "scrapeops")
                            logger.warning(f"⚠️ Nenhum produto parseado via ScrapeOps para '{term}'")
            except Exception as e:
                logger.warning(f"Erro ScrapeOps '{term}': {e}")
    return None

def fetch_direct_requests(term: str):
    url = f"https://www.amazon.com.br/s?k={term}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    }
    for attempt in range(1, 3):
        try:
            resp = requests.get(url, headers=headers, timeout=25)
            logger.info(f"Fetch direto {resp.status_code} para '{term}' (tentativa {attempt})")
            if resp.status_code == 200 and len(resp.text) > 1000:
                products = parse_products_from_html(resp.text, term)
                if products:
                    return products
                else:
                    save_debug_html(term, resp.text, "direct")
                    logger.warning(f"Nenhum produto parseado direto '{term}'")
        except Exception as e:
            logger.warning(f"Erro fetch direto '{term}': {e}")
    return None

# ---------------- PIPELINE ----------------

async def buscar_produtos_hibrido(term: str):
    produtos = await fetch_via_scrapeops(term)
    if produtos:
        logger.info(f"✅ {len(produtos)} produtos via ScrapeOps '{term}'")
        return produtos
    loop = asyncio.get_running_loop()
    produtos = await loop.run_in_executor(executor, fetch_direct_requests, term)
    if produtos:
        logger.info(f"✅ {len(produtos)} produtos via fetch direto '{term}'")
        return produtos
    logger.error(f"❌ Falha total para '{term}'")
    return []

def produto_valido(produto: dict) -> bool:
    if MIN_DISCOUNT_PERCENT <= 0:
        return True
    d = produto.get("desconto_pct")
    return d is not None and d >= MIN_DISCOUNT_PERCENT

async def enviar_telegram(produto: dict):
    texto = (
        f"🔥 <b>OFERTA AMAZON ({produto.get('categoria','')})</b> 🔥\n\n"
        f"🛒 <i>{produto.get('titulo')}</i>\n\n"
    )
    if produto.get("preco_antigo_str"):
        texto += f"🏷️ De: <strike>{produto['preco_antigo_str']}</strike>\n"
    texto += f"💰 <b>{produto['preco_atual_str']}</b>\n"
    if produto.get("desconto_pct") is not None:
        texto += f"💥 Desconto: {produto['desconto_pct']}%\n"
    texto += f"\n➡️ <a href=\"{produto['link']}\">COMPRAR NA AMAZON</a>"

    try:
        await bot.send_message(GROUP_CHAT_ID, texto, parse_mode=ParseMode.HTML, disable_web_page_preview=False)
        logger.info(f"📤 Enviado: {produto['titulo'][:60]}...")
    except Exception as e:
        logger.error(f"Erro ao enviar Telegram: {e}")

# ---------------- JOB ----------------

async def job_buscar_e_enviar():
    logger.info("🔄 Iniciando ciclo de busca...")
    for categoria in CATEGORIES:
        produtos = await buscar_produtos_hibrido(categoria)
        if not produtos:
            continue
        enviados = 0
        for p in produtos:
            if not produto_valido(p):
                continue
            await enviar_telegram(p)
            enviados += 1
            await asyncio.sleep(3)
            if enviados >= 1:
                break
    logger.info("✅ Ciclo concluído!")

# ---------------- MAIN ----------------

async def main():
    logger.info("🤖 Iniciando bot híbrido com debug ativo...")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_buscar_e_enviar, "interval", minutes=INTERVAL_MIN)
    scheduler.start()
    await job_buscar_e_enviar()
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
