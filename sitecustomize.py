"""Runtime customisations used during test execution.

This module provides a lightweight fallback stub for the optional ``redis``
dependency. The production application installs ``redis`` via
``pyproject.toml``, but our execution environment for automated tests may omit
that wheel. Importing ``sitecustomize`` allows us to hook into Python start-up
and register the stub exactly once when the dependency is absent.
"""

from __future__ import annotations

import importlib.util
import sys
from types import ModuleType
from typing import Any, AsyncIterator, Final


def _redis_is_available() -> bool:
    """Return ``True`` when the real ``redis`` package can be imported."""

    spec = importlib.util.find_spec("redis")
    return spec is not None


class _StubRedisConnectionError(ConnectionError):
    """Exception raised by the stub client to emulate Redis failures."""


class _StubRedis:
    """Minimal async Redis client used when the dependency is missing."""

    def __init__(self) -> None:
        # No connection is ever established; the stub only signals failures.
        self._connected: Final[bool] = False

    @classmethod
    def from_url(cls, *_args: Any, **_kwargs: Any) -> "_StubRedis":
        """Return a client instance regardless of the provided parameters."""

        return cls()

    async def ping(self) -> None:
        """Simulate a ping operation by raising a connection error."""

        raise _StubRedisConnectionError("Redis client is unavailable")

    async def get(self, _key: str) -> Any:
        """Simulate ``GET`` by raising a connection error."""

        raise _StubRedisConnectionError("Redis client is unavailable")

    async def set(self, _key: str, _value: Any, *, ex: int | None = None) -> None:
        """Simulate ``SET`` by raising a connection error."""

        raise _StubRedisConnectionError("Redis client is unavailable")

    async def delete(self, *_keys: str) -> None:
        """Simulate ``DEL`` by raising a connection error."""

        raise _StubRedisConnectionError("Redis client is unavailable")

    async def scan_iter(self, *, match: str | None = None) -> AsyncIterator[str]:
        """Simulate ``SCAN`` by raising a connection error."""

        raise _StubRedisConnectionError("Redis client is unavailable")
        yield  # pragma: no cover - generator formality

    async def aclose(self) -> None:
        """Provide an awaitable close method for graceful shutdown calls."""

        return None


def _install_stub() -> None:
    """Register the stub ``redis`` module hierarchy in ``sys.modules``."""

    redis_module = ModuleType("redis")
    exceptions_module = ModuleType("redis.exceptions")
    asyncio_module = ModuleType("redis.asyncio")

    exceptions_module.ConnectionError = _StubRedisConnectionError  # type: ignore[attr-defined]
    asyncio_module.Redis = _StubRedis  # type: ignore[attr-defined]

    redis_module.exceptions = exceptions_module  # type: ignore[attr-defined]
    redis_module.asyncio = asyncio_module  # type: ignore[attr-defined]

    sys.modules.setdefault("redis", redis_module)
    sys.modules.setdefault("redis.exceptions", exceptions_module)
    sys.modules.setdefault("redis.asyncio", asyncio_module)


if not _redis_is_available():
    _install_stub()

__all__ = [
    "_StubRedisConnectionError",
]
