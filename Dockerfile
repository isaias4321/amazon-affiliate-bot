# Usa imagem base leve com Python 3.12
FROM python:3.12-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia todos os arquivos do projeto para dentro do container
COPY . .

# Instala dependências do sistema necessárias para o Playwright e Chromium
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
    fonts-dejavu-core \
    && apt-get clean

# Instala dependências Python listadas no requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Instala o Playwright e o navegador Chromium (modo headless)
RUN playwright install chromium

# Expõe a porta (para FastAPI opcional ou healthcheck)
EXPOSE 8080

# Define o comando padrão para iniciar o bot
CMD ["python", "bot.py"]
