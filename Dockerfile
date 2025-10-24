FROM python:3.12

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

# ⚙️ Gera o token automaticamente durante o build
RUN python gerar_token_ml_auto.py || true

CMD ["python", "bot.py"]
