# Usa imagem base leve
FROM python:3.12-slim

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . .

# Atualiza pacotes e instala dependências necessárias
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

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright e Chromium
RUN playwright install --with-deps chromium

# Define variáveis de ambiente obrigatórias (pode sobrescrever no painel)
ENV PYTHONUNBUFFERED=1

# Expõe a porta (para FastAPI opcional)
EXPOSE 8080

# Inicia o bot (sem múltiplas instâncias)
CMD ["python", "bot.py"]
