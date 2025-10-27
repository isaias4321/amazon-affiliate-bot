import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from flask import Flask, request
import threading
import asyncio
from ml_api import buscar_produto_mercadolivre
from shopee_api import buscar_produto_shopee

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # URL pública do seu Railway
PORT = int(os.getenv("PORT", 8080))

# Cria app Flask para webhook
app = Flask(__name__)

# Cria app Telegram
application = Application.builder().token(TOKEN).build()


# 🔹 Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Olá! Eu sou seu bot de ofertas! Use /oferta para ver uma promoção!")


# 🔹 Comando /oferta
async def oferta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Buscando ofertas...")

    # Busca primeiro no Mercado Livre
    produto = await buscar_produto_mercadolivre()
    if not produto:
        # Se não achar, tenta Shopee
        produto = await buscar_produto_shopee()

    if produto:
        mensagem = f"🔥 OFERTA ENCONTRADA!\n\n🛍️ {produto['titulo']}\n💰 {produto['preco']}\n🔗 {produto['link']}"
        await update.message.reply_text(mensagem)
    else:
        await update.message.reply_text("⚠️ Nenhuma oferta encontrada no momento.")


# Registra comandos
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("oferta", oferta))


# 🔹 Endpoint do Webhook (onde o Telegram envia as mensagens)
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "ok", 200


# 🔹 Endpoint raiz (só pra testar se o app está rodando)
@app.route("/", methods=["GET"])
def home():
    return "🤖 Bot rodando com Webhook!", 200


# 🔹 Função para iniciar o bot com o Webhook ativo
async def setup_webhook():
    logger.info("🧹 Limpando webhooks antigos...")
    await application.bot.delete_webhook(drop_pending_updates=True)
    full_url = f"{WEBHOOK_URL}/webhook/{TOKEN}"
    await application.bot.set_webhook(url=full_url)
    logger.info(f"✅ Webhook configurado com sucesso: {full_url}")


def start_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_webhook())
    app.run(host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
