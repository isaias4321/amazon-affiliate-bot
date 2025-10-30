import os
import aiohttp
from urllib.parse import urlencode

MELI_MATT_TOOL = os.getenv("MELI_MATT_TOOL", "")
MELI_MATT_WORD = os.getenv("MELI_MATT_WORD", "")
SHOPEE_AFIL = os.getenv("SHOPEE_AFIL", "")

NICHOS = [
    "eletrônicos", "informatica", "computador", "ferramentas", "eletrodomésticos"
]

def montar_link_meli_afiliado(permalink: str) -> str:
    # Mantém query existente e adiciona seus params de afiliação do Meli
    sep = "&" if "?" in permalink else "?"
    q = urlencode({"matt_tool": MELI_MATT_TOOL, "matt_word": MELI_MATT_WORD})
    return f"{permalink}{sep}{q}"

async def buscar_ofertas_mercadolivre_api(min_desconto=20, limite=6):
    """
    Busca pela API pública do Mercado Livre (site MLB - Brasil) usando keywords do nicho.
    Filtra itens com desconto >= min_desconto (quando original_price existir).
    """
    base = "https://api.mercadolibre.com/sites/MLB/search"
    ofertas = []
    async with aiohttp.ClientSession() as session:
        for termo in NICHOS:
            params = {
                "q": termo,
                "limit": 20,
                "sort": "price_asc",  # pode trocar por 'relevance'
            }
            async with session.get(base, params=params) as resp:
                if resp.status != 200:
                    continue
                data = await resp.json()

            for it in data.get("results", []):
                title = it.get("title")
                price = it.get("price")
                orig = it.get("original_price")  # pode ser None
                permalink = it.get("permalink")
                thumbnail = it.get("thumbnail")

                # calcula desconto quando possível
                desconto = 0
                if orig and orig > 0 and price:
                    desconto = round((1 - (price / orig)) * 100)

                # regra de seleção: usa desconto ou palavras chave do nicho
                if desconto >= min_desconto or any(
                    k in (title or "").lower() for k in ["ssd", "notebook", "furadeira", "smart", "placa", "processador"]
                ):
                    link_af = montar_link_meli_afiliado(permalink) if permalink else None
                    if not link_af:
                        continue
                    # formata mensagem
                    tag_desc = f"🔻 {desconto}% OFF" if desconto > 0 else "💥 Oferta"
                    msg = [
                        f"🛒 *{title}*",
                        f"💸 R$ {price:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    ]
                    if desconto > 0 and orig:
                        msg.append(f"~R$ {orig:,.2f}~".replace(",", "X").replace(".", ",").replace("X", "."))
                    msg.append(f"{tag_desc}")
                    msg.append(f"🔗 {link_af}")
                    ofertas.append("\n".join(msg))

                if len(ofertas) >= limite:
                    return ofertas

    return ofertas

async def buscar_ofertas_shopee_fallback(limite=2):
    """
    Fallback Shopee: usa o seu shortlink de afiliado como CTA.
    (Depois trocamos para Shopee OpenAPI com assinatura.)
    """
    if not SHOPEE_AFIL:
        return []
    ofertas = []
    textos = [
        "🔥 Ofertas relâmpago Shopee — confira agora!",
        "🧡 Achados Shopee com cupom & frete — veja os destaques!",
        "⚡ Shopee Flash: preços caindo — corra!",
    ]
    for t in textos[:limite]:
        ofertas.append(f"{t}\n🔗 {SHOPEE_AFIL}")
    return ofertas

async def postar_ofertas():
    try:
        ml = await buscar_ofertas_mercadolivre_api(min_desconto=20, limite=6)
        sp = await buscar_ofertas_shopee_fallback(limite=2)

        if not ml and not sp:
            logging.info("Nenhuma oferta encontrada no momento.")
            return

        # prioriza ML e complementa com Shopee fallback
        todas = ml + sp
        msg = "\n\n".join(todas[:8])
        await app_tg.bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        logging.info("✅ Ofertas enviadas com sucesso!")
    except Exception as e:
        logging.exception(f"Erro ao postar ofertas: {e}")
