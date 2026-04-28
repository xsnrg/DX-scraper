from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from .service import DXPeditionService
from .config import Config
from .qrz_config import save_qrz_data, get_qrz_data
from .qrz_qso import sync_qso_data, QSO_CACHE_FILE
from .bands import frequency_to_band
import asyncio
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

@app.get("/qrz-status")
async def get_qrz_status():
    data = get_qrz_data()
    return {"callsign": data.get("callsign", ""), "token": data.get("token", "")}

@app.post("/qrz-token")
async def set_qrz_token(body: dict):
    callsign = body.get("callsign", "")
    token = body.get("token", "")
    if not callsign or not token:
        raise HTTPException(status_code=400, detail="callsign and token are required")
    save_qrz_data(callsign, token)
    return {"status": "ok"}


@app.get("/qrz-sync")
async def qrz_sync():
    data = get_qrz_data()
    callsign = data.get("callsign", "")
    token = data.get("token", "")
    if not callsign or not token:
        return JSONResponse(status_code=400, content={"status": "error", "error": "QRZ credentials not configured"})
    result = await sync_qso_data(callsign, token)
    if result.get("status") == "error":
        return JSONResponse(status_code=502, content=result)
    return result


@app.get("/qrz-cache")
async def qrz_cache():
    import json
    import os
    import time
    if not QSO_CACHE_FILE.exists():
        return {"data": [], "exists": False, "count": 0, "last_modified": ""}
    stat = QSO_CACHE_FILE.stat()
    pairs = []
    for line in QSO_CACHE_FILE.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            freq = d.get("freq", "")
            band = None
            if freq:
                try:
                    band = frequency_to_band(float(freq))
                except (ValueError, TypeError):
                    pass
            call = d.get("call", "")
            if band and call:
                pairs.append([call.upper(), band])
        except (json.JSONDecodeError, TypeError):
            pass
    last_modified = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stat.st_mtime))
    return {"data": pairs, "exists": True, "count": len(pairs), "last_modified": last_modified}
