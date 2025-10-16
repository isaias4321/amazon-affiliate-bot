import aiohttp
import logging

logger = logging.getLogger(__name__)

async def enviar_mensagem(token, group_id, oferta):
    msg = f"🔥 *{oferta['titulo']}*\n💰 Preço: {oferta['preco']}\n👉 [Compre aqui]({oferta['link']})"
    async with aiohttp.ClientSession() as session:
        await session.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={
                "chat_id": group_id,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": "true"
            }
        )
    logger.info(f"🛒 Enviado: {oferta['titulo']}")
