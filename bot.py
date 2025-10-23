import logging
import asyncio
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from shopee_api import buscar_produto_shopee as buscar_shopee
from mercadolivre_api import buscar_produto_ml as buscar_mercadolivre

# =============================
# CONFIGURAÇÕES DO BOT
# =============================
TOKEN = "SEU_TOKEN_DO_BOT_AQUI"  # Substitua pelo seu token do BotFather
CHAT_ID = "SEU_CHAT_ID_AQUI"      # Substitua pelo ID do chat do grupo/canal
INTERVALO_MINUTOS = 2             # Intervalo de postagens automáticas

# =============================
# LOGGING
# =============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================
# VARIÁVEIS DE CONTROLE
# =============================
scheduler = AsyncIOScheduler()
loja_atual = "Shopee"  # alterna Shopee ↔ Mercado Livre

# =============================
# FUNÇÕES PRINCIPAIS
# =============================
async def postar_oferta(context: ContextTypes.DEFAULT_TYPE):
    global loja_atual

    if loja_atual == "Shopee":
        oferta = await buscar_shopee()
        loja_atual = "Mercado Livre"
    else:
        oferta = await buscar_mercadolivre()
        loja_atual = "Shopee"

    if not oferta:
        logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
        return

    mensagem = (
        f"🛍️ *{oferta['loja']}* 🔥\n\n"
        f"*{oferta['titulo']}*\n"
        f"💰 {oferta['preco']}\n"
        f"[🛒 Ver oferta]({oferta['link']})"
    )

    try:
        await context.bot.send_photo(
            chat_id=CHAT_ID,
            photo=oferta["imagem"],
            caption=mensagem,
            parse_mode="Markdown"
        )
        logger.info(f"✅ Oferta enviada: {oferta['titulo']}")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar mensagem: {e}")

# =============================
# COMANDOS DO BOT
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Use /start_posting para iniciar as postagens automáticas.")

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not scheduler.get_jobs():
        scheduler.add_job(
            postar_oferta,
            trigger="interval",
            minutes=INTERVALO_MINUTOS,
            args=[context],
        )
        scheduler.start()
        await update.message.reply_text("🕒 Postagens automáticas iniciadas!")
        logger.info("🕒 Ciclo automático iniciado via /start_posting")
    else:
        await update.message.reply_text("⚠️ O bot já está postando automaticamente!")

async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scheduler.remove_all_jobs()
    await update.message.reply_text("🛑 Postagens automáticas paradas.")
    logger.info("🛑 Postagens automáticas interrompidas.")

# =============================
# MAIN
# =============================
async def main():
    application = Application.builder().token(TOKEN).build()

    # Handlers de comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))
    application.add_handler(CommandHandler("stop_posting", stop_posting))

    # Limpa webhooks e atualizações antigas
    await application.bot.delete_webhook()
    await application.bot.get_updates(offset=-1)
    logger.info("🧹 Webhook limpo e atualizações antigas removidas.")

    # Inicia o bot
    logger.info("🚀 Bot iniciado e escutando comandos.")
    await application.run_polling()

# =============================
# EXECUÇÃO
# =============================
if __name__ == "__main__":
    asyncio.run(main())
