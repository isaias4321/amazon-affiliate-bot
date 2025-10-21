# Usa a imagem base oficial do Python 3.12
FROM python:3.12-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . .

# Instala dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta usada pelo webhook (necessário para Railway)
EXPOSE 8080

# Define variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1

# Comando padrão para iniciar o bot
CMD ["python", "bot.py"]
