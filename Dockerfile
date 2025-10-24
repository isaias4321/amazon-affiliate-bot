FROM python:3.12

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# Cria o .env antes de gerar token (garante permissão de escrita)
RUN touch .env && chmod 666 .env

# Executa o script que gera o token automaticamente
RUN python gerar_token_ml_auto.py || true

CMD ["python", "bot.py"]
