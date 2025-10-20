import logging
import os
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from playwright.async_api import async_playwright

# === CONFIGURAÇÕES ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")

if not BOT_TOKEN:
    raise ValueError("❌ A variável BOT_TOKEN não está definida!")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

scheduler = AsyncIOScheduler()


# === FUNÇÃO: BUSCAR PROMOÇÕES NA AMAZON ===
async def fetch_amazon_promotions():
    """Abre a Amazon GoldBox e coleta as promoções visíveis"""
    url = "https://www.amazon.com.br/gp/goldbox"
    logging.info("🔍 Buscando promoções reais da Amazon...")
    produtos = []

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)
            await page.wait_for_selector("div.a-section", timeout=15000)

            itens = await page.query_selector_all("div[data-asin][data-component-type='s-search-result']")

            for item in itens[:5]:
                titulo = await item.query_selector_eval("h2 a span", "el => el.innerText") if await item.query_selector("h2 a span") else None
                link = await item.query_selector_eval("h2 a", "el => el.href") if await item.query_selector("h2 a") else None
                preco = await item.query_selector_eval("span.a-price-whole", "el => el.innerText") if await item.query_selector("span.a-price-whole") else "Preço indisponível"
                imagem = await item.query_selector_eval("img.s-image", "el => el.src") if await item.query_selector("img.s-image") else None

                if titulo and link:
                    produtos.append({
                        "titulo": titulo.strip(),
                        "link": link.strip(),
                        "preco": preco.strip(),
                        "imagem": imagem
                    })

            await browser.close()

    except Exception as e:
        logging.error(f"❌ Erro ao buscar promoções: {e}")

    return produtos


# === TAREFA AGENDADA ===
async def postar_ofertas(context: ContextTypes.DEFAULT_TYPE):
    """Posta automaticamente as ofertas no grupo"""
    produtos = await fetch_amazon_promotions()

    if not produtos:
        logging.info("⚠️ Nenhuma promoção encontrada no momento.")
        return

    for p in produtos:
        msg = (
            f"🔥 *{p['titulo']}*\n"
            f"💰 Preço: R$ {p['preco']}\n"
            f"🔗 [Ver na Amazon]({p['link']})"
        )

        if p["imagem"]:
            await context.bot.send_photo(chat_id=GROUP_ID, photo=p["imagem"], caption=msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown")

    logging.info(f"✅ {len(produtos)} promoções postadas às {datetime.now()}")


# === COMANDOS DO BOT ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Use /start_posting para iniciar as postagens automáticas de ofertas da Amazon.")

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Comandos disponíveis:*\n"
        "/start - Inicia o bot\n"
        "/ajuda - Mostra esta mensagem\n"
        "/start_posting - Começa a postar ofertas automáticas\n",
        parse_mode="Markdown"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Você disse: {update.message.text}")


# === INICIAR POSTAGENS ===
async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ativa a tarefa de postagem automática"""
    if not GROUP_ID:
        await update.message.reply_text("⚠️ Defina o GROUP_ID nas variáveis de ambiente!")
        return

    if not scheduler.running:
        scheduler.start()

    for job in scheduler.get_jobs():
        job.remove()

    scheduler.add_job(
        postar_ofertas,
        "interval",
        minutes=1,
        args=[context],
        id="job_postar_ofertas"
    )

    await update.message.reply_text("✅ Postagens automáticas iniciadas! A cada 1 minuto serão verificadas novas promoções.")


# === FUNÇÃO PRINCIPAL ===
def main():
    logging.info("🚀 Iniciando bot...")

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("start_posting", start_posting))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logging.info("✅ Bot iniciado e aguardando mensagens...")
    app.run_polling(close_loop=False)


# === EXECUÇÃO ===
if __name__ == "__main__":
    main()
