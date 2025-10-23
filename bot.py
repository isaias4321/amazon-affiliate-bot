import os
import random
import asyncio
import logging
import nest_asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Importações das APIs
from shopee_api import buscar_produto_shopee as buscar_shopee
from mercadolivre_api import buscar_produto_mercadolivre as buscar_mercadolivre

# --- CONFIGURAÇÃO ---
load_dotenv()
nest_asyncio.apply()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# Configuração do logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Alternância automática Shopee ↔ Mercado Livre
fonte_atual = "shopee"
scheduler = AsyncIOScheduler()


# --- FUNÇÕES DE OFERTAS ---
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    """Posta ofertas alternando entre Shopee e Mercado Livre"""
    global fonte_atual
    try:
        if fonte_atual == "shopee":
            produto = await buscar_shopee()
            fonte_atual = "mercadolivre"
        else:
            produto = await buscar_mercadolivre()
            fonte_atual = "shopee"

        if not produto:
            logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
            return

        mensagem = (
            f"🔥 *{produto['titulo']}*\n"
            f"💰 *Preço:* {produto['preco']}\n"
            f"🛒 *Loja:* {produto['loja']}\n"
            f"📦 *Categoria:* {produto.get('categoria', 'N/A')}\n"
            f"👉 [Compre agora]({produto['link']})"
        )

        await context.bot.send_photo(
            chat_id=CHAT_ID,
            photo=produto["imagem"],
            caption=mensagem,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Oferta enviada ({produto['loja']})")

    except Exception as e:
        logger.error(f"❌ Erro ao postar oferta: {e}")


# --- COMANDOS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Olá! Eu sou o bot de ofertas automáticas!\n"
        "Use /start_posting para começar a postar ofertas."
    )


async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia o agendamento automático"""
    job_existente = scheduler.get_job("postar_oferta")
    if job_existente:
        await update.message.reply_text("⚙️ O bot já está postando automaticamente!")
        return

    scheduler.add_job(postar_oferta, "interval", minutes=2, args=[context], id="postar_oferta")
    scheduler.start()

    await update.message.reply_text("🕒 Ciclo automático iniciado!")


async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Para o ciclo automático"""
    job = scheduler.get_job("postar_oferta")
    if job:
        job.remove()
        await update.message.reply_text("⏹️ Postagem automática parada.")
    else:
        await update.message.reply_text("❌ Nenhum ciclo ativo encontrado.")


# --- FUNÇÃO PRINCIPAL ---
async def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Limpar Webhook e updates antigos
    await application.bot.delete_webhook()
    await application.bot.get_updates(offset=-1)
    logger.info("🧹 Webhook limpo e atualizações antigas removidas.")

    # Registrar comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))
    application.add_handler(CommandHandler("stop_posting", stop_posting))

    logger.info("🚀 Bot iniciado e escutando comandos.")
    await application.run_polling(close_loop=False)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
