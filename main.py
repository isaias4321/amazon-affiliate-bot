import os
import logging
import asyncio
from threading import Thread
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import buscar_ofertas_por_categorias
from sendtotelegram import send_offer_messages

# ----------------- Configuration -----------------
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '8463817884:AAEiLsczIBOSsvazaEgNgkGUCmPJi9tmI6A')
GROUP_ID = int(os.getenv('GROUP_ID', '-4983279500'))
AFFILIATE_TAG = os.getenv('AFFILIATE_TAG', 'isaias06f-20')
SCRAPEOPS_API_KEY = os.getenv('SCRAPEOPS_API_KEY', '3694ad1e-583c-4a39-bdf9-9de5674814ee')
WEBHOOK_BASE = os.getenv('WEBHOOK_BASE', 'https://amazon-ofertas-api.up.railway.app')
INTERVAL_MINUTES = int(os.getenv('INTERVAL_MINUTES', '5'))
BOT_NAME = os.getenv('BOT_NAME', 'Amazon Ofertas Brasil')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ----------------- Flask app (webhook receiver + keepalive) -----------------
app = Flask(__name__)

# Create bot and dispatcher (used to process incoming updates)
bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=False)

# ----------------- Telegram command handlers (group-only) -----------------
def start(update, context):
    try:
        if update.effective_chat and update.effective_chat.id == GROUP_ID:
            update.message.reply_text(f"🤖 {BOT_NAME} iniciado. Monitorando ofertas a cada {INTERVAL_MINUTES} minutos.")
    except Exception:
        pass

def status(update, context):
    try:
        if update.effective_chat and update.effective_chat.id == GROUP_ID:
            update.message.reply_text("✅ Bot ativo e monitorando ofertas.")
    except Exception:
        pass

def buscar_now(update, context):
    try:
        if update.effective_chat and update.effective_chat.id == GROUP_ID:
            update.message.reply_text("🔄 Buscando ofertas agora..." )
            Thread(target=asyncio.run, args=(manual_search_and_send(),)).start()
    except Exception:
        pass

# register handlers on dispatcher
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('status', status))
dispatcher.add_handler(CommandHandler('buscar', buscar_now))

# ----------------- Search & send logic -----------------
async def manual_search_and_send():
    try:
        categorias = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"] 
        offers = await buscar_ofertas_por_categorias(categorias, AFFILIATE_TAG, SCRAPEOPS_API_KEY)
        if not offers:
            logger.info("🔍 Busca manual: nenhuma oferta encontrada (>=15%%)")
            await bot.send_message(chat_id=GROUP_ID, text="✅ Busca manual concluída — nenhuma oferta encontrada.")
            return
        await send_offer_messages(bot, GROUP_ID, offers)
        await bot.send_message(chat_id=GROUP_ID, text=f"✅ Busca manual concluída — {len(offers)} ofertas enviadas.")
    except Exception as e:
        logger.error("Erro na busca manual: %s", e)

async def job_busca_e_enviar():
    logger.info("🔄 Iniciando ciclo agendado de busca e envio de ofertas...")
    try:
        await bot.send_message(chat_id=GROUP_ID, text="🔄 Iniciando busca automática por ofertas...")
    except Exception as e:
        logger.error('Não pôde notificar grupo sobre o início do ciclo: %s', e)
    categorias = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]
    offers = await buscar_ofertas_por_categorias(categorias, AFFILIATE_TAG, SCRAPEOPS_API_KEY)
    if not offers:
        logger.info("Nenhuma oferta encontrada neste ciclo.")
        try:
            await bot.send_message(chat_id=GROUP_ID, text="✅ Ciclo concluído — nenhuma oferta encontrada.")
        except Exception:
            pass
        return
    await send_offer_messages(bot, GROUP_ID, offers)
    try:
        await bot.send_message(chat_id=GROUP_ID, text=f"✅ Ciclo concluído — {len(offers)} ofertas enviadas.")
    except Exception:
        pass
    logger.info("✅ Ciclo concluído — ofertas enviadas.")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: asyncio.run(job_busca_e_enviar()), 'interval', minutes=INTERVAL_MINUTES, id='job_buscar_e_enviar')
    scheduler.start()
    logger.info("Agendador iniciado (intervalo: %d minutos)", INTERVAL_MINUTES)

# ----------------- Webhook endpoint -----------------
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(force=True)
        update = Update.de_json(data, bot)
        dispatcher.process_update(update)
    except Exception as e:
        logger.error('Erro ao processar update via webhook: %s', e)
    return jsonify({'ok': True})

@app.route('/')
def index():
    return 'OK - Amazon Ofertas Brasil'

# ----------------- Startup helpers -----------------
def set_webhook():
    webhook_url = f"{WEBHOOK_BASE.rstrip('/')}/webhook"
    try:
        success = bot.set_webhook(url=webhook_url)
        if success:
            logger.info("Webhook registrado em: %s", webhook_url)
        else:
            logger.error("Falha ao registrar webhook em: %s", webhook_url)
    except Exception as e:
        logger.error('Erro ao registrar webhook: %s', e)

def run_flask():
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

def main():
    set_webhook()
    t = Thread(target=run_flask, daemon=True)
    t.start()
    start_scheduler()
    try:
        bot.send_message(chat_id=GROUP_ID, text=f"🤖 {BOT_NAME} iniciado e webhook registrado.")
    except Exception as e:
        logger.error("Não foi possível enviar mensagem de inicialização ao grupo: %s", e)
    try:
        # Keep the main thread alive
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Encerrando.')

if __name__ == '__main__':
    main()
