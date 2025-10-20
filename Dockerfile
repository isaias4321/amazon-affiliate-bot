# Usa imagem leve com Python 3.12
FROM python:3.12-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia apenas o requirements primeiro para cache otimizado
COPY requirements.txt .

# Instala dependências do sistema necessárias para o Playwright + Chromium headless
RUN apt-get update && apt-get install -y --no-install-recommends \
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
    fonts-unifont \
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

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala o Playwright (sem deps, pois já instalamos manualmente acima)
RUN playwright install chromium

# Copia o restante do código do projeto
COPY . .

# Define variáveis de ambiente úteis
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Expõe a porta usada pelo FastAPI/Uvicorn
EXPOSE 8080

# Comando de inicialização
CMD ["python", "bot.py"]
