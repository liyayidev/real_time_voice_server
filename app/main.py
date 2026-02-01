from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import logger
from app.core.redis import redis_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up Realtime Voice Server...")
    try:
        await redis_client.connect()
    except Exception as e:
        logger.critical(f"Startup failed: {e}")
        # In production we might want to exit, but for dev we might continue or retry
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await redis_client.close()

app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    version="0.1.0"
)

from fastapi.staticfiles import StaticFiles
from app.api.ws_endpoints import router as ws_router

app.include_router(ws_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def get_index():
    from fastapi.responses import FileResponse
    return FileResponse("app/static/index.html")

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=settings.DEBUG
    )
    # python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

