# Usa imagem leve com Python
FROM python:3.13-slim

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . .

# Atualiza pacotes e instala dependências do sistema necessárias para o Playwright
RUN apt-get update && apt-get install -y \
    wget \
    g++ \
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
    && apt-get clean

# Instala dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright (módulo Python + navegador Chromium)
RUN pip install playwright && playwright install --with-deps chromium

# Expõe a porta usada pelo FastAPI/Uvicorn (caso use)
EXPOSE 8080

# Comando de inicialização
CMD ["python", "bot.py"]
