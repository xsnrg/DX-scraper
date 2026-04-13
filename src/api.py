from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .service import DXPeditionService
from .config import Config
import os

app = FastAPI(title="DXpedition Monitor API")

# Mount the web directory for static files
# This allows the app to serve CSS/JS if they were separate files
if os.path.exists("src/web"):
    app.mount("/static", StaticFiles(directory="src/web"), name="static")

@app.get("/")
async def root():
    # Serve the index.html file as the home page
    if os.path.exists("src/web/index.html"):
        return FileResponse("src/web/index.html")
    return {"message": "DXpedition Monitor API - Frontend not found"}

@app.get("/data")
async def get_data():
    service = DXPeditionService(Config.DATA_MAX_AGE_SECONDS)
    return await service.get_current_data()
