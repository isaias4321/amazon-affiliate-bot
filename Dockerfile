# Usa imagem base do Python
FROM python:3.12-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia arquivos do projeto
COPY . .

# Instala dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    curl \
    libnss3 \
    libxss1 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxrandr2 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libx11-xcb1 \
    libasound2 \
    libxshmfence1 \
    fonts-liberation \
    xdg-utils \
    libgbm1 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta (necessário pro Railway)
EXPOSE 8080

# Comando de inicialização
CMD ["python", "bot.py"]
