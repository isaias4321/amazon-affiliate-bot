import asyncio
import uvicorn
import nest_asyncio
from fastapi import FastAPI
from bot import iniciar_bot, postar_ofertas

nest_asyncio.apply()
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "mensagem": "Bot e API Amazon Goldbox ativos!"}

@app.get("/force")
async def force():
    await postar_ofertas()
    return {"status": "ok", "mensagem": "Ofertas enviadas manualmente."}

if __name__ == "__main__":
    async def main():
        asyncio.create_task(iniciar_bot())
        config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(main())
