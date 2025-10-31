from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI

from .api import fighters, search, stats

app = FastAPI(
    title="UFC Pokedex API",
    version="0.1.0",
    description="REST API serving UFC fighter data scraped from UFCStats.",
)


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    """Simple health endpoint for readiness checks."""
    return {"status": "ok"}


app.include_router(fighters.router, prefix="/fighters", tags=["fighters"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
