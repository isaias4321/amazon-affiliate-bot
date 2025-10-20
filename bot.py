import os
import re
import logging
import asyncio
from typing import List, Dict

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, filters
)
from telegram.error import ChatMigrated

from playwright.async_api import async_playwright
import aiohttp

# ====================== CONFIG ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DEFAULT_CHAT_ID = os.getenv("CHAT_ID", "").strip()  # opcional
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "").strip()  # ex: seuid-20
SHORTENER_API = os.getenv("SHORTENER_API", "https://tinyurl.com/api-create.php?url=")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Categorias permitidas (conforme solicitado)
CATEGORIES_ENABLED = {
    "eletronicos": True,
    "eletrodomesticos": True,
    "ferramentas": True,
    "pecas_pc": True,
    "notebooks": True,
}

# Palavras-chave para filtrar por título (minúsculas)
KEYWORDS = {
    "eletronicos": [
        "eletrôn", "smart", "tv", "monitor", "soundbar", "fone", "headset",
        "bluetooth", "usb", "hdmi", "tablet", "smartwatch", "echo", "alexa"
    ],
    "eletrodomesticos": [
        "geladeira", "refrigerador", "freezer", "micro-ondas", "microondas",
        "lava", "secadora", "liquidificador", "aspirador", "ar-condicionado",
        "air fryer", "cafeteira", "batedeira", "purificador", "climatizador"
    ],
    "ferramentas": [
        "parafusadeira", "furadeira", "serra", "esmerilhadeira", "multímetro",
        "nivela", "compressor", "chave", "martelete", "kit ferramenta",
        "parafusos", "soprador", "tupia"
    ],
    "pecas_pc": [
        "ssd", "hdd", "hard disk", "placa-mãe", "placa mae", "motherboard",
        "processador", "ryzen", "intel", "geforce", "rtx", "radeon",
        "memória", "memoria", "ram", "gabinete", "fonte", "psu",
        "cooler", "water cooler", "nvme", "m.2", "m2", "gpu", "vga"
    ],
    "notebooks": [
        "notebook", "laptop", "macbook", "chromebook", "ultrabook", "ideapad",
    ],
}

# Monta uma regex por categoria pra ficar rápido
CATEGORY_REGEX = {
    cat: re.compile("|".join(re.escape(k) for k in kws), flags=re.I)
    for cat, kws in KEYWORDS.items()
}


# ====================== HELPERS ======================
async def liberar_antigo_bot() -> None:
    """Evita conflito 409 (outro getUpdates ativo)."""
    if not BOT_TOKEN:
        return
    try:
        async with aiohttp.ClientSession() as session:
            await session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
            logging.info("🧹 Webhook antigo removido (polling livre).")
    except Exception as e:
        logging.warning(f"Falha ao limpar webhook: {e}")


def titulo_bate_categoria(titulo: str) -> bool:
    """Retorna True se o título bater em alguma das categorias habilitadas."""
    t = titulo.lower()
    for cat, enabled in CATEGORIES_ENABLED.items():
        if not enabled:
            continue
        if CATEGORY_REGEX[cat].search(t):
            return True
    return False


def anexar_afiliado(url: str) -> str:
    """Acrescenta tag de afiliado, respeitando querystring existente."""
    if not AFFILIATE_TAG:
        return url
    sep = "&" if "?" in url else "?"
    # Evita duplicar tag
    if "tag=" not in url:
        url = f"{url}{sep}tag={AFFILIATE_TAG}"
    return url


async def encurtar_link(url: str) -> str:
    """Encurta link via API simples (TinyURL por padrão)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SHORTENER_API}{url}") as resp:
                if resp.status == 200:
                    txt = await resp.text()
                    if txt.startswith("http"):
                        return txt
    except Exception as e:
        logging.warning(f"Falha ao encurtar link: {e}")
    return url


async def buscar_ofertas_filtradas(limit: int = 8) -> List[Dict]:
    """Scrape da Amazon BR (Goldbox), filtra por categorias e retorna ofertas."""
    url_goldbox = "https://www.amazon.com.br/gp/goldbox"
    resultados: List[Dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url_goldbox, timeout=60000, wait_until="domcontentloaded")

        # Amazon muda CSS sempre; esses seletores abrangem os cartões de oferta
        await page.wait_for_selector("div.DealCard, div[data-testid='deal-card']", timeout=20000)

        cards = await page.query_selector_all("div.DealCard, div[data-testid='deal-card']")
        for card in cards:
            # Título
            el_title = await card.query_selector("span.a-text-normal, span[data-testid='deal-title']")
            # Preço (pode não existir)
            el_price = await card.query_selector("span.a-price-whole, span[data-a-color='price'] span.a-offscreen")
            # Link
            el_link = await card.query_selector("a.a-link-normal, a[data-testid='deal-title-link']")

            if not el_title or not el_link:
                continue

            title = (await el_title.inner_text()).strip()
            if not titulo_bate_categoria(title):
                continue

            price = (await el_price.inner_text()).strip() if el_price else "Preço indisponível"
            href = await el_link.get_attribute("href") or ""
            if not href:
                continue

            if not href.startswith("http"):
                href = "https://www.amazon.com.br" + href

            href = anexar_afiliado(href)
            href = await encurtar_link(href)

            resultados.append({
                "titulo": title if len(title) <= 100 else title[:97] + "...",
                "preco": price,
                "link": href
            })

            if len(resultados) >= limit:
                break

        await browser.close()

    return resultados


# ====================== JOB ======================
async def postar_ofertas_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    ofertas = await buscar_ofertas_filtradas(limit=6)

    if not ofertas:
        logging.info("Nenhuma oferta (após filtro de categorias).")
        return

    for o in ofertas:
        msg = (
            f"📦 *{o['titulo']}*\n"
            f"💰 {o['preco']}\n"
            f"🔗 [Ver oferta]({o['link']})\n"
            f"_Categorias: eletrônicos / eletrodomésticos / ferramentas / peças de PC / notebooks_"
        )
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            await asyncio.sleep(3)
        except ChatMigrated as e:
            novo_id = e.new_chat_id
            os.environ["CHAT_ID"] = str(novo_id)
            await context.bot.send_message(chat_id=novo_id, text="✅ Grupo virou supergrupo. Continuo por aqui.")
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem: {e}")


# ====================== COMMANDS ======================
def job_name(chat_id: int | str) -> str:
    return f"posting-{chat_id}"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Inspira+ Ofertas* online!\n"
        "Vou postar promoções **reais** da Amazon BR, filtradas para:\n"
        "• Eletrônicos\n• Eletrodomésticos\n• Ferramentas\n• Peças de computador\n• Notebooks\n\n"
        "Comandos:\n"
        "• /start_posting – iniciar postagens automáticas\n"
        "• /stop_posting – parar postagens\n",
        parse_mode="Markdown"
    )


async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.job_queue.get_jobs_by_name(job_name(chat_id)):
        await update.message.reply_text("✔️ Já estou postando aqui.")
        return

    # a cada 2 minutos
    context.job_queue.run_repeating(
        postar_ofertas_job, interval=120, first=2, chat_id=chat_id, name=job_name(chat_id)
    )
    await update.message.reply_text("🚀 Postagens automáticas iniciadas (a cada 2 minutos).")


async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(job_name(chat_id))
    if not jobs:
        await update.message.reply_text("ℹ️ Não há postagens ativas neste chat.")
        return
    for j in jobs:
        j.schedule_removal()
    await update.message.reply_text("🛑 Postagens automáticas paradas.")


# ====================== BOOT ======================
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("Defina BOT_TOKEN nas variáveis de ambiente.")

    await liberar_antigo_bot()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))

    # se quiser já iniciar em um chat fixo (ex.: grupo)
    if DEFAULT_CHAT_ID:
        app.job_queue.run_repeating(
            postar_ofertas_job, interval=120, first=5, chat_id=int(DEFAULT_CHAT_ID), name=job_name(DEFAULT_CHAT_ID)
        )

    # modo compatível com Render/Docker (sem fechar o loop)
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logging.info("✅ Bot iniciado e aguardando mensagens...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
