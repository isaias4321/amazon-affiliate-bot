# Usa a imagem base oficial do Python 3.12
FROM python:3.12-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . .

# Atualiza pacotes e instala dependências necessárias para o Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxrandr2 libxdamage1 libxext6 \
    libxfixes3 libx11-xcb1 libasound2 libxshmfence1 xvfb fonts-liberation \
    fonts-dejavu fonts-freefont-ttf fonts-unifont \
    libappindicator3-1 xdg-utils unzip libgbm1 libpango-1.0-0 \
    libgdk-pixbuf-2.0-0 libgtk-3-0 libxrender1 libxcb1 libx11-6 libxau6 libxdmcp6 \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala o Chromium e dependências do Playwright
RUN npx playwright install --with-deps chromium || playwright install chromium

# Expõe a porta usada pelo webhook (necessário para Railway)
EXPOSE 8080

# Define variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# Comando padrão para iniciar o bot
CMD ["python", "bot.py"]
