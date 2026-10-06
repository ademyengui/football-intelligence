import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api import export, health, matches, ws
from app.config import settings
from app.services.reaper import start_stale_job_reaper_loop

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks: launch stale job reaper background loop
    reaper_task = asyncio.create_task(start_stale_job_reaper_loop())
    yield
    # Shutdown tasks
    reaper_task.cancel()

app = FastAPI(
    title="Football Intelligence Dashboard API",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# GZip middleware for large JSON responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(matches.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(ws.router)

@app.get("/")
def root():
    return {"message": "Football Intelligence Dashboard API v1.0"}
