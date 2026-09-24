import asyncio, sys
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.database import init_db
from app.api.endpoints import router as api_router
from app.middleware.auth import APIKeyMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database
    await init_db()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS configuration — restrict to frontend origins
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://lisa-qa-platform.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount evidence directory for static access (e.g. screenshots)
if settings.EVIDENCE_DIR.exists():
    app.mount("/evidence", StaticFiles(directory=str(settings.EVIDENCE_DIR)), name="evidence")

# API key auth middleware (only active when LISA_API_KEY is configured)
app.add_middleware(APIKeyMiddleware)


@app.get("/health")
async def health():
    """Liveness probe for load balancers / Docker healthchecks."""
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


@app.get("/")
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "llm_provider": "NvidiaProvider" if settings.NVIDIA_API_KEY else "FallbackProvider"
    }

def proactor_loop_factory():
    if sys.platform == 'win32':
        return asyncio.ProactorEventLoop()
    return asyncio.new_event_loop()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.LISA_HOST, port=settings.LISA_BACKEND_PORT, reload=True, loop="app.main:proactor_loop_factory")
