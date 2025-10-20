# Usa uma imagem leve e estável com Python 3.12
FROM python:3.12-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia apenas os arquivos necessários para o build inicial
COPY requirements.txt .

# Instala dependências do sistema necessárias para o Playwright + Chromium headless
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright e Chromium (modo headless)
RUN playwright install --with-deps chromium

# Copia o restante do projeto
COPY . .

# Define variáveis de ambiente úteis
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Expõe a porta usada pelo Uvicorn ou FastAPI
EXPOSE 8080

# Comando padrão de inicialização
CMD ["python", "bot.py"]
