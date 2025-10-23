import os
import asyncio
import logging
import random
import nest_asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import Application, CommandHandler
from shopee_api import buscar_produto_shopee as buscar_shopee
from mercadolivre_api import buscar_produto_mercadolivre as buscar_mercadolivre

# ===================== CONFIGURAÇÕES =====================
load_dotenv()
nest_asyncio.apply()

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID", "-1003140787649")  # Grupo padrão

INTERVALO = 120  # tempo entre postagens (em segundos)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Alternância entre lojas
LOJAS = ["shopee", "mercadolivre"]
ultima_loja = None

scheduler = AsyncIOScheduler()


# ===================== FUNÇÃO DE POSTAGEM =====================
async def postar_oferta(bot: Bot):
    global ultima_loja

    loja_atual = "mercadolivre" if ultima_loja == "shopee" else "shopee"
    ultima_loja = loja_atual
    logger.info(f"🛍️ Buscando oferta da loja: {loja_atual}")

    oferta = None
    if loja_atual == "shopee":
        oferta = await buscar_shopee()
    else:
        oferta = await buscar_mercadolivre()

    if not oferta:
        logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
        return

    try:
        msg = (
            f"🔥 *Oferta {oferta['loja']}!*\n\n"
            f"*{oferta['titulo']}*\n"
            f"💰 {oferta['preco']}\n"
            f"📦 Categoria: {oferta['categoria']}\n\n"
            f"👉 [Aproveite aqui]({oferta['link']})"
        )
        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=oferta["imagem"],
            caption=msg,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Oferta enviada: {oferta['titulo']}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")


# ===================== COMANDOS DO BOT =====================
async def start(update, context):
    await update.message.reply_text("🤖 Bot ativo! Use /start_posting para iniciar as postagens automáticas.")


async def start_posting(update, context):
    if not scheduler.running:
        scheduler.start()

    scheduler.add_job(
        postar_oferta,
        "interval",
        seconds=INTERVALO,
        args=[context.bot],
        id="postar_oferta",
        replace_existing=True,
    )

    await update.message.reply_text("🕒 Postagens automáticas iniciadas!")
    logger.info("🕒 Ciclo automático iniciado via /start_posting")


# ===================== EXECUÇÃO PRINCIPAL =====================
async def main():
    application = Application.builder().token(TOKEN).build()

    # 🔹 LIMPA instâncias antigas e pendências antes de iniciar polling
    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("🧹 Webhook limpo e atualizações antigas removidas.")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))

    logger.info("🚀 Bot iniciado e escutando comandos.")
    await application.run_polling(close_loop=False)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
