import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy.exc import (
    DatabaseError,
    DBAPIError,
    IntegrityError,
    OperationalError,
)
from sqlalchemy.exc import (
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.db.connection import (
    get_database_type as _connection_get_database_type,
)
from backend.db.connection import (
    get_database_url as _connection_get_database_url,
)
from backend.db.connection import (
    get_engine as _connection_get_engine,
)

from .api import (
    events,
    favorites,
    fighters,
    fightweb,
    image_validation,
    odds,
    rankings,
    search,
    stats,
)
from .schemas.error import ErrorType, ValidationErrorDetail
from .utils.error_responses import (
    build_error_response,
    build_validation_error_response,
)
from .utils.request_context import get_request_id, set_request_id

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _validate_environment() -> None:
    """Validate environment variables at startup and log warnings for missing optional vars."""
    warnings: list[str] = []

    # Check optional but recommended environment variables
    if not os.getenv("REDIS_URL"):
        warnings.append(
            "REDIS_URL is not set - caching will use in-memory fallback "
            "(performance may be degraded)"
        )

    if not os.getenv("CORS_ALLOW_ORIGINS"):
        warnings.append(
            "CORS_ALLOW_ORIGINS is not set - using default localhost origins only "
            "(may cause CORS issues in production)"
        )

    # Log warnings if any
    if warnings:
        logger.warning("=" * 60)
        logger.warning("Environment Configuration Warnings:")
        for warning in warnings:
            logger.warning(f"  • {warning}")
        logger.warning("=" * 60)


def validate_environment() -> None:
    """Public wrapper ensuring CLI tools can trigger configuration validation."""

    _validate_environment()


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


def get_database_type() -> str:
    """Return the configured database flavor.

    The helper simply proxies ``backend.db.connection.get_database_type`` while
    keeping an explicit module-level symbol that our test-suite can patch.  The
    indirection keeps the production implementation in one place yet allows
    dependency injection without touching private attributes.
    """

    return _connection_get_database_type()


def get_database_url() -> str:
    """Return the database URL currently in use.

    A dedicated wrapper with a descriptive docstring clarifies *why* the helper
    exists in this module: FastAPI's lifespan hooks and the accompanying unit
    tests expect to patch ``backend.main.get_database_url`` directly.  Surfacing
    the function at module scope avoids repeated local imports and keeps
    observability behaviour—such as preflight logging—centralised in this file.
    """

    return _connection_get_database_url()


def get_engine() -> AsyncEngine:
    """Retrieve (and lazily create) the shared SQLAlchemy async engine.

    The wrapper preserves the public contract of ``backend.db.connection`` while
    providing a stable attribute for unit tests to stub.  Returning the
    ``AsyncEngine`` keeps type-checkers honest and improves developer ergonomics
    when navigating usages.
    """

    return _connection_get_engine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Validate configuration as soon as the application begins starting up so the
    # same warnings previously emitted at import time remain visible to operators.
    validate_environment()

    db_type = get_database_type()
    db_url = get_database_url()
    sanitized_url = _sanitize_database_url(db_url)

    # Preflight logging
    logger.info("=" * 60)
    logger.info("UFC Pokedex API - Database Preflight Check")
    logger.info("=" * 60)
    logger.info(f"Database Type: {db_type.upper()}")
    logger.info(f"Database URL: {sanitized_url}")

    if db_type != "postgresql":
        raise RuntimeError(
            "Unsupported database type detected. Configure DATABASE_URL for "
            "PostgreSQL before starting the API."
        )

    logger.info("Mode: PRODUCTION")
    logger.info("PostgreSQL mode - using Alembic migrations")
    logger.info("Ensure migrations are up to date (run: make db-upgrade)")

    logger.info("=" * 60)

    # NEW: Warmup connections
    from backend.warmup import warmup_all

    await warmup_all(
        resolve_db_type=get_database_type,
        resolve_engine=get_engine,
    )

    yield

    # Shutdown: Clean up resources
    from backend.cache import close_redis

    logger.info("Shutting down UFC Pokedex API")
    await close_redis()


app = FastAPI(
    title="UFC Pokedex API",
    version="0.1.0",
    description="REST API serving UFC fighter data scraped from UFCStats.",
    lifespan=lifespan,
    redirect_slashes=False,  # Disable automatic trailing slash redirects
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
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
    if origin.strip()
]


def _extract_origin(
    url: str | None,
    *,
    default_scheme: str | None = None,
) -> str | None:
    """Normalise ``url`` into a canonical CORS origin string.

    Deployment platforms frequently expose hostnames without a URL scheme (for
    example ``VERCEL_URL=ufc-pokedex.vercel.app``).  The previous
    implementation rejected those values outright which meant the backend
    defaulted to localhost-only CORS allow-lists unless operators manually set
    ``CORS_ALLOW_ORIGINS``.  In production this manifested as a seemingly blank
    frontend because browsers blocked cross-origin requests to the API.

    The helper now accepts optional ``default_scheme`` hints allowing us to
    coerce bare hostnames into ``https://`` origins while still validating full
    URLs.  The returned value is safe to pass directly to FastAPI's
    ``allow_origins`` configuration.
    """

    if not url:
        return None

    raw_value = url.strip()
    if not raw_value:
        return None

    candidates: list[str] = [raw_value]

    if "://" not in raw_value:
        schemes: list[str]
        if default_scheme:
            schemes = [default_scheme]
        else:
            schemes = ["https", "http"]
        candidates.extend(f"{scheme}://{raw_value}" for scheme in schemes)

    for candidate in candidates:
        try:
            parsed = urlsplit(candidate)
        except ValueError:
            continue

        if not parsed.scheme or not parsed.netloc:
            continue

        normalized = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        if normalized:
            return normalized

    logger.debug("Ignoring invalid CORS origin candidate: %s", raw_value)
    return None


def _split_env_values(value: str | None) -> list[str]:
    """Split comma separated environment variables into trimmed entries."""

    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _combine_origins(*origin_groups: list[str]) -> list[str]:
    """Merge origins preserving order and removing duplicates."""
    seen: set[str] = set()
    combined: list[str] = []
    for group in origin_groups:
        for origin in group:
            normalized = origin.rstrip("/")
            if normalized and normalized not in seen:
                seen.add(normalized)
                combined.append(normalized)
    return combined


_ORIGIN_ENVIRONMENT_VARIABLES: tuple[tuple[str, str | None], ...] = (
    ("PUBLIC_FRONTEND_URL", None),
    ("PUBLIC_SITE_URL", None),
    ("NEXT_PUBLIC_SITE_URL", None),
    ("NEXT_PUBLIC_FRONTEND_URL", None),
    ("NEXT_PUBLIC_WEB_URL", None),
    ("NEXT_PUBLIC_WEBSITE_URL", None),
    ("NEXT_PUBLIC_APP_URL", None),
    ("NEXT_PUBLIC_CLIENT_URL", None),
    ("NEXT_PUBLIC_API_BASE_URL", None),
    ("NEXT_PUBLIC_VERCEL_URL", "https"),
    ("VERCEL_URL", "https"),
    ("VERCEL_BRANCH_URL", "https"),
    ("VERCEL_PROJECT_PRODUCTION_URL", "https"),
    ("CF_PAGES_URL", "https"),
    ("NETLIFY_URL", "https"),
    ("RENDER_EXTERNAL_URL", "https"),
    ("RAILWAY_STATIC_URL", "https"),
    ("RAILWAY_PUBLIC_DOMAIN", "https"),
)


def _collect_derived_origins() -> list[str]:
    """Derive additional CORS origins from well-known deployment variables."""

    derived: list[str] = []
    for env_var, default_scheme in _ORIGIN_ENVIRONMENT_VARIABLES:
        values = _split_env_values(os.getenv(env_var))
        for value in values:
            origin = _extract_origin(value, default_scheme=default_scheme)
            if origin:
                derived.append(origin)
    return derived


derived_origins = _collect_derived_origins()

if extra_origins:
    allow_origins = _combine_origins(default_origins, extra_origins, derived_origins)
else:
    allow_origins = _combine_origins(default_origins, derived_origins)

cors_origin_regex = os.getenv("CORS_ALLOW_ORIGIN_REGEX") or None

if allow_origins:
    logger.info("Configured CORS allow_origins: %s", ", ".join(allow_origins))
if cors_origin_regex:
    logger.info("Configured CORS allow_origin_regex: %s", cors_origin_regex)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex=cors_origin_regex,
)


# Middleware to add request ID to each request
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request for tracking."""
    request_id = str(uuid.uuid4())
    set_request_id(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle FastAPI request validation errors."""
    errors = [
        ValidationErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
            value=error.get("input"),
        )
        for error in exc.errors()
    ]

    logger.warning(
        "Validation error for request %s to %s: %s errors",
        get_request_id(),
        request.url.path,
        len(errors),
    )

    error_response = build_validation_error_response(
        message="Request validation failed",
        detail=f"{len(errors)} validation error(s)",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    errors = [
        ValidationErrorDetail(
            field=".".join(str(loc) for loc in error["loc"]),
            message=error["msg"],
            value=error.get("input"),
        )
        for error in exc.errors()
    ]

    logger.warning(
        "Pydantic validation error for request %s to %s: %s errors",
        get_request_id(),
        request.url.path,
        len(errors),
    )

    error_response = build_validation_error_response(
        message="Data validation failed",
        detail=f"{len(errors)} validation error(s)",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    logger.error(
        "Database connection error for request %s to %s: %s",
        get_request_id(),
        request.url.path,
        str(exc),
    )

    error_response = build_error_response(
        error_type=ErrorType.DATABASE_ERROR,
        message="Database connection failed",
        detail="Unable to connect to the database. Please try again later.",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
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
    logger.error(
        "Database timeout error for request %s to %s: %s",
        get_request_id(),
        request.url.path,
        str(exc),
    )

    error_response = build_error_response(
        error_type=ErrorType.TIMEOUT_ERROR,
        message="Database query timeout",
        detail="The database query took too long to complete. Please try again.",
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
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
    logger.error(
        "Database integrity error for request %s to %s: %s",
        get_request_id(),
        request.url.path,
        str(exc),
    )

    error_response = build_error_response(
        error_type=ErrorType.DATABASE_ERROR,
        message="Data integrity constraint violation",
        detail="The operation would violate a database constraint.",
        status_code=status.HTTP_409_CONFLICT,
        path=str(request.url.path),
    )

    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_response.model_dump(mode="json"),
    )


@app.exception_handler(DatabaseError)
async def database_generic_exception_handler(request: Request, exc: DatabaseError):
    """Handle generic database errors."""
    logger.error(
        "Database error for request %s to %s: %s",
        get_request_id(),
        request.url.path,
        str(exc),
    )

    error_response = build_error_response(
        error_type=ErrorType.DATABASE_ERROR,
        message="Database operation failed",
        detail="An error occurred while accessing the database. Please try again.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
    logger.exception(
        "Unhandled exception for request %s to %s: %s",
        get_request_id(),
        request.url.path,
        type(exc).__name__,
    )

    error_response = build_error_response(
        error_type=ErrorType.INTERNAL_ERROR,
        message="Internal server error",
        detail=f"An unexpected error occurred: {type(exc).__name__}",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
app.include_router(rankings.router, prefix="/rankings", tags=["rankings"])
app.include_router(odds.router, prefix="/odds", tags=["odds"])
app.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
app.include_router(fightweb.router, prefix="/fightweb", tags=["fightweb"])
app.include_router(
    image_validation.router, prefix="/image-validation", tags=["image-validation"]
)
