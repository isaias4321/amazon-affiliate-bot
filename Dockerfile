# Usa imagem leve com Python 3.12
FROM python:3.12-slim

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . .

# Atualiza pacotes e instala dependências necessárias
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    libnss3 \
    libxss1 \
    libasound2 \
    libxshmfence1 \
    libgbm1 \
    libgtk-3-0 \
    libatk1.0-0 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libatk-bridge2.0-0 \
    fonts-liberation \
    libdrm2 \
    libxrandr2 \
    libxdamage1 \
    libxcomposite1 \
    libxext6 \
    libxfixes3 \
    libxcb1 \
    libxi6 \
    libglu1-mesa \
    libxkbcommon0 \
    fonts-unifont \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala apenas o navegador Chromium (sem dependências extras)
RUN playwright install chromium

# Expõe a porta usada pelo bot (opcional, se usar FastAPI)
EXPOSE 8080

# Define variáveis padrão (podem ser sobrescritas no Render)
ENV BOT_TOKEN=""
ENV CHAT_ID=""

# Comando de inicialização
CMD ["python", "bot.py"]
