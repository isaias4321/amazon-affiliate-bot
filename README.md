# 🤖 Amazon Affiliate Bot (Brasil)
Um bot automático que publica promoções da Amazon Brasil no Telegram com seu link de afiliado.

## 🚀 Como usar

### 1️⃣ Crie seu bot no Telegram
Use o **BotFather** e obtenha o `BOT_TOKEN`.

### 2️⃣ Crie um grupo e adicione seu bot
- Adicione o bot como administrador.
- Copie o ID do grupo (use o @RawDataBot para descobrir).

### 3️⃣ Configure as variáveis de ambiente (no Railway ou localmente)
| Nome | Descrição | Exemplo |
|------|------------|----------|
| BOT_TOKEN | Token do bot do BotFather | 123456:ABCDEF... |
| GROUP_ID | ID do grupo onde postar | -4983279500 |
| AFFILIATE_TAG | Seu código de afiliado Amazon | isaias06f-20 |
| INTERVAL_MIN | Intervalo entre postagens (minutos) | 5 |

### 4️⃣ Instale dependências
```bash
pip install -r requirements.txt
