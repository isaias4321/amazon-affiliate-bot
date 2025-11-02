# bot.py
import os
import random
import logging
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from colorama import Fore, Style, init
import nest_asyncio

# =====================================
# Inicialização
# =====================================
init(autoreset=True)
nest_asyncio.apply()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ofertas-bot")

# =====================================
# Variáveis de Ambiente
# =====================================
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Mercado Livre
ML_ACCESS_TOKEN = os.getenv("ML_ACCESS_TOKEN")  # opcional p/ search pública
MELI_MATT_TOOL = os.getenv("MELI_MATT_TOOL")
MELI_MATT_WORD = os.getenv("MELI_MATT_WORD")

# Shopee (Affiliate)
SHOPEE_APP_ID = os.getenv("SHOPEE_APP_ID")
SHOPEE_APP_SECRET = os.getenv("SHOPEE_APP_SECRET")  # conforme sua conta afiliada
SHOPEE_AFIL = os.getenv("SHOPEE_AFIL")  # shortener base (opcional)

# Categorias desejadas
CATEGORIAS = [
    "eletrodomésticos",
    "peças de computador",
    "notebooks",
    "celulares",
    "ferramentas",
]

# Evitar duplicados recentes
ULTIMOS_TITULOS = set()
MAX_CACHE_TITULOS = 100

# Alternância de marketplace
STATE = {"proximo": "mercadolivre"}  # alterna entre 'mercadolivre' e 'shopee'

# =====================================
# Utilitários
# =====================================
def brl(v: Any) -> str:
    try:
        n = float(v)
    except Exception:
        return str(v)
    # formatação simples para BRL (sem locale)
    inteiro, cent = f"{n:.2f}".split(".")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    return f"R$ {inteiro},{cent}"

def clear_duplicates_cache():
    """Mantém o set de títulos num tamanho razoável."""
    if len(ULTIMOS_TITULOS) > MAX_CACHE_TITULOS:
        ULTIMOS_TITULOS.clear()

def make_aff_link_meli(permalink: str) -> str:
    # mantem seus parâmetros de afiliação
    tool = MELI_MATT_TOOL or ""
    word = MELI_MATT_WORD or ""
    sep = "&" if "?" in permalink else "?"
    return f"{permalink}{sep}matt_tool={tool}&matt_word={word}"

def make_aff_link_shopee(base_url: str) -> str:
    # se você tiver um shortener de afiliação, pode combiná-lo aqui.
    # caso já venha com link final, apenas retorna.
    return base_url

def build_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(text="Ver oferta 🔗", url=url)]]
    )

async def send_offer(app: Application, o: Dict[str, Any]):
    """Envia uma oferta em formato caprichado com botão."""
    titulo = o.get("titulo", "Oferta")
    preco = o.get("preco", "")
    link = o.get("link", "")

    # Mensagem em HTML (evita precisar escapar Markdown)
    partes = []
    partes.append(f"📦 <b>{titulo}</b>")
    if preco:
        partes.append(f"💰 <b>{brl(preco)}</b>")
    texto = "\n".join(partes)

    try:
        await app.bot.send_message(
            chat_id=CHAT_ID,
            text=texto,
            parse_mode="HTML",
            reply_markup=build_keyboard(link) if link else None,
            disable_web_page_preview=False,
        )
        logger.info(Fore.GREEN + f"Enviado: {titulo}")
    except Exception as e:
        logger.error(Fore.RED + f"Erro ao enviar mensagem: {e}")

# =====================================
# Mercado Livre
# =====================================
async def buscar_ofertas_mercadolivre() -> List[Dict[str, Any]]:
    """Busca 3 produtos do Mercado Livre via endpoint público de busca."""
    termo = random.choice(CATEGORIAS)
    url = "https://api.mercadolibre.com/sites/MLB/search"
    params = {"q": termo, "limit": 3}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; OfertasBot/1.0)"}
    # Opcional: incluir Authorization se desejar (não é necessário p/ search pública)
    if ML_ACCESS_TOKEN:
        headers["Authorization"] = f"Bearer {ML_ACCESS_TOKEN}"

    logger.info(Fore.BLUE + f"[ML] Buscando por: {termo}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=20) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    logger.error(Fore.RED + f"[ML] HTTP {resp.status} - {txt[:180]}")
                    return []
                data = await resp.json()
    except Exception as e:
        logger.error(Fore.RED + f"[ML] Erro de requisição: {e}")
        return []

    results = data.get("results", [])[:3]
    ofertas = []
    for r in results:
        titulo = r.get("title") or ""
        if not titulo or titulo in ULTIMOS_TITULOS:
            continue
        preco = r.get("price")
        link = r.get("permalink") or ""
        if link:
            link = make_aff_link_meli(link)
        ofertas.append({"titulo": titulo, "preco": preco, "link": link})

    return ofertas

# =====================================
# Shopee (Affiliate)
# =====================================
async def buscar_ofertas_shopee() -> List[Dict[str, Any]]:
    """
    Busca 3 ofertas pela API de Afiliados v1 (formato parecido com o que você já usava).
    Ajuste este endpoint/headers se sua conta exigir OAuth/sign HMAC diferente.
    """
    if not SHOPEE_APP_ID or not SHOPEE_APP_SECRET:
        logger.error(Fore.RED + "❌ Shopee credenciais ausentes.")
        return []

    termo = random.choice(CATEGORIAS)
    ts = int(datetime.now(timezone.utc).timestamp())

    url = "https://open-api.affiliate.shopee.com.br/api/v1/offer/product_offer"
    headers = {
        "Content-Type": "application/json",
        # Em algumas integrações é realmente 'Bearer {token_acesso_afiliado}'
        # Se a sua exigir assinatura HMAC ou outro header, adapte aqui:
        "Authorization": f"Bearer {SHOPEE_APP_SECRET}",
        "X-Appid": str(SHOPEE_APP_ID),
    }
    payload = {
        "page_size": 3,
        "page": 1,
        "keyword": termo,
        "timestamp": ts,
    }

    logger.info(Fore.BLUE + f"[Shopee] Buscando por: {termo}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=25) as resp:
                data = await resp.json(content_type=None)
                if resp.status != 200:
                    logger.error(Fore.RED + f"[Shopee] HTTP {resp.status} - {str(data)[:200]}")
                    return []
    except Exception as e:
        logger.error(Fore.RED + f"[Shopee] Erro de requisição: {e}")
        return []

    items = (data or {}).get("data", {}).get("list", []) or []
    ofertas = []
    for item in items:
        titulo = item.get("name")
        if not titulo or titulo in ULTIMOS_TITULOS:
            continue

        # Preço: algumas respostas usam centavos; outras, número direto
        preco = item.get("price") or item.get("min_price") or item.get("final_price")
        link = item.get("short_url") or item.get("offer_link") or item.get("target_url")
        if link:
            link = make_aff_link_shopee(link)

        ofertas.append({"titulo": titulo, "preco": preco, "link": link})

    return ofertas

# =====================================
# Postagem e Agendamento
# =====================================
async def postar_ofertas_alternado(app: Application):
    """
    A cada execução (1 min), alterna a origem: Mercado Livre -> Shopee -> ML -> ...
    """
    origem = STATE["proximo"]
    logger.info(Fore.CYAN + f"🔁 Rodada de ofertas de: {origem.upper()}")

    if origem == "mercadolivre":
        ofertas = await buscar_ofertas_mercadolivre()
        STATE["proximo"] = "shopee"
    else:
        ofertas = await buscar_ofertas_shopee()
        STATE["proximo"] = "mercadolivre"

    if not ofertas:
        logger.info(Fore.YELLOW + "⚠️ Nenhuma oferta encontrada nesta rodada.")
        return

    enviados = 0
    for o in ofertas:
        titulo = o.get("titulo")
        if titulo in ULTIMOS_TITULOS:
            continue
        await send_offer(app, o)
        ULTIMOS_TITULOS.add(titulo)
        enviados += 1

    clear_duplicates_cache()
    logger.info(Fore.GREEN + f"✅ Ofertas enviadas: {enviados}")

# =====================================
# Comandos do Bot
# =====================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "🤖 <b>Bot de Ofertas</b> ativo!\n"
        "Postagens automáticas a cada <b>1 minuto</b>, alternando entre <i>Mercado Livre</i> e <i>Shopee</i>.\n"
        "Categorias: eletrodomésticos, peças de computador, notebooks, celulares, ferramentas."
    )

# =====================================
# Inicialização
# =====================================
async def main():
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("TELEGRAM_TOKEN e/ou CHAT_ID ausentes.")

    logger.info(Fore.CYAN + "🚀 Iniciando bot de ofertas...")

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Inicia polling e agendador
    scheduler = AsyncIOScheduler()
    loop = asyncio.get_running_loop()

    async def job_wrapper():
        await postar_ofertas_alternado(app)

    def schedule_job():
        # Executa coroutine no loop do telegram-application
        asyncio.run_coroutine_threadsafe(job_wrapper(), loop)

    # Executa a cada 1 minuto
    scheduler.add_job(schedule_job, "interval", minutes=1, id="postagens_autom")
    scheduler.start()
    logger.info(Fore.GREEN + "🗓️ Agendador iniciado (intervalo: 1 minuto).")

    # Garante que não há webhooks ativos e inicia polling
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info(Fore.GREEN + "✅ Bot conectado. Iniciando polling...")
    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(Style.DIM + "Encerrado pelo usuário.")
