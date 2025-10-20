# Usa imagem base oficial do Python
FROM python:3.12-slim

# Define diretório de trabalho
WORKDIR /app

# Instala dependências do sistema necessárias para o Playwright e Chromium
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxrandr2 libxdamage1 libxext6 \
    libxfixes3 libx11-xcb1 libasound2 libxshmfence1 xvfb fonts-liberation \
    libappindicator3-1 xdg-utils unzip libgbm1 libpango-1.0-0 libatk1.0-data \
    libgdk-pixbuf2.0-0 libgtk-3-0 libxrender1 libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de dependências
COPY requirements.txt .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright e Chromium
RUN playwright install chromium

# Copia o restante do projeto
COPY . .

# Define variáveis padrão (podem ser sobrescritas no painel do Railway)
ENV PORT=8080 \
    PYTHONUNBUFFERED=1

# Expõe a porta usada pelo Railway
EXPOSE 8080

# Comando para iniciar o bot
CMD ["python", "bot.py"]
