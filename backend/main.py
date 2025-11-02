import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .api import fighters, search, stats

app = FastAPI(
    title="UFC Pokedex API",
    version="0.1.0",
    description="REST API serving UFC fighter data scraped from UFCStats.",
)

def _default_origins() -> list[str]:
    ports = list(range(3000, 3011)) + [5173]
    origins = []
    for host in ("localhost", "127.0.0.1"):
        origins.extend([f"http://{host}:{port}" for port in ports])
    origins.append("http://localhost")
    origins.append("http://127.0.0.1")
    return origins

default_origins = _default_origins()
extra_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
    if origin.strip()
]
allow_origins = extra_origins or default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for fighter images
images_dir = Path("data/images")
if images_dir.exists():
    app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    """Simple health endpoint for readiness checks."""
    return {"status": "ok"}


app.include_router(fighters.router, prefix="/fighters", tags=["fighters"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
