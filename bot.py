import os
import logging
import asyncio
import random
import aiohttp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import ChatMigrated

# ==================== CONFIGURAÇÕES ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_CHAT_ID = os.getenv("CHAT_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "").strip()  # Seu ID de afiliado Amazon

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ==================== LIMPAR CONFLITOS ====================
async def liberar_antigo_bot():
    """Libera polling anterior (evita erro Conflict 409)."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook") as resp:
                if resp.status == 200:
                    logging.info("🧹 Webhook antigo removido (liberado para novo polling).")
    except Exception as e:
        logging.warning(f"Falha ao limpar webhook antigo: {e}")

# ==================== BUSCAR OFERTAS ====================
async def buscar_ofertas() -> list[dict]:
    """Simula busca de ofertas com ID de afiliado Amazon."""
    base_links = [
        "B09B8V1LZ3",  # Echo Dot
        "B0C3V7T6ZK",  # Lenovo
        "B08WSY9RRG",  # JBL
        "B0CSZK8Z12",  # Galaxy A15
        "B08DL4C5D2",  # Amazfit
    ]

    ofertas = []
    for asin in base_links:
        url = f"https://www.amazon.com.br/dp/{asin}"
        if AFFILIATE_TAG:
            url += f"?tag={AFFILIATE_TAG}"
        ofertas.append({
            "titulo": random.choice([
                "🔥 Oferta imperdível!",
                "💥 Promoção relâmpago!",
                "🛒 Desconto exclusivo!",
                "🎯 Achado do dia!"
            ]),
            "preco": random.choice(["R$ 279,00", "R$ 899,00", "R$ 2.399,00", "R$ 349,00"]),
            "link": url
        })
    return ofertas

# ==================== POSTAGENS AUTOMÁTICAS ====================
async def postar_ofertas_job(context: ContextTypes.DEFAULT_TYPE):
    """Job para postar ofertas automaticamente."""
    chat_id = context.job.chat_id
    ofertas = await buscar_ofertas()

    if not ofertas:
        logging.info("Nenhuma promoção encontrada no momento.")
        return

    for oferta in ofertas:
        msg = f"📦 *{oferta['titulo']}*\n💰 {oferta['preco']}\n🔗 [Ver oferta]({oferta['link']})"
        try:
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
            await asyncio.sleep(2)
        except ChatMigrated as e:
            novo_id = e.new_chat_id
            logging.warning(f"⚠️ Chat migrado! Novo chat_id: {novo_id}")
            os.environ["CHAT_ID"] = str(novo_id)
            await context.bot.send_message(chat_id=novo_id, text="✅ Chat migrado detectado. Continuando postagens aqui.")
        except Exception as e:
            logging.error(f"Erro ao enviar mensagem: {e}")

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Sou seu bot de ofertas automáticas da Amazon!\n\n"
        "Comandos disponíveis:\n"
        "• /start_posting → começar postagens automáticas\n"
        "• /stop_posting → parar postagens\n"
        "• /ajuda → informações de uso"
    )

async def ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Use /start_posting para iniciar as postagens automáticas de ofertas a cada minuto.\n"
        "Use /stop_posting para parar."
    )

def job_name(chat_id: int | str) -> str:
    return f"posting-{chat_id}"

async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = job_name(chat_id)
    existing = context.job_queue.get_jobs_by_name(name)

    if existing:
        await update.message.reply_text("✅ Já estou postando ofertas aqui! Use /stop_posting para parar.")
        return

    context.job_queue.run_repeating(
        postar_ofertas_job,
        interval=60,
        first=0,
        chat_id=chat_id,
        name=name
    )
    await update.message.reply_text("🚀 Comecei a postar ofertas neste chat a cada 1 minuto!")

async def stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    name = job_name(chat_id)
    jobs = context.job_queue.get_jobs_by_name(name)

    if not jobs:
        await update.message.reply_text("ℹ️ Nenhuma postagem automática está ativa neste chat.")
        return

    for job in jobs:
        job.schedule_removal()

    await update.message.reply_text("🛑 Postagens automáticas paradas neste chat.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        await update.message.reply_text(f"Você disse: {update.message.text}")

# ==================== INICIALIZAÇÃO DO BOT ====================
async def iniciar_bot():
    logging.info("🚀 Iniciando bot...")
    await liberar_antigo_bot()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajuda", ajuda))
    app.add_handler(CommandHandler("start_posting", start_posting))
    app.add_handler(CommandHandler("stop_posting", stop_posting))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Postagens automáticas fixas se CHAT_ID estiver definido
    if DEFAULT_CHAT_ID:
        app.job_queue.run_repeating(
            postar_ofertas_job,
            interval=60,
            first=5,
            chat_id=int(DEFAULT_CHAT_ID),
            name=job_name(DEFAULT_CHAT_ID)
        )
        logging.info("⏱️ Postagens automáticas ativas via CHAT_ID de ambiente.")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logging.info("✅ Bot iniciado e aguardando mensagens...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(iniciar_bot())
