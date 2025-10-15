import os
import logging
import requests
from apscheduler.schedulers.blocking import BlockingScheduler
from bot import enviar_oferta

# Configuração do logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Variáveis de ambiente
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = os.getenv("GROUP_ID")
AFFILIATE_TAG = os.getenv("AFFILIATE_TAG")
RAIN_API_KEY = os.getenv("RAIN_API_KEY")

# Verificação
if not all([BOT_TOKEN, GROUP_ID, AFFILIATE_TAG, RAIN_API_KEY]):
    logger.error("❌ Variáveis de ambiente ausentes! Verifique BOT_TOKEN, GROUP_ID, AFFILIATE_TAG e RAIN_API_KEY.")
    raise SystemExit("Erro de configuração")

# Categorias que o bot vai buscar
CATEGORIES = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]

# Função para buscar produtos
def buscar_produtos(termo):
    url = "https://api.rainforestapi.com/request"
    params = {
        "api_key": RAIN_API_KEY,
        "type": "search",
        "amazon_domain": "amazon.com.br",
        "search_term": termo,
        "sort_by": "featured"
    }

    try:
        r = requests.get(url, params=params, timeout=20)
        if r.status_code != 200:
            logger.warning(f"Erro HTTP {r.status_code} ao buscar {termo}")
            return []

        data = r.json()
        produtos = data.get("search_results", [])
        resultados = []

        for p in produtos[:5]:
            info = {
                "titulo": p.get("title"),
                "preco": p.get("price", {}).get("raw", "Preço indisponível"),
                "link": p.get("link"),
                "imagem": p.get("image"),
            }
            resultados.append(info)

        return resultados

    except Exception as e:
        logger.error(f"Erro ao buscar produtos de {termo}: {e}")
        return []

# Função principal de envio
def job_busca_e_envio():
    logger.info("🔄 Iniciando ciclo de busca e envio de ofertas...")

    total_enviados = 0
    for categoria in CATEGORIES:
        produtos = buscar_produtos(categoria)
        if not produtos:
            logger.warning(f"Nenhum produto encontrado para {categoria}")
            continue

        for p in produtos:
            if p["titulo"] and p["link"]:
                link_afiliado = f"{p['link']}?tag={AFFILIATE_TAG}"
                enviar_oferta(p["titulo"], p["preco"], link_afiliado, p["imagem"])
                total_enviados += 1

    logger.info(f"✅ Ciclo concluído! {total_enviados} ofertas enviadas.")

# Scheduler
if __name__ == "__main__":
    logger.info("🤖 Bot de Ofertas Amazon iniciado com sucesso!")
    logger.info(f"Tag de Afiliado: {AFFILIATE_TAG}")

    scheduler = BlockingScheduler()
    scheduler.add_job(job_busca_e_envio, "interval", minutes=30)
    job_busca_e_envio()
    scheduler.start()
