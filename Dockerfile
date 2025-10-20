# Imagem base com Python 3.12
FROM python:3.12-slim

# Diretório de trabalho
WORKDIR /app

# Copia o projeto para dentro do container
COPY . .

# Instala dependências do sistema necessárias para Playwright e Chromium
RUN apt-get update && apt-get install -y \
    wget \
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
    && apt-get clean

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright e Chromium
RUN playwright install --with-deps chromium

# Expõe a porta (para FastAPI opcional)
EXPOSE 8080

# Comando padrão: inicia o bot
CMD ["python", "bot.py"]
