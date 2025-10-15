import os
import time
import logging
import asyncio
import aiohttp
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# -----------------------------------------------------
# 1. Configuração do Logging
# -----------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------
# 2. Variáveis de Ambiente (Railway)
# -----------------------------------------------------
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID')
AFFILIATE_TAG = os.getenv('AFFILIATE_TAG', 'isaias06f-20')

if not TELEGRAM_TOKEN or not GROUP_CHAT_ID:
    logger.error("ERRO: TELEGRAM_TOKEN ou GROUP_CHAT_ID não configurado.")
    exit(1)

bot = Bot(token=TELEGRAM_TOKEN)

# URL da sua API (Railway)
API_URL = "https://amazon-affiliate-bot-production.up.railway.app/buscar"

# -----------------------------------------------------
# 3. Funções de Busca de Ofertas (via sua API)
# -----------------------------------------------------
async def buscar_ofertas_amazon():
    """
    Consulta a API FastAPI hospedada no Railway para buscar produtos com imagem.
    """
    categorias = ["notebook", "processador", "celular", "ferramenta", "eletrodoméstico"]
    ofertas = []

    try:
        async with aiohttp.ClientSession() as session:
            for cat in categorias:
                async with session.get(f"{API_URL}?q={cat}") as resp:
                    if resp.status != 200:
                        logger.warning(f"Erro HTTP {resp.status} ao buscar {cat}")
                        continue

                    data = await resp.json()
                    produtos = data.get("results", [])
                    for p in produtos:
                        ofertas.append({
                            'nome': p['title'],
                            'preco_atual': p['price'],
                            'preco_antigo': '—',
                            'desconto': '—',
                            'link_afiliado': p['url'],
                            'categoria': cat.capitalize(),
                            'imagem': p.get('image', '')
                        })
                    await asyncio.sleep(2)  # pequena pausa entre categorias
    except Exception as e:
        logger.error(f"Erro ao buscar ofertas: {e}")

    return ofertas

# -----------------------------------------------------
# 4. Envio das Ofertas no Telegram
# -----------------------------------------------------
async def enviar_oferta_telegram(oferta):
    """
    Envia a oferta com imagem (se disponível) e texto formatado em HTML.
    """
    mensagem = (
        f"🔥 <b>OFERTA AMAZON ({oferta['categoria'].upper()})</b> 🔥\n\n"
        f"🛒 <i>{oferta['nome']}</i>\n\n"
        f"💰 <b>Preço:</b> {oferta['preco_atual']}\n\n"
        f"➡️ <a href=\"{oferta['link_afiliado']}\">CLIQUE AQUI PARA VER NA AMAZON</a>"
    )

    try:
        if oferta.get('imagem'):
            await bot.send_photo(
                chat_id=GROUP_CHAT_ID,
                photo=oferta['imagem'],
                caption=mensagem,
                parse_mode=ParseMode.HTML
            )
        else:
            await bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=mensagem,
                parse_mode=ParseMode.HTML
            )
        logger.info(f"✅ Oferta enviada: {oferta['nome']}")
    except Exception as e:
        logger.error(f"Erro ao enviar oferta: {e}")

# -----------------------------------------------------
# 5. Ciclo de Busca + Envio
# -----------------------------------------------------
async def job_busca_e_envio():
    logger.info("🔄 Iniciando ciclo de busca e envio de ofertas...")
    ofertas = await buscar_ofertas_amazon()

    if not ofertas:
        logger.info("Nenhuma oferta encontrada neste ciclo.")
        return

    logger.info(f"Encontradas {len(ofertas)} ofertas. Enviando para o grupo...")
    for oferta in ofertas[:10]:  # limita a 10 por ciclo para evitar flood
        await enviar_oferta_telegram(oferta)
        await asyncio.sleep(10)  # pausa entre mensagens

# -----------------------------------------------------
# 6. Loop Principal e Agendamento
# -----------------------------------------------------
async def main():
    logger.info("🤖 Bot de Ofertas Amazon iniciado com sucesso!")
    logger.info(f"Tag de Afiliado: {AFFILIATE_TAG}")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(job_busca_e_envio, 'interval', minutes=120)  # a cada 2h
    await job_busca_e_envio()  # executa imediatamente
    scheduler.start()

    try:
        await asyncio.Future()  # mantém o loop ativo
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Bot encerrado com segurança.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
