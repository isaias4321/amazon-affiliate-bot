import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Optional, List

from dotenv import load_dotenv
from flask import Flask, request, jsonify
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, ContextTypes
)

from providers.amazon_api import buscar_ofertas_amazon
from providers.shopee_api import buscar_ofertas_shopee
from utils.text import formatar_oferta

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE", "").rstrip("/")
CHAT_ID_FIXED = os.getenv("TELEGRAM_CHAT_ID", "").strip() or None
POST_INTERVAL = int(os.getenv("POST_INTERVAL_SECONDS", "120"))

CATEGORIAS = ["eletronicos", "pecas de computador", "eletrodomesticos", "ferramentas"]

if not TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN não configurado no .env")

# --- Telegram Application ---
application: Application = ApplicationBuilder().token(TOKEN).build()

# Em memória: controle simples de posting ligado/desligado por chat
POSTING_ON = set()

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu posto ofertas automaticamente.\n"
        "Comandos:\n"
        "• /start_posting – começar a postar\n"
        "• /stop_posting – parar de postar\n"
        "• /status – ver status"
    )

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    POSTING_ON.add(chat_id)
    await update.message.reply_text("🚀 Começando a postar ofertas aqui! (a cada ~2 min)")

async def cmd_stop_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    POSTING_ON.discard(chat_id)
    await update.message.reply_text("🧯 Parei de postar ofertas neste chat.")

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ligado = "ON" if chat_id in POSTING_ON else "OFF"
    await update.message.reply_text(f"📊 Status deste chat: {ligado}")

application.add_handler(CommandHandler("start", cmd_start))
application.add_handler(CommandHandler("start_posting", cmd_start_posting))
application.add_handler(CommandHandler("stop_posting", cmd_stop_posting))
application.add_handler(CommandHandler("status", cmd_status))

# --- Job que busca e posta ofertas ---
async def postar_oferta_job():
    try:
        logger.info("🛍️ Verificando novas ofertas...")
        ofertas: List[dict] = []

        # Amazon (sempre tenta)
        ofertas_amz = await buscar_ofertas_amazon(CATEGORIAS, max_itens=2)
        ofertas.extend(ofertas_amz)

        # Shopee (só se credenciais válidas)
        ofertas_shp = await buscar_ofertas_shopee(CATEGORIAS, max_itens=2)
        ofertas.extend(ofertas_shp)

        if not ofertas:
            logger.info("🙈 Sem ofertas no momento.")
            return

        # Para onde postar?
        destinos = list(POSTING_ON)
        if CHAT_ID_FIXED and CHAT_ID_FIXED not in destinos:
            destinos.append(int(CHAT_ID_FIXED))

        if not destinos:
            logger.info("⚠️ Ninguém ativou /start_posting ainda. Skippando envio.")
            return

        # Posta 1–3 ofertas por rodada
        to_post = ofertas[:3]
        for chat_id in destinos:
            for of in to_post:
                texto = formatar_oferta(of)
                try:
                    await application.bot.send_message(chat_id=chat_id, text=texto, disable_web_page_preview=False)
                except Exception as e:
                    logger.warning(f"Falha ao enviar para {chat_id}: {e}")

    except Exception as e:
        logger.exception(f"Erro no job de ofertas: {e}")

# --- Scheduler (rodando no mesmo loop do PTB) ---
scheduler = AsyncIOScheduler()

# --- Flask webhook ---
app = Flask(__name__)

@app.get("/")
def health():
    return "OK", 200

@app.post(f"/webhook/{TOKEN}")
async def webhook():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        update = Update.de_json(payload, application.bot)
        # Garantir que o app esteja inicializado e rodando
        if not application.running:
            await application.initialize()
            await application.start()
        # Entrega o update à fila interna
        await application.process_update(update)
        return jsonify({"ok": True}), 200
    except Exception as e:
        logger.exception("❌ Erro no webhook")
        return jsonify({"ok": False, "error": str(e)}), 500

async def setup_webhook():
    # limpa e seta o webhook
    await application.bot.delete_webhook(drop_pending_updates=True)
    url = f"{WEBHOOK_BASE}/webhook/{TOKEN}"
    await application.bot.set_webhook(url)
    logger.info(f"✅ Webhook configurado: {url}")

async def main_async():
    # inicia app + webhook + scheduler
    await application.initialize()
    await application.start()
    await setup_webhook()

    # agenda job
    if not scheduler.running:
        scheduler.add_job(postar_oferta_job, "interval", seconds=POST_INTERVAL, id="postar_oferta", replace_existing=True)
        scheduler.start()
        logger.info("⏱️ Scheduler iniciado")

    # mantém vivo (Flask segura o processo; aqui só dormimos em background)
    while True:
        await asyncio.sleep(3600)

def start_background_tasks():
    loop = asyncio.get_event_loop()
    loop.create_task(main_async())

if __name__ == "__main__":
    # inicia tarefas assíncronas e o Flask
    start_background_tasks()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
