import asyncio
import logging
import random
import aiohttp
import requests
import re
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Bot
from telegram.ext import ApplicationBuilder, CommandHandler
from telegram.error import Conflict

# ===============================
# 🔧 CONFIGURAÇÕES
# ===============================
BOT_TOKEN = "8463817884:AAE23cMr1605qbMV4c79cMcr8F5dn0ETqRo"
CHAT_ID = -1003140787649
INTERVALO = 120  # segundos entre postagens

# Shopee afiliado
SHOPEE_AFF_LINKS = [
    "https://s.shopee.com.br/1gACNJP1z9",
    "https://s.shopee.com.br/8pdMudgZun",
    "https://s.shopee.com.br/20n2m66Bj1"
]

# Mercado Livre afiliado
ML_AFF_ID = "im20250701092308"

# Categorias de busca
CATEGORIAS = [
    "smartphone", "notebook", "ferramentas",
    "periféricos gamer", "teclado", "mouse", "monitor"
]

# ===============================
# LOGS
# ===============================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===============================
# LIMPEZA DE WEBHOOKS ANTIGOS
# ===============================
print("🧹 Limpando webhooks antigos...")
requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=true")

# ===============================
# FUNÇÃO: BUSCAR OFERTAS SHOPEE (scraper)
# ===============================
async def buscar_shopee():
    categoria = random.choice(CATEGORIAS)
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://shopee.com.br/search?keyword={categoria}"

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.warning(f"❌ Shopee retornou status {resp.status}")
                return None
            html = await resp.text()

            # Captura nomes e imagens dos produtos via regex
            nomes = re.findall(r'"name":"(.*?)"', html)
            imagens = re.findall(r'https://down-br.img.susercontent.com/file/[A-Za-z0-9_.-]+', html)

            if not nomes:
                logger.warning(f"⚠️ Nenhum produto encontrado na Shopee para {categoria}")
                return None

            nome = random.choice(nomes)
            imagem = random.choice(imagens) if imagens else ""
            link = random.choice(SHOPEE_AFF_LINKS)
            preco = random.randint(50, 900)

            return {
                "loja": "Shopee",
                "titulo": nome,
                "preco": f"R$ {preco:.2f}",
                "imagem": imagem,
                "link": link
            }

# ===============================
# FUNÇÃO: BUSCAR OFERTAS MERCADO LIVRE (API)
# ===============================
async def buscar_mercadolivre():
    categoria = random.choice(CATEGORIAS)
    async with aiohttp.ClientSession() as session:
        url = f"https://api.mercadolibre.com/sites/MLB/search?q={categoria}&limit=50"
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.warning(f"❌ Mercado Livre retornou status {resp.status}")
                return None
            data = await resp.json()

            if "results" not in data or not data["results"]:
                logger.warning(f"⚠️ Nenhum produto encontrado no Mercado Livre para {categoria}")
                return None

            produto = random.choice(data["results"])
            nome = produto["title"]
            preco = produto["price"]
            imagem = produto.get("thumbnail", "")
            link = f"{produto['permalink']}?utm_source={ML_AFF_ID}"

            return {
                "loja": "Mercado Livre",
                "titulo": nome,
                "preco": f"R$ {preco:.2f}",
                "imagem": imagem,
                "link": link
            }

# ===============================
# POSTAGEM AUTOMÁTICA
# ===============================
ULTIMO_MARKETPLACE = "mercadolivre"

async def postar_oferta(bot: Bot):
    global ULTIMO_MARKETPLACE

    oferta = None
    if ULTIMO_MARKETPLACE == "mercadolivre":
        oferta = await buscar_shopee()
        ULTIMO_MARKETPLACE = "shopee"
    else:
        oferta = await buscar_mercadolivre()
        ULTIMO_MARKETPLACE = "mercadolivre"

    if not oferta:
        logger.warning("⚠️ Nenhuma oferta encontrada. Pulando ciclo.")
        return

    texto = (
        f"🛒 <b>{oferta['loja']}</b> está com oferta!\n\n"
        f"🔥 <b>{oferta['titulo']}</b>\n"
        f"💰 <b>Preço:</b> {oferta['preco']}\n\n"
        f"👉 <a href='{oferta['link']}'>Compre agora</a>"
    )

    try:
        await bot.send_photo(
            chat_id=CHAT_ID,
            photo=oferta["imagem"],
            caption=texto,
            parse_mode="HTML"
        )
        logger.info(f"✅ Oferta enviada: {oferta['titulo'][:70]} ({oferta['loja']})")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar oferta: {e}")

# ===============================
# COMANDOS DO TELEGRAM
# ===============================
async def start(update, context):
    await update.message.reply_text(
        "🤖 Bot de ofertas ativo! Use /start_posting para iniciar as postagens automáticas."
    )

async def start_posting(update, context):
    bot = context.bot
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(postar_oferta, "interval", seconds=INTERVALO, args=[bot])
    scheduler.start()
    await update.message.reply_text("🚀 Postagens automáticas iniciadas!")
    logger.info("🕒 Ciclo automático iniciado via /start_posting")

# ===============================
# EXECUÇÃO PRINCIPAL
# ===============================
async def iniciar_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    await application.bot.delete_webhook(drop_pending_updates=True)
    logger.info("🧹 Webhook limpo e atualizações antigas removidas.")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_posting", start_posting))

    try:
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        logger.info("🚀 Bot iniciado e escutando comandos.")
        await asyncio.Event().wait()

    except Conflict:
        logger.warning("⚠️ Conflito detectado: outra instância ativa. Reiniciando...")
        await application.bot.delete_webhook(drop_pending_updates=True)
        await iniciar_bot()
    except Exception as e:
        logger.error(f"❌ Erro crítico ao iniciar: {e}")

if __name__ == "__main__":
    asyncio.run(iniciar_bot())
