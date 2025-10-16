import logging
import asyncio

logger = logging.getLogger(__name__)

async def send_offer_messages(bot, group_id, offers):
    for offer in offers:
        title = offer.get('title')
        price_new = offer.get('price_new')
        price_old = offer.get('price_old')
        discount = offer.get('discount_pct')
        link = offer.get('link')
        def fmt_price(v):
            return f"R$ {v:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
        price_line = f"De {fmt_price(price_old)} por {fmt_price(price_new)}" if price_old and price_new else f"Preço: {price_new or 'N/A'}"
        msg = f"🔥 *OFERTA AMAZON* 🔥\n\n*{title}*\n{price_line} (-{discount}% )\n\n👉 {link}"
        try:
            await bot.send_message(chat_id=group_id, text=msg, parse_mode='Markdown', disable_web_page_preview=False)
            logger.info('🛒 Enviado: %s', title)
            await asyncio.sleep(1)
        except Exception as e:
            logger.error('Erro ao enviar oferta para Telegram: %s', e)
