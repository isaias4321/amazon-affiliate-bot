import os
import re
import logging
import asyncio
from typing import List, Dict

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)
from telegram.error import ChatMigrated

from playwright.async_api import async_playwright
import aiohttp

# =============== CONFIG ===============
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
DEFAULT_CHAT_ID = os.getenv("CHAT_ID", "").strip()
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "").strip()
SHORTENER_API = os.getenv("SHORTENER_API", "https://tinyurl.com/api-create.php?url=")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Categorias permitidas
CATEGORIES_ENABLED = {
    "eletronicos": True,
    "eletrodomesticos": True,
    "ferramentas": True,
    "pecas_pc": True,
    "notebooks": True,
}

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
        "ssd", "hdd", "placa-mãe", "placa mae", "motherboard",
        "processador", "ryzen", "intel", "geforce", "rtx", "radeon",
        "memória", "ram", "gabinete", "fonte", "cooler", "water cooler",
        "nvme", "m.2", "m2", "gpu", "vga"
    ],
    "notebooks": [
        "notebook", "laptop", "macbook", "chromebook", "ultrabook", "ideapad",
    ],
}

CATEGORY_REGEX = {
    cat: re.compile("|".join(re.escape(k) for k in kws), flags=re.I)
    for cat, kws in KEYWORDS.items()
}

# =============== FUNÇÕES ===============

async def liberar_antigo_bot():
    """Evita erro de polling duplicado (409 Conflict)."""
    try:
        async with aiohttp.ClientSession() as session:
            await session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook")
            logging.info("🧹 Webhook antigo removido (polling livre).")
    except Exception as e:
        logging.warning(f"Falha ao limpar webhook: {e}")

def titulo_bate_categoria(titulo: str) -> bool:
    """Verifica se o produto pertence a uma categoria habilitada."""
    t = titulo.lower()
    for cat, ativo in CATEGORIES_ENABLED.items():
        if ativo and CATEGORY_REGEX[cat].search(t):
            return True
    return False

def anexar_afiliado(url: str) -> str:
    """Adiciona tag de afiliado se existir."""
    if not AFFILIATE_TAG:
        return url
    sep = "&" if "?" in url else "?"
    if "tag=" not in url:
        url += f"{sep}tag={AFFILIATE_TAG}"
    return url

async def encurtar_link(url: str) -> str:
    """Usa TinyURL para encurtar links."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SHORTENER_API}{url}") as resp:
                if resp.status == 200:
                    short = await resp.text()
                    if short.startswith("http"):
                        return short
    except Exception:
        pass
    return url

async def buscar_ofertas_filtradas(limit: int = 8) -> List[Dict]:
    """Busca promoções reais da Amazon BR."""
    url_goldbox = "https://www.amazon.com.br/gp/goldbox"
    resultados: List[Dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url_goldbox, timeout=60000)

        # Timeout aumentado + seletor alternativo
        await page.wait_for_selector(
            "div.DealCard, div[data-testid='deal-card'], div.a-section.a-spacing-none.tall-cell-view",
            timeout=60000
        )

        cards = await page.query_selector_all(
            "div.DealCard, div[data-testid='deal-card'], div.a-section.a-spacing-none.tall-cell-view"
        )

        for card in cards:
            title_el = await card.query_selector("span.a-text-normal, span[data-testid='deal-title']")
            price_el = await card.query_selector("span.a-price-whole, span[data-a-color='price'] span.a-offscreen")
            link_el = await card.query_selector("a.a-link-normal, a[data-testid='deal-title-link']")

            if not title_el or not link_el:
                continue

            title = (await title_el.inner_text()).strip()
            if not titulo_bate_categoria(title):
                continue

            price = (await price_el.inner_text()).strip() if price_el else "Preço indisponível"
            href = await link_el.get_attribute("href") or ""
            if not href.startswith("http"):
                href = f"https://www.amazon.com.br{href}"

            href = anexar_afiliado(href)
            href = await encurtar_link(href)

            resultados.append({
                "titulo": title[:100] + "..." if len(title) > 100 else title,
                "preco": price,
                "link": href
            })

            if len(resultados) >= limit:
                break

        await browser.close()

    return resultados

# =============== JOB ===============

async def postar_ofertas_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    ofertas = await buscar_ofertas_filtradas(limit=6)

    if not ofertas:
        logging.info("Nenhuma oferta encontrada após o filtro.")
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
            await context.bot.send_message(chat_id=novo_id, text="✅ Grupo atualizado! Continuando postagens aqui.")
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem: {e}")

# =============== COMANDOS ===============

def job_name(chat_id: int | str) -> str:
    return f"posting-{chat_id}"

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Inspira+ Ofertas*\n"
        "Eu trago promoções reais da Amazon BR nas categorias:\n"
        "📱 Eletrônicos\n🏠 Eletrodomésticos\n🧰 Ferramentas\n💻 Peças de PC / Notebooks\n\n"
        "Comandos:\n/start_posting – iniciar postagens\n/stop_posting – parar postagens",
        parse_mode="Markdown"
    )

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.job_queue.get_jobs_by_name(job_name(chat_id)):
        await update.message.reply_text("✅ Já estou postando aqui!")
        return
    context.job_queue.run_repeating(postar_ofertas_job, interval=120, first=2, chat_id=chat_id, name=job_name(chat_id))
    await update.message.reply_text("🚀 Comecei a postar ofertas a cada 2 minutos!")

async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(job_name(chat_id))
    if not jobs:
        await update.message.reply_text("ℹ️ Nenhuma postagem ativa aqui.")
        return
    for j in jobs:
        j.schedule_removal()
    await update.message.reply_text("🛑 Postagens automáticas paradas.")

# =============== MAIN ===============

async def main():
    await liberar_antigo_bot()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("start_posting", cmd_start_posting))
    app.add_handler(CommandHandler("stop_posting", cmd_stop_posting))

    if DEFAULT_CHAT_ID:
        app.job_queue.run_repeating(postar_ofertas_job, interval=120, first=5, chat_id=int(DEFAULT_CHAT_ID))

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logging.info("✅ Bot iniciado e aguardando mensagens...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
