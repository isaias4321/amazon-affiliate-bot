import asyncio
import logging
import aiohttp
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# -----------------------------
# CONFIGURAÇÕES DO BOT
# -----------------------------
BOT_TOKEN = "SEU_TOKEN_AQUI"  # substitua pelo seu token
GROUP_ID = "-1001234567890"   # substitua após confirmar com o /start_posting
AFILIADO = "isaíasmaia-20"

# -----------------------------
# LOGGING
# -----------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# CATEGORIAS DE PRODUTOS
# -----------------------------
CATEGORIAS = [
    "eletrodomésticos",
    "ferramentas",
    "cadeira gamer",
    "mouse gamer",
    "monitor",
    "placa de vídeo",
    "headset gamer",
    "teclado mecânico",
    "SSD",
    "notebook gamer",
]

# -----------------------------
# FUNÇÃO DE BUSCA DE PRODUTOS
# -----------------------------
async def buscar_promocoes():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                      " AppleWebKit/537.36 (KHTML, like Gecko)"
                      " Chrome/120.0.0.0 Safari/537.36"
    }

    produtos = []
    async with aiohttp.ClientSession(headers=headers) as session:
        for categoria in CATEGORIAS:
            url = f"https://www.amazon.com.br/s?k={categoria.replace(' ', '+')}"
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        # Aqui simplificamos apenas para simular o resultado
                        produtos.append({
                            "nome": f"🔥 Oferta especial em {categoria.title()}",
                            "link": f"https://www.amazon.com.br/s?k={categoria.replace(' ', '+')}&tag={AFILIADO}"
                        })
                    else:
                        logger.warning(f"Erro HTTP {response.status} ao acessar {url}")
            except Exception as e:
                logger.error(f"Erro ao buscar {categoria}: {e}")

    return produtos

# -----------------------------
# FUNÇÃO DE POSTAGEM AUTOMÁTICA
# -----------------------------
async def postar_ofertas_automaticamente(context: ContextTypes.DEFAULT_TYPE):
    produtos = await buscar_promocoes()
    if not produtos:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text="⏱️ Nenhuma promoção encontrada agora. Tentando novamente em 2 minutos..."
        )
        logger.info("Nenhuma promoção encontrada nesta rodada.")
        return

    produto = random.choice(produtos)
    mensagem = f"{produto['nome']}\n🔗 {produto['link']}"
    await context.bot.send_message(chat_id=GROUP_ID, text=mensagem)
    logger.info(f"Mensagem enviada: {mensagem}")

# -----------------------------
# COMANDO /START_POSTING
# -----------------------------
async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"Comando recebido em chat {chat_id}")

    # Mostra ID do grupo pra confirmar
    await update.message.reply_text(f"✅ Bot ativado neste chat!\n📢 ID do grupo: `{chat_id}`", parse_mode="Markdown")

    # Atualiza o GROUP_ID (caso o usuário não tenha configurado manualmente)
    global GROUP_ID
    GROUP_ID = str(chat_id)

    # Inicia o loop de postagens automáticas a cada 2 minutos
    context.job_queue.run_repeating(postar_ofertas_automaticamente, interval=120, first=5)
    await update.message.reply_text("🚀 Postagens automáticas ativadas a cada 2 minutos!")

# -----------------------------
# MAIN
# -----------------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start_posting", start_posting))
    logger.info("Bot iniciado com sucesso.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
