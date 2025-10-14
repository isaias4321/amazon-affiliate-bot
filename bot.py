import asyncio
import logging
import aiohttp
import os
import nest_asyncio
from telegram import Bot
from telegram.error import Forbidden, InvalidToken
from datetime import datetime
from dotenv import load_dotenv

# Corrige event loop (necessário em ambientes como Jupyter, mantido por precaução)
nest_asyncio.apply()

# Configuração de logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

# --- VARIÁVEIS DE AMBIENTE (REMOVIDOS VALORES HARDCODED PARA FORÇAR USO DO RAILWAY) ---
# Se estas variáveis não estiverem definidas no Railway, o script irá falhar, o que é o comportamento desejado.
try:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    GROUP_ID = int(os.getenv("GROUP_ID"))
    API_URL = os.getenv("API_URL")
    INTERVAL_MIN = int(os.getenv("INTERVAL_MIN", 1)) # Permite configurar o intervalo em minutos

    if not all([BOT_TOKEN, GROUP_ID, API_URL]):
         raise ValueError("As variáveis de ambiente BOT_TOKEN, GROUP_ID e API_URL são obrigatórias.")
         
except (TypeError, ValueError) as e:
    logger.error(f"Erro de configuração: {e}")
    # Encerra o script se as variáveis cruciais não estiverem definidas
    exit(1)


# ======================
# BUSCAR PRODUTOS VIA SUA API
# ======================
async def buscar_produtos():
    """Busca produtos na API local (FastAPI) rodando no Railway."""
    categorias = ["notebook", "monitor", "mouse", "cadeira gamer", "teclado", "ferramenta", "geladeira"]
    produtos = []

    # Configurando um timeout de 15 segundos para a requisição
    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for categoria in categorias:
            try:
                # Usa a variável API_URL injetada do Railway
                url = f"{API_URL}/api/amazon?query={categoria}"
                async with session.get(url) as resp:
                    
                    if resp.status == 404:
                         # Isso geralmente significa que a API_URL está correta, mas a rota não existe
                         logger.error(f"Erro 404: Rota não encontrada na API. URL: {url}")
                         continue

                    if resp.status != 200:
                        logger.warning(f"Erro HTTP {resp.status} ao acessar {categoria} (URL: {url})")
                        continue
                        
                    data = await resp.json()
                    if "items" in data:
                        produtos.extend(data["items"])
                        
            except aiohttp.client_exceptions.ClientConnectorError:
                logger.error(f"Erro de conexão: API_URL '{API_URL}' não está acessível ou está incorreta.")
                break # Para o loop de categorias se a API não estiver acessível
            except asyncio.TimeoutError:
                logger.error(f"Timeout (15s) ao buscar produtos de {categoria}.")
            except Exception as e:
                logger.error(f"Erro geral ao buscar {categoria}: {e}")
    
    return produtos

# ======================
# ENVIAR OFERTAS PARA O GRUPO
# ======================
async def postar_ofertas(bot):
    """Busca e posta as 3 primeiras ofertas no grupo do Telegram."""
    produtos = await buscar_produtos()

    if not produtos:
        logger.warning("Nenhum produto encontrado. A API pode estar fora do ar ou sem dados.")
        return

    # Limita a 3 produtos por ciclo
    for produto in produtos[:3]:
        try:
            nome = produto.get("title", "Produto sem nome")
            preco = produto.get("price", "Preço indisponível")
            imagem = produto.get("image", None)
            link = produto.get("link", "https://amazon.com.br")

            # Tratamento para garantir que a formatação Markdown está correta
            nome = nome.replace('*', '').replace('_', '')
            
            legenda = f"🔥 *{nome}*\n💰 {preco}\n🔗 [Ver na Amazon]({link})"
            
            if imagem:
                await bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=imagem,
                    caption=legenda,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=GROUP_ID,
                    text=legenda,
                    parse_mode="Markdown"
                )

            await asyncio.sleep(5) # Espera 5 segundos entre cada postagem

        except Forbidden:
            logger.error("Bot sem permissão (Forbidden). Certifique-se de que o BOT_TOKEN está correto e o bot é ADMINISTRADOR do grupo.")
            return
        except Exception as e:
            logger.error(f"Erro ao postar produto: {e}")

# ======================
# LOOP PRINCIPAL
# ======================
async def main():
    """Função principal que inicia o bot e o loop de postagem."""
    bot = Bot(BOT_TOKEN)
    
    # 1. Tenta enviar uma mensagem inicial para testar o token e a permissão
    try:
        await bot.send_message(chat_id=GROUP_ID, text="🤖 Bot iniciado com sucesso! Buscando ofertas...")
    except InvalidToken:
        logger.error("ERRO CRÍTICO: BOT_TOKEN inválido. O processo será encerrado.")
        return
    except Forbidden:
        logger.error("ERRO CRÍTICO: Bot não é administrador no grupo ou GROUP_ID está incorreto. O processo será encerrado.")
        return
    except Exception as e:
         logger.error(f"ERRO CRÍTICO na inicialização do bot: {e}. O processo será encerrado.")
         return

    logger.info(f"Bot conectado ao Telegram e rodando a cada {INTERVAL_MIN} minutos.")
    
    # 2. Inicia o loop de postagem
    while True:
        await postar_ofertas(bot)
        logger.info(f"Ciclo de postagem finalizado. Próximo ciclo em {INTERVAL_MIN} minutos.")
        await asyncio.sleep(INTERVAL_MIN * 60)

if __name__ == "__main__":
    # Tratamento de erro final para garantir que o motivo do crash seja logado
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Processo interrompido pelo usuário.")
    except Exception as e:
        logger.error(f"Falha fatal no loop principal: {e}")
