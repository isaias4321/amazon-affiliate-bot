# Bot de Ofertas (Telegram) — Mercado Livre + Shopee

Bot que publica ofertas automaticamente no Telegram alternando entre Mercado Livre e Shopee.

## Recursos
- Alternância Shopee ↔ Mercado Livre (a cada 1 min)
- Mensagens com botão “Ver oferta 🔗”
- Mercado Livre via proxy (sem 403)
- Shopee com assinatura HMAC-SHA256
- Pronto para Railway (webhook + worker)

## Arquivos
- `bot.py`: código principal
- `requirements.txt`: dependências
- `Procfile`: define o worker no Railway
- `.env.example`: modelo de variáveis
- `utils/`: utilidades (opcional)
- `data/cache.json`: exemplo de cache

## Como rodar (local)
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # edite os valores
python bot.py
```

## Railway (deploy)
1. Suba o repositório com estes arquivos.
2. Em *Settings → Variables*, cole as variáveis do `.env`.
3. O Railway instala `requirements.txt` e inicia `worker: python bot.py`.

Logs esperados:
```
🗓️ Agendador iniciado (1 min).
🌐 Webhook configurado: https://<app>.up.railway.app/<TOKEN>
🔁 Rodada: MERCADOLIVRE
✅ Enviado: ...
```

## Variáveis necessárias
- `TELEGRAM_TOKEN`, `CHAT_ID`, `WEBHOOK_BASE`
- `MELI_MATT_TOOL`, `MELI_MATT_WORD`
- `SHOPEE_APP_ID`, `SHOPEE_APP_SECRET`
