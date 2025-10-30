import os
import logging
import asyncio
import nest_asyncio
import aiohttp
from urllib.parse import urlencode
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from aiohttp import web

# ======================================================
# 🔧 CONFIGURAÇÕES INICIAIS
# ======================================================

load_dotenv()
nest_asyncio.apply()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
print("🚀 Iniciando bot...", flush=True)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK_BASE = os.getenv("WEBHOOK_BASE")

MELI_MATT_TOOL = os.getenv("MELI_MATT_TOOL", "")
MELI_MATT_WORD = os.getenv("MELI_MATT_WORD", "")
SHOPEE_AFIL = os.getenv("SHOPEE_AFIL", "")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_TOKEN não definido no .env")

# ======================================================
# 🛍️ NICHOS
# ======================================================
NICHOS = ["eletrônicos", "informatica", "computador", "ferramentas", "eletrodomésticos"]

# ======================================================
# 🛒 FUNÇÕES DE BUSCA DE OFERTAS
# ======================================================

def montar_link_meli_afiliado(permalink: str) -> str:
    sep = "&" if "?" in permalink else "?"
    q = urlencode({"matt_tool": MELI_MATT_TOOL, "matt_word": MELI_MATT_WORD})
    return f"{permalink}{sep}{q}"

async def buscar_ofertas_mercadolivre_api(min_desconto=20, limite=6):
    """Busca produtos reais do Mercado Livre com desconto."""
    base = "https://api.mercadolibre.com/sites/MLB/search"
    ofertas = []
    async with aiohttp.ClientSession() as session:
        for termo in NICHOS:
            params = {"q": termo, "limit": 30, "sort": "price_asc"}
            async with session.get(base, params=params) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()

            for it in data.get("results", []):
                title = it.get("title", "")
                price = it.get("price", 0)
                orig = it.get("original_price")
                permalink = it.get("permalink")

                # Ignorar produtos sem desconto real
                if not orig or orig <= price:
                    continue

                desconto = round((1 - price / orig) * 100)
                if desconto < min_desconto:
                    continue

                link_af = montar_link_meli_afiliado(permalink)
                msg = [
                    f"🛒 *{title}*",
                    f"💸 De ~R$ {orig:,.2f}~ por *R$ {price:,.2f}*"
                    .replace(",", "X").replace(".", ",").replace("X", "."),
                    f"🔻 {desconto}% OFF",
                    f"🔗 {link_af}",
                ]
                ofertas.append("\n".join(msg))

                if len(ofertas) >= limite:
                    return ofertas
    return ofertas

async def buscar_ofertas_shopee_fallback(limite=2):
    """Fallback para Shopee apenas se não houver ofertas do ML."""
    if not SHOPEE_AFIL:
        return []
    textos = [
        "🔥 Ofertas relâmpago Shopee — confira agora!",
        "🧡 Achados Shopee com cupom & frete — veja os destaques!",
        "⚡ Shopee Flash: preços caindo — corra!",
    ]
    return [f"{t}\n🔗 {SHOPEE_AFIL}" for t in textos[:limite]]

# ======================================================
# 🤖 FUNÇÕES DO TELEGRAM
# ======================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Olá! Use /start_posting para ativar as postagens automáticas.")

async def cmd_start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Postagem automática iniciada aqui!")

    scheduler = AsyncIOScheduler(timezone="UTC")

    async def job_postar():
        await postar_ofertas()

    scheduler.add_job(job_postar, "interval", minutes=2)
    scheduler.start()
    logging.info("⏰ Scheduler iniciado com sucesso!")

async def postar_ofertas():
    try:
        ml = await buscar_ofertas_mercadolivre_api(min_desconto=20, limite=6)

        if ml:
            todas = ml
        else:
            logging.info("Nenhuma oferta do Mercado Livre, usando fallback Shopee.")
            todas = await buscar_ofertas_shopee_fallback(limite=2)

        if not todas:
            logging.info("Nenhuma oferta encontrada no momento.")
            return

        msg = "\n\n".join(todas[:8])
        await app_tg.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        logging.info("✅ Ofertas enviadas com sucesso!")
    except Exception as e:
        logging.exception(f"Erro ao postar ofertas: {e}")

# ======================================================
# 🚀 INICIALIZAÇÃO DO BOT
# ======================================================

app_tg = Application.builder().token(TOKEN).build()
app_tg.add_handler(CommandHandler("start", cmd_start))
app_tg.add_handler(CommandHandler("start_posting", cmd_start_posting))

# ======================================================
# 🌐 HEALTH CHECK PARA RAILWAY
# ======================================================

async def healthz(request):
    return web.Response(text="ok", status=200)

async def iniciar_health_server():
    app = web.Application()
    app.add_routes([web.get("/healthz", healthz)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8081)
    await site.start()
    logging.info("💓 Health check ativo em /healthz")

# ======================================================
# 🌍 EXECUÇÃO LOCAL OU VIA RAILWAY
# ======================================================

async def main():
    asyncio.create_task(iniciar_health_server())

    if WEBHOOK_BASE:
        url = f"{WEBHOOK_BASE}/webhook/{TOKEN}"
        print(f"🌍 Iniciando em modo Webhook: {url}", flush=True)
        await app_tg.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", "8080")),
            url_path=f"webhook/{TOKEN}",
            webhook_url=url,
        )
    else:
        print("💻 Executando localmente com polling...", flush=True)
        await app_tg.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
