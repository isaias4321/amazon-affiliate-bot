import asyncio
import logging
import random
import re
import os
from bs4 import BeautifulSoup
import aiohttp
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import InvalidToken, Forbidden
# Se você estiver usando um arquivo .env localmente, use: from dotenv import load_dotenv

# Configuração de logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- VARIÁVEIS DE AMBIENTE (OBRIGATÓRIO PARA DEPLOY NO RAILWAY) ---
try:
    # Remove os valores hardcoded para forçar o uso de variáveis de ambiente do Railway
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    # O CHAT_ID deve ser um inteiro (incluindo o sinal de menos para grupos)
    CHAT_ID = int(os.getenv("CHAT_ID"))
    AFILIADO = os.getenv("AFILIADO_TAG")
    INTERVALO_MINUTOS = int(os.getenv("INTERVALO_MINUTOS", 2)) 

    if not all([BOT_TOKEN, CHAT_ID, AFILIADO]):
         # Se faltar qualquer variável essencial, o script encerra e o erro aparece no log do Railway.
         raise ValueError("As variáveis BOT_TOKEN, CHAT_ID e AFILIADO_TAG são obrigatórias.")
         
except (TypeError, ValueError) as e:
    logger.error(f"ERRO DE CONFIGURAÇÃO CRÍTICO: Verifique as variáveis de ambiente no Railway: {e}")
    exit(1)

# ==========================
# URLs de CATEGORIAS
# ==========================
URLS_CATEGORIAS = [
    "https://www.amazon.com.br/gp/browse.html?node=16243862011",  # Eletrônicos
    "https://www.amazon.com.br/gp/browse.html?node=16364755011",  # Games
    "https://www.amazon.com.br/gp/browse.html?node=16243890011"    # Computadores
]

# ==========================
# BUSCAR PRODUTOS COM DESCONTO (WEB SCRAPING)
# ==========================
async def buscar_produtos_com_desconto():
    """Realiza web scraping nas URLs da Amazon para encontrar produtos em promoção."""
    produtos = []
    
    # Adiciona timeout para evitar que o processo trave
    timeout = aiohttp.ClientTimeout(total=20) 
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for url in URLS_CATEGORIAS:
            try:
                # Usa um User-Agent de navegador real para evitar bloqueio
                async with session.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}) as response:
                    if response.status != 200:
                        logger.warning(f"Erro HTTP {response.status} ao acessar {url}. O scraping pode estar sendo bloqueado.")
                        continue
                    html = await response.text()
                    # Usa 'lxml' que é mais rápido e robusto que 'html.parser'
                    soup = BeautifulSoup(html, "lxml") 

                    for produto in soup.select(".s-result-item"):
                        # Seletores simplificados
                        titulo_tag = produto.select_one("h2 a span")
                        preco_tag = produto.select_one(".a-price-whole")
                        link_tag = produto.select_one("h2 a")
                        imagem_tag = produto.select_one("img")
                        preco_antigo_tag = produto.select_one(".a-text-price span")

                        if not (titulo_tag and preco_tag and link_tag):
                            continue

                        titulo = titulo_tag.text.strip()
                        preco = preco_tag.text.strip()
                        link = link_tag["href"]
                        imagem_url = imagem_tag["src"] if imagem_tag else None

                        # --- Lógica de Desconto ---
                        desconto = None
                        if preco_antigo_tag:
                            try:
                                # Converte o valor limpo com vírgula para ponto e depois para float
                                preco_antigo_val = float(re.sub(r"[^\d,]", "", preco_antigo_tag.text).replace(',', '.'))
                                preco_atual_val = float(re.sub(r"[^\d,]", "", preco).replace('.', '').replace(',', '.'))
                                
                                if preco_antigo_val > preco_atual_val:
                                    desconto = int(100 - (preco_atual_val / preco_antigo_val * 100))
                            except:
                                logger.debug("Falha ao calcular desconto para um item.")
                                pass

                        # Só adiciona se tiver um desconto razoável (ex: 5% ou mais)
                        if desconto and desconto >= 5:
                            # Constrói o link final com a tag de afiliado
                            final_link = f"https://www.amazon.com.br{link}?tag={AFILIADO}" if not link.startswith("http") else f"{link}?tag={AFILIADO}"

                            produtos.append({
                                "titulo": titulo,
                                "preco": preco,
                                "desconto": desconto,
                                "link": final_link,
                                "imagem": imagem_url
                            })
                            
            except Exception as e:
                logger.error(f"Erro fatal no scraping de {url}: {e}")

    # Retorna uma lista de produtos únicos
    return list({p['link']: p for p in produtos}.values())


# ==========================
# POSTAR NO TELEGRAM
# ==========================
async def postar_produto(bot: Bot, produto: dict):
    """Formata e envia a mensagem da oferta para o Telegram."""
    
    # Limpeza básica do título para evitar erros de HTML/Markdown
    titulo_limpo = produto['titulo'].replace('<', '&lt;').replace('>', '&gt;')

    mensagem = (
        f"🔥 <b>OFERTA!</b> -{produto['desconto']}% 🔥\n\n"
        f"➡️ <b>{titulo_limpo}</b>\n"
        f"💰 Por: R$ <b>{produto['preco']}</b>\n\n"
        f"🛒 <a href='{produto['link']}'>COMPRE AGORA na Amazon!</a>"
    )

    try:
        if produto["imagem"]:
            await bot.send_photo(
                chat_id=CHAT_ID,
                photo=produto["imagem"],
                caption=mensagem,
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=mensagem,
                parse_mode="HTML",
                disable_web_page_preview=False
            )
        logger.info(f"Produto postado: {produto['titulo']}")
        
    except Forbidden:
        logger.error("Permissão negada (Forbidden). O bot é administrador do grupo?")
    except InvalidToken:
        logger.error("Token Inválido.")
    except Exception as e:
        logger.error(f"Erro ao postar produto: {e}")

# ==========================
# LOOP AUTOMÁTICO (RODA EM BACKGROUND)
# ==========================
async def loop_postagens(context: ContextTypes.DEFAULT_TYPE):
    """Job que roda a cada 'INTERVALO_MINUTOS' para buscar e postar ofertas."""
    bot = context.bot
    
    logger.info("Iniciando ciclo de busca de ofertas...")
    produtos = await buscar_produtos_com_desconto()
    
    if not produtos:
        logger.info("Nenhum produto com desconto encontrado neste ciclo.")
    else:
        # Posta um produto aleatório com desconto
        produto = random.choice(produtos) 
        await postar_produto(bot, produto)
        
    logger.info(f"Ciclo finalizado. Próximo ciclo em {INTERVALO_MINUTOS} minutos.")

# ==========================
# COMANDO /start_posting (opcional, para iniciar manualmente via Telegram)
# ==========================
async def start_posting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde ao comando /start_posting e agenda o loop."""
    
    # Adiciona uma checagem de ID simples, se desejar que só o dono possa usar
    # if update.message.chat_id != CHAT_ID:
    #     await update.message.reply_text("Este comando só pode ser usado no chat configurado.")
    #     return
        
    await update.message.reply_text(f"🚀 Loop de postagens agendado! Verificando a Amazon a cada {INTERVALO_MINUTOS} minutos.")

    # Agenda a tarefa de postagem (se não estiver agendada)
    if not context.job_queue.get_jobs_by_name("auto_post_job"):
        context.job_queue.run_repeating(
            loop_postagens, 
            interval=INTERVALO_MINUTOS * 60, # segundos
            first=0, # Inicia imediatamente
            name="auto_post_job"
        )
        logger.info("Tarefa de postagem agendada com sucesso.")
    else:
        await update.message.reply_text("O loop de postagens já está ativo.")

# ==========================
# MAIN
# ==========================
def main():
    """Função principal que configura o bot."""
    
    logger.info("Iniciando aplicação do Telegram...")
    try:
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Adiciona o handler para o comando de start manual
        app.add_handler(CommandHandler("start_posting", start_posting))
        
        # Inicia a tarefa de postagem logo que o bot inicia
        # O Job Queue usa o loop do Polling para rodar em intervalos
        app.job_queue.run_repeating(
            loop_postagens, 
            interval=INTERVALO_MINUTOS * 60,
            first=10, # 10 segundos após iniciar
            name="auto_post_job"
        )

        logger.info("Bot configurado. Iniciando Polling (Loop infinito)...")
        # O Polling mantém o processo do Railway vivo, escutando e executando jobs
        app.run_polling(poll_interval=1) 
        
    except InvalidToken:
        logger.error("Token de Bot Inválido. Verifique a variável BOT_TOKEN no Railway.")
    except Exception as e:
        logger.critical(f"Falha CRÍTICA ao iniciar o bot: {e}")

if __name__ == "__main__":
    main()
