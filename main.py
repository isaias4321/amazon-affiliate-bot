import asyncio
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot
import requests

# ======================================================
# 🔧 CONFIGURAÇÕES PRINCIPAIS
# ======================================================

TOKEN = "8463817884:AAG1cuPG4l77RFy8l95WsCjj9tp88dRDomE"
GROUP_ID = -1003140787649
AFFILIATE_TAG = "isaias06f-20"
AXESSO_API_KEY = "fb2f7fd38c57470489d000c1c7aa8cd6"  # sua chave primária

# ======================================================
# ⚙️ LOGGING
# ======================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ======================================================
# 🤖 CONFIGURAÇÃO DO BOT TELEGRAM
# ======================================================

bot = Bot(token=TOKEN)

# ======================================================
# 🛒 FUNÇÃO: Buscar ofertas usando API Axesso
# ======================================================

def buscar_ofertas(categoria: str):
    """
    Busca produtos da categoria usando a API Axesso.
    Retorna uma lista de dicionários com informações básicas dos produtos.
    """
    logger.info(f"🔍 Buscando ofertas na categoria '{categoria}'...")

    try:
        url = "https://api.axesso.de/amz/amazon-best-sellers-list"
        params = {
            "url": f"https://www.amazon.com.br/gp/bestsellers/{categoria}/",
            "page": 1
        }
        headers = {"x-rapidapi-key": AXESSO_API_KEY}

        response = requests.get(url, headers=headers, params=params, timeout=30)

        if response.status_code != 200:
            logger.error(f"❌ Erro ao buscar '{categoria}': {response.status_code}")
            return []

        data = response.json()
        produtos = data.get("products", [])

        ofertas = []
        for produto in produtos:
            nome = produto.get("productTitle")
            link = f"https://www.amazon.com.br{produto.get('url')}?tag={AFFILIATE_TAG}"
            rating = produto.get("productRating")
            reviews = produto.get("countReview")
            posicao = produto.get("position")

            ofertas.append({
                "nome": nome,
                "link": link,
                "rating": rating,
                "reviews": reviews,
                "posicao": posicao
            })

        logger.info(f"✅ {len(ofertas)} ofertas encontradas em '{categoria}'")
        return ofertas

    except Exception as e:
        logger.error(f"⚠️ Erro ao buscar {categoria}: {e}")
        return []

# ======================================================
# 💬 FUNÇÃO: Enviar mensagens no Telegram
# ======================================================

async def enviar_para_telegram(oferta):
    """
    Envia uma oferta formatada para o grupo do Telegram.
    """
    nome = oferta["nome"]
    link = oferta["link"]
    rating = oferta["rating"] or "⭐ Sem avaliações"
    reviews = oferta["reviews"] or 0
    posicao = oferta["posicao"]

    msg = (
        f"🔥 *{nome}*\n"
        f"📊 *Ranking:* {posicao}\n"
        f"⭐ *Avaliação:* {rating} ({reviews} reviews)\n"
        f"🔗 [Ver na Amazon]({link})"
    )

    try:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=msg,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )
        logger.info(f"✅ Oferta enviada: {nome}")
    except Exception as e:
        logger.error(f"⚠️ Erro ao enviar oferta para o Telegram: {e}")

# ======================================================
# 🔁 CICLO DE BUSCA
# ======================================================

async def ciclo_de_busca(bot):
    """
    Executa o ciclo completo: busca e envia as ofertas.
    """
    logger.info("🔄 Iniciando ciclo de busca de ofertas...")

    categorias = ["eletrodomesticos", "computers", "tools"]
    ofertas_encontradas = []

    for categoria in categorias:
        resultados = buscar_ofertas(categoria)
        ofertas_encontradas.extend(resultados)
        await asyncio.sleep(2)

    if not ofertas_encontradas:
        logger.info("⚠️ Nenhuma oferta encontrada neste ciclo.")
        return

    for oferta in ofertas_encontradas[:10]:  # envia até 10 por ciclo
        await enviar_para_telegram(oferta)
        await asyncio.sleep(5)

    logger.info("✅ Ciclo concluído!")

# ======================================================
# 🚀 MAIN (executa o bot e agenda o ciclo)
# ======================================================

async def main():
    logger.info("🤖 Iniciando bot *Amazon Ofertas Brasil* (2 em 2 minutos)...")

    loop = asyncio.get_event_loop()
    scheduler = BackgroundScheduler()

    def agendar_busca():
        loop.create_task(ciclo_de_busca(bot))

    scheduler.add_job(agendar_busca, "interval", minutes=2)
    scheduler.start()

    logger.info("✅ Agendador iniciado. Executando primeira busca agora...")
    await ciclo_de_busca(bot)

    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
