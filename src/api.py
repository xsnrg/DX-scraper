from fastapi import FastAPI
from .service import DXPeditionService
from .config import Config

app = FastAPI(title="DXpedition Monitor API")

@app.get("/")
async def root():
    return {"message": "DXpedition Monitor API"}

@app.get("/data")
async def get_data():
    service = DXPeditionService(Config.DATA_MAX_AGE_SECONDS)
    return await service.get_current_data()
