from fastapi import FastAPI
from pydantic import BaseModel
import random
import logging

app = FastAPI(title="Amazon Affiliate Bot API")

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Model da requisição
class Item(BaseModel):
    categoria: str

# Exemplo de banco de ofertas simulado
OFERTAS_FAKE = {
    "notebook": [
        {"titulo": "Notebook Lenovo Ideapad 3", "preco": "R$ 2.799,00", "link": "https://amzn.to/3QbFxHt"},
        {"titulo": "Notebook Acer Aspire 5", "preco": "R$ 3.199,00", "link": "https://amzn.to/3WenFRs"}
    ],
    "processador": [
        {"titulo": "Ryzen 5 5600G", "preco": "R$ 899,00", "link": "https://amzn.to/4fKnq2H"},
        {"titulo": "Intel Core i5 12400F", "preco": "R$ 999,00", "link": "https://amzn.to/4fJEb8W"}
    ],
    "celular": [
        {"titulo": "Samsung Galaxy A15", "preco": "R$ 1.099,00", "link": "https://amzn.to/3AAaQJE"},
        {"titulo": "Redmi Note 13", "preco": "R$ 1.299,00", "link": "https://amzn.to/3AEuGzL"}
    ],
    "ferramenta": [
        {"titulo": "Parafusadeira Bosch 12V", "preco": "R$ 479,00", "link": "https://amzn.to/3WjE6MV"},
        {"titulo": "Furadeira Philco 550W", "preco": "R$ 249,00", "link": "https://amzn.to/4gN3a4K"}
    ],
    "eletrodoméstico": [
        {"titulo": "Air Fryer Mondial 4L", "preco": "R$ 349,00", "link": "https://amzn.to/3Q3xJZb"},
        {"titulo": "Liquidificador Oster", "preco": "R$ 199,00", "link": "https://amzn.to/4gK5TNY"}
    ]
}

@app.get("/")
def home():
    return {"status": "ok", "mensagem": "API do Amazon Affiliate Bot está online 🚀"}

@app.post("/buscar")
def buscar(item: Item):
    categoria = item.categoria.lower()
    logger.info(f"🛍️ Buscando ofertas para categoria: {categoria}")
    ofertas = OFERTAS_FAKE.get(categoria)
    if not ofertas:
        return {"erro": f"Nenhuma oferta encontrada para '{categoria}'"}
    return {"categoria": categoria, "oferta": random.choice(ofertas)}
