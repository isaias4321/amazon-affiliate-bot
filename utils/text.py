def formatar_oferta(o: dict) -> str:
    fonte = o.get("fonte", "LOJA")
    titulo = o.get("titulo", "Oferta")
    preco = o.get("preco", "—")
    link = o.get("link", "")
    # Pode enriquecer com imagem (enviar como foto com caption, se quiser)
    return f"🛒 <b>{fonte}</b>\n{titulo}\n💰 {preco}\n🔗 {link}"
