import os
import requests
import logging
import time
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler

# ------------------------------------------------------------
# 🔧 CONFIGURAÇÕES DAS VARIÁVEIS DE AMBIENTE (Railway)
# ------------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG", "isaias06f-20")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# ------------------------------------------------------------
# 🛑 VERIFICAÇÃO DE VARIÁVEIS OBRIGATÓRIAS
# ------------------------------------------------------------
if not all([BOT_TOKEN, GROUP_ID, AFFILIATE_TAG, SERPAPI_KEY]):
    logging.error("❌ Variáveis de ambiente ausentes! Verifique BOT_TOKEN, GROUP_ID, AFFILIATE_TAG e SERPAPI_KEY.")
    raise SystemExit("Erro de configuração")

# ------------------------------------------------------------
# 🧠 CONFIGURAÇÕES DO BOT
# ------------------------------------------------------------
CATEGORIAS = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
bot = Bot(token=BOT_TOKEN)

# ------------------------------------------------------------
# 🔍 FUNÇÃO PARA BUSCAR PRODUTOS VIA SERPAPI
# ------------------------------------------------------------
def buscar_produtos(categoria):
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "amazon",
            "amazon_domain": "amazon.com.br",
            "q": categoria,
            "api_key": SERPAPI_KEY,
        }

        response = requests.get(url, params=params)
        if response.status_code != 200:
            logger.warning(f"Erro HTTP {response.status_code} ao buscar {categoria}")
            return []

        data = response.json()
        produtos = []

        for item in data.get("organic_results", [])[:5]:
            titulo = item.get("title")
            preco = item.get("price_str", "Preço não disponível")
            link = item.get("link")
            imagem = item.get("thumbnail")

            if not (titulo and link):
                continue

            # Adiciona o link de afiliado
            if "/dp/" in link:
                asin = link.split("/dp/")[1].split("/")[0]
                link = f"https://www.amazon.com.br/dp/{asin}/?tag={AFFILIATE_TAG}"

            produtos.append({
                "titulo": titulo,
                "preco": preco,
                "link": link,
                "imagem": imagem
            })

        return produtos

    except Exception as e:
        logger.error(f"Erro ao buscar produtos de {categoria}: {e}")
        return []

# ------------------------------------------------------------
# 🚀 FUNÇÃO PARA ENVIAR PRODUTOS NO TELEGRAM
# ------------------------------------------------------------
def enviar_produtos():
    logger.info("🔄 Iniciando ciclo de busca e envio de ofertas...")
    total = 0

    for categoria in CATEGORIAS:
        produtos = buscar_produtos(categoria)
        if not produtos:
            logger.info(f"Nenhum produto encontrado em {categoria}.")
            continue

        for p in produtos:
            msg = f"📦 *{p['titulo']}*\n💰 {p['preco']}\n🔗 [Ver na Amazon]({p['link']})"
            try:
                if p['imagem']:
                    bot.send_photo(chat_id=GROUP_ID, photo=p['imagem'], caption=msg, parse_mode="Markdown")
                else:
                    bot.send_message(chat_id=GROUP_ID, text=msg, parse_mode="Markdown")
                total += 1
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Erro ao enviar produto: {e}")

    if total == 0:
        logger.info("Nenhum produto enviado neste ciclo.")
    else:
        logger.info(f"✅ {total} produtos enviados com sucesso!")

# ------------------------------------------------------------
# ⏰ AGENDAMENTO DE EXECUÇÃO
# ------------------------------------------------------------
def job_busca_e_envio():
    enviar_produtos()

# ------------------------------------------------------------
# 🧩 EXECUÇÃO PRINCIPAL
# ------------------------------------------------------------
if __name__ == "__main__":
    logger.info("🤖 Bot de Ofertas Amazon iniciado com sucesso!")
    logger.info(f"Tag de Afiliado: {AFFILIATE_TAG}")

    scheduler = BackgroundScheduler()
    scheduler.add_job(job_busca_e_envio, "interval", hours=1)
    scheduler.start()

    # Executa imediatamente no início
    enviar_produtos()

    # Mantém o processo ativo
    while True:
        time.sleep(60)
