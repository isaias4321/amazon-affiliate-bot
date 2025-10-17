import requests
import logging
import asyncio
from telegram import Bot, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 🔑 CONFIGURAÇÕES
TOKEN = "8463817884:AAG1cuPG4l77RFy8l95WsCjj9tp88dRDomE"
CHAT_ID = "-4983279500"
API_KEY = "59ce64518d90456d95ad55f293bb877e"
AFFILIATE_TAG = "isaias06f-20"

# 🔍 CATEGORIAS A SEREM MONITORADAS
CATEGORIES = {
    "Eletrodomésticos": "https://www.amazon.com.br/gp/bestsellers/appliances",
    "Peças de Computador": "https://www.amazon.com.br/gp/bestsellers/computers",
    "Ferramentas": "https://www.amazon.com.br/gp/bestsellers/hi"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

scheduler = AsyncIOScheduler()


# 📦 Função para buscar best-sellers via Axesso API
def buscar_best_sellers(categoria_nome, categoria_url):
    url = "https://api.axesso.de/amz/amazon-best-sellers-list"
    params = {"url": categoria_url, "page": 1}
    headers = {"x-rapidapi-key": API_KEY}

    logging.info(f"🔍 Buscando best-sellers em {categoria_nome}...")
    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        produtos_filtrados = []
        for p in data.get("products", []):
            if p.get("productRating"):
                rating_str = p["productRating"].split(" ")[0]
                try:
                    rating = float(rating_str)
                    if rating >= 4.0:
                        produtos_filtrados.append(p)
                except ValueError:
                    continue

        logging.info(f"✅ {len(produtos_filtrados)} produtos com nota >= 4 encontrados em {categoria_nome}")
        return produtos_filtrados

    except Exception as e:
        logging.error(f"❌ Erro ao buscar {categoria_nome}: {e}")
        return []


# 💬 Envia mensagem formatada pro Telegram
async def enviar_ofertas(bot: Bot):
    for nome, url in CATEGORIES.items():
        produtos = buscar_best_sellers(nome, url)

        if not produtos:
            await bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Nenhuma oferta com nota >= 4 em {nome}.")
            continue

        for p in produtos[:5]:  # limita a 5 produtos por categoria
            titulo = p.get("productTitle", "Produto sem nome")
            avaliacao = p.get("productRating", "Sem avaliação")
            link = f"https://www.amazon.com.br{p['url']}?tag={AFFILIATE_TAG}"
            posicao = p.get("position", "")
            reviews = p.get("countReview", 0)

            msg = (
                f"🔥 *{titulo}*\n"
                f"⭐ {avaliacao} ({reviews} avaliações)\n"
                f"📦 Categoria: {nome}\n"
                f"🏅 Posição: {posicao}\n"
                f"🔗 [Ver na Amazon]({link})"
            )

            await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")


# ⏱️ Ciclo de busca
async def ciclo_de_busca(bot: Bot):
    logging.info("🔄 Iniciando ciclo de busca de ofertas...")
    await enviar_ofertas(bot)
    logging.info("✅ Ciclo concluído!")


# 🤖 Mensagem de boas-vindas
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "🤖 *Bot conectado!*\n\n"
        "🔔 Enviaremos as melhores ofertas da Amazon a cada 5 minutos!\n"
        "🛒 Categorias: Eletrodomésticos, Peças de Computador e Ferramentas."
    )
    await context.bot.send_message(chat_id=CHAT_ID, text=welcome_msg, parse_mode="Markdown")


async def main():
    bot = Bot(token=TOKEN)

    # Envia a mensagem de boas-vindas ao iniciar
    await bot.send_message(
        chat_id=CHAT_ID,
        text="🤖 *Bot conectado!*\n\n🔔 Enviaremos as melhores ofertas da Amazon a cada 5 minutos!\n🛒 Categorias: Eletrodomésticos, Peças de Computador e Ferramentas.",
        parse_mode="Markdown"
    )

    # Inicia agendador
    scheduler.add_job(lambda: asyncio.create_task(ciclo_de_busca(bot)), "interval", minutes=5)
    scheduler.start()

    logging.info("🚀 Bot Amazon Ofertas Brasil iniciado (atualiza a cada 5 min)...")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
