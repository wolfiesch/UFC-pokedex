import os
import uuid
import logging
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import ValidationError
from sqlalchemy.exc import (
    DatabaseError,
    DBAPIError,
    IntegrityError,
    OperationalError,
    TimeoutError as SQLAlchemyTimeoutError,
)

from .api import events, favorites, fighters, fightweb, search, stats
from .schemas.error import (
    ErrorResponse,
    ErrorType,
    ValidationErrorDetail,
    ValidationErrorResponse,
)

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Context variable for request ID tracking
request_id_context: ContextVar[str] = ContextVar("request_id", default="")


def _sanitize_database_url(url: str) -> str:
    """Sanitize database URL to hide password in logs."""
    if "://" not in url:
        return url

    # Split into scheme and rest
    scheme, rest = url.split("://", 1)

    # Check if there's authentication
    if "@" in rest:
        # Format: scheme://user:password@host/db
        auth, host_db = rest.split("@", 1)
        if ":" in auth:
            user, _ = auth.split(":", 1)
            return f"{scheme}://{user}:***@{host_db}"
        return f"{scheme}://{auth}@{host_db}"

    # No authentication to hide
    return url


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Initialize database tables for SQLite
    from backend.db.connection import get_database_type, get_database_url, get_engine
    from backend.db.models import Base

    db_type = get_database_type()
    db_url = get_database_url()
    sanitized_url = _sanitize_database_url(db_url)

    # Preflight logging
    logger.info("=" * 60)
    logger.info("UFC Pokedex API - Database Preflight Check")
    logger.info("=" * 60)
    logger.info(f"Database Type: {db_type.upper()}")
    logger.info(f"Database URL: {sanitized_url}")

    if db_type == "sqlite":
        logger.info("Mode: DEVELOPMENT (SQLite is not recommended for production)")
        logger.info("SQLite mode - tables will be auto-created via create_all()")

        # For SQLite, create tables automatically (bypass Alembic)
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ SQLite tables initialized successfully")
    else:
        logger.info("Mode: PRODUCTION")
        logger.info("PostgreSQL mode - using Alembic migrations")
        logger.info("Ensure migrations are up to date (run: make db-upgrade)")

    logger.info("=" * 60)

    yield

    # Shutdown: Clean up resources
    logger.info("Shutting down UFC Pokedex API")


app = FastAPI(
    title="UFC Pokedex API",
    version="0.1.0",
    description="REST API serving UFC fighter data scraped from UFCStats.",
    lifespan=lifespan,
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


# Middleware to add request ID to each request
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request for tracking."""
    request_id = str(uuid.uuid4())
    request_id_context.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors."""
    request_id = request_id_context.get()
    errors = [
        ValidationErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
            value=error.get("input"),
        )
        for error in exc.errors()
    ]

    logger.warning(
        f"Validation error for request {request_id} to {request.url.path}: {len(errors)} errors"
    )

    error_response = ValidationErrorResponse(
        error_type=ErrorType.VALIDATION_ERROR,
        message="Request validation failed",
        detail=f"{len(errors)} validation error(s)",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        timestamp=datetime.utcnow(),
        request_id=request_id,
        path=str(request.url.path),
        errors=errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    request_id = request_id_context.get()
    errors = [
        ValidationErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
            value=error.get("input"),
        )
        for error in exc.errors()
    ]

    logger.warning(
        f"Pydantic validation error for request {request_id} to {request.url.path}: {len(errors)} errors"
    )

    error_response = ValidationErrorResponse(
        error_type=ErrorType.VALIDATION_ERROR,
        message="Data validation failed",
        detail=f"{len(errors)} validation error(s)",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        timestamp=datetime.utcnow(),
        request_id=request_id,
        path=str(request.url.path),
        errors=errors,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(OperationalError)
@app.exception_handler(DBAPIError)
async def database_connection_exception_handler(request: Request, exc: Exception):
    """Handle database connection errors."""
    request_id = request_id_context.get()
    logger.error(
        f"Database connection error for request {request_id} to {request.url.path}: {str(exc)}"
    )

    error_response = ErrorResponse(
        error_type=ErrorType.DATABASE_ERROR,
        message="Database connection failed",
        detail="Unable to connect to the database. Please try again later.",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        timestamp=datetime.utcnow(),
        request_id=request_id,
        path=str(request.url.path),
        retry_after=5,
    )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(SQLAlchemyTimeoutError)
async def database_timeout_exception_handler(
    request: Request, exc: SQLAlchemyTimeoutError
):
    """Handle database query timeout errors."""
    request_id = request_id_context.get()
    logger.error(
        f"Database timeout error for request {request_id} to {request.url.path}: {str(exc)}"
    )

    error_response = ErrorResponse(
        error_type=ErrorType.TIMEOUT_ERROR,
        message="Database query timeout",
        detail="The database query took too long to complete. Please try again.",
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        timestamp=datetime.utcnow(),
        request_id=request_id,
        path=str(request.url.path),
        retry_after=3,
    )

    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(IntegrityError)
async def database_integrity_exception_handler(request: Request, exc: IntegrityError):
    """Handle database integrity constraint errors."""
    request_id = request_id_context.get()
    logger.error(
        f"Database integrity error for request {request_id} to {request.url.path}: {str(exc)}"
    )

    error_response = ErrorResponse(
        error_type=ErrorType.DATABASE_ERROR,
        message="Data integrity constraint violation",
        detail="The operation would violate a database constraint.",
        status_code=status.HTTP_409_CONFLICT,
        timestamp=datetime.utcnow(),
        request_id=request_id,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(DatabaseError)
async def database_generic_exception_handler(request: Request, exc: DatabaseError):
    """Handle generic database errors."""
    request_id = request_id_context.get()
    logger.error(
        f"Database error for request {request_id} to {request.url.path}: {str(exc)}"
    )

    error_response = ErrorResponse(
        error_type=ErrorType.DATABASE_ERROR,
        message="Database operation failed",
        detail="An error occurred while accessing the database. Please try again.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        timestamp=datetime.utcnow(),
        request_id=request_id,
        path=str(request.url.path),
        retry_after=3,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all other unhandled exceptions."""
    request_id = request_id_context.get()
    logger.exception(
        f"Unhandled exception for request {request_id} to {request.url.path}: {type(exc).__name__}"
    )

    error_response = ErrorResponse(
        error_type=ErrorType.INTERNAL_ERROR,
        message="Internal server error",
        detail=f"An unexpected error occurred: {type(exc).__name__}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        timestamp=datetime.utcnow(),
        request_id=request_id,
        path=str(request.url.path),
        retry_after=5,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode="json"),
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
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
app.include_router(fightweb.router, prefix="/fightweb", tags=["fightweb"])
