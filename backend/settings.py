"""Centralized configuration management for the UFC Pokedex backend."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field, PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables defined in a local .env file before instantiating the
# settings singleton. Keeping this call inside the module ensures that any consumer
# importing :mod:`backend.settings` enjoys parity with ``load_dotenv`` previously
# executed in ``backend.main``.
load_dotenv()

# -- Application-wide constants -------------------------------------------------

DEFAULT_SQLITE_DATABASE_URL = "sqlite+aiosqlite:///./data/app.db"
POSTGRES_ASYNC_PREFIX = "postgresql+psycopg://"
POSTGRES_SYNC_PREFIXES = ("postgres://", "postgresql://")
DEFAULT_REDIS_URL = "redis://localhost:6379/0"
DEFAULT_REDIS_RETRY_BACKOFF_SECONDS = 30.0
DEFAULT_LOG_LEVEL = "INFO"


def _normalize_origin(origin: str) -> str:
    """Return the origin stripped of whitespace and trailing slashes."""

    return origin.strip().rstrip("/")


def _extract_origin(url: str | None) -> str | None:
    """Return the scheme + netloc portion of ``url`` when valid."""

    if not url:
        return None

    try:
        from urllib.parse import urlsplit

        parsed = urlsplit(url.strip())
    except ValueError:
        return None

    if not parsed.scheme or not parsed.netloc:
        return None

    return f"{parsed.scheme}://{parsed.netloc}"


class AppSettings(BaseSettings):
    """Typed configuration surface built on top of ``pydantic-settings``.

    The class encapsulates commonly accessed environment variables and exposes
    higher-level helpers (for example, normalized database URLs) that downstream
    modules can reuse without repeating parsing logic.  Additional properties keep
    the implementation verbose, favouring explicit naming, docstrings, and
    type hints to match the repository's contributor guidelines.
    """

    _explicit_database_url: bool = PrivateAttr(default=False)
    _explicit_redis_url: bool = PrivateAttr(default=False)
    _explicit_cors_allow_origins: bool = PrivateAttr(default=False)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(
        self, **values: object
    ) -> None:  # noqa: D401 - short override explanation
        """Capture explicit overrides prior to delegating to ``BaseSettings``."""

        normalized_keys = {str(key).lower() for key in values}
        super().__init__(**values)
        self._explicit_database_url = "database_url" in normalized_keys
        self._explicit_redis_url = "redis_url" in normalized_keys
        self._explicit_cors_allow_origins = (
            "cors_allow_origins_raw" in normalized_keys
            or "cors_allow_origins" in normalized_keys
        )
        redis_env = os.getenv("REDIS_URL")
        if redis_env is not None and redis_env.strip():
            self._explicit_redis_url = True
        cors_env = os.getenv("CORS_ALLOW_ORIGINS")
        if cors_env is not None and cors_env.strip():
            self._explicit_cors_allow_origins = True

    database_url: str | None = Field(
        default=None,
        alias="DATABASE_URL",
        description=(
            "Full SQLAlchemy-compatible database URL. Postgres URLs supplied in"
            " sync format (postgres:// or postgresql://) are coerced into the"
            " async psycopg driver string at runtime."
        ),
    )
    use_sqlite: bool = Field(
        default=False,
        alias="USE_SQLITE",
        description=(
            "Force SQLite usage regardless of DATABASE_URL. Helpful for local"
            " development and test suites that do not require PostgreSQL."
        ),
    )
    redis_url: str = Field(
        default=DEFAULT_REDIS_URL,
        alias="REDIS_URL",
        description=(
            "Redis connection string consumed by cache utilities. Defaults to a"
            " localhost instance so the application remains usable without an"
            " explicit environment variable."
        ),
    )
    redis_retry_backoff_seconds: float = Field(
        default=DEFAULT_REDIS_RETRY_BACKOFF_SECONDS,
        alias="REDIS_RETRY_BACKOFF_SECONDS",
        description=("Cooldown duration applied after Redis connection failures."),
    )
    cors_allow_origins_raw: str | None = Field(
        default=None,
        alias="CORS_ALLOW_ORIGINS",
        description=(
            "Comma-separated list of additional CORS origins supplied via environment variable."
        ),
    )
    cors_allow_origin_regex: str | None = Field(
        default=None,
        alias="CORS_ALLOW_ORIGIN_REGEX",
        description=(
            "Optional regular expression evaluated by FastAPI's CORS middleware."
        ),
    )
    log_level: str = Field(
        default=DEFAULT_LOG_LEVEL,
        alias="LOG_LEVEL",
        description="Root logging level (e.g. INFO, DEBUG, WARNING).",
    )
    public_frontend_url: str | None = Field(
        default=None,
        alias="PUBLIC_FRONTEND_URL",
        description="Primary externally reachable frontend URL used for CORS hints.",
    )
    next_public_site_url: str | None = Field(
        default=None,
        alias="NEXT_PUBLIC_SITE_URL",
        description="Next.js public site URL leveraged when deriving CORS origins.",
    )
    next_public_api_base_url: str | None = Field(
        default=None,
        alias="NEXT_PUBLIC_API_BASE_URL",
        description="Client-facing API base URL utilised for derived origin logic.",
    )
    slow_query_threshold: float = Field(
        default=0.1,
        alias="SLOW_QUERY_THRESHOLD",
        description=(
            "Threshold in seconds after which queries are considered slow for"
            " monitoring instrumentation."
        ),
    )

    @property
    def resolved_database_url(self) -> str:
        """Return the async-compatible database URL after applying fallbacks."""

        if self.use_sqlite:
            return DEFAULT_SQLITE_DATABASE_URL

        if not self.database_url:
            return DEFAULT_SQLITE_DATABASE_URL

        url = self.database_url

        for prefix in POSTGRES_SYNC_PREFIXES:
            if url.startswith(prefix):
                return url.replace(prefix, POSTGRES_ASYNC_PREFIX, 1)

        if url.startswith(POSTGRES_ASYNC_PREFIX):
            return url

        raise RuntimeError(
            f"Expected a PostgreSQL connection string or SQLite fallback, received: {url}"
        )

    @property
    def database_type(self) -> str:
        """Return ``sqlite`` when using SQLite otherwise ``postgresql``."""

        url = self.resolved_database_url
        if url.startswith("sqlite"):
            return "sqlite"
        return "postgresql"

    @property
    def cors_allow_origins(self) -> list[str]:
        """Return normalised CORS origins supplied via environment variables."""

        if not self.cors_allow_origins_raw:
            return []

        origins = [
            _normalize_origin(origin)
            for origin in self.cors_allow_origins_raw.split(",")
            if origin.strip()
        ]
        return [origin for origin in origins if origin]

    @property
    def derived_cors_origins(self) -> list[str]:
        """Return origins inferred from public-facing configuration variables."""

        candidates = (
            self.public_frontend_url,
            self.next_public_site_url,
            self.next_public_api_base_url,
        )
        derived = [_extract_origin(candidate) for candidate in candidates]
        return [origin for origin in derived if origin]

    @property
    def log_level_numeric(self) -> int:
        """Translate ``log_level`` into the numeric constant expected by logging."""

        candidate = logging.getLevelName(self.log_level.upper())
        if isinstance(candidate, int):
            return candidate
        return logging.INFO

    def optional_config_warnings(self) -> list[str]:
        """Return human-readable warnings for unset optional configuration."""

        warnings: list[str] = []

        if not self._explicit_redis_url and self.redis_url == DEFAULT_REDIS_URL:
            warnings.append(
                "REDIS_URL is not set - caching will use in-memory fallback "
                "(performance may be degraded)"
            )

        if not self._explicit_cors_allow_origins and not self.cors_allow_origins:
            warnings.append(
                "CORS_ALLOW_ORIGINS is not set - using default localhost origins only "
                "(may cause CORS issues in production)"
            )

        return warnings


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return a cached instance of :class:`AppSettings`."""

    return AppSettings()


# Expose a module-level singleton mirroring the previous pattern used in the code
# base. The getter remains available for tests that prefer dependency injection.
settings = get_settings()

__all__ = [
    "AppSettings",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_REDIS_RETRY_BACKOFF_SECONDS",
    "DEFAULT_REDIS_URL",
    "DEFAULT_SQLITE_DATABASE_URL",
    "POSTGRES_ASYNC_PREFIX",
    "POSTGRES_SYNC_PREFIXES",
    "get_settings",
    "settings",
]
