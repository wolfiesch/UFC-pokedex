"""Pytest configuration helpers for the UFC Pokedex project.

The ``pytest`` plugin system automatically imports ``tests.conftest``. We use
that behavior to ensure the repository root is present on ``sys.path`` before
any test modules import application code.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

import pytest

from tests import _ensure_repo_on_path


def _ensure_redis_stub_loaded() -> None:
    """Import ``sitecustomize`` so the Redis compatibility shim is registered."""

    try:
        __import__("sitecustomize")
    except ModuleNotFoundError:
        # The shim only exists inside the kata runner where optional
        # dependencies are omitted. When running in a fully provisioned
        # environment the import naturally fails and can be ignored.
        return None
    return None


class _AsyncioCompatPlugin:
    """Minimal fallback runner for ``async def`` tests."""

    def pytest_pyfunc_call(self, pyfuncitem: Any) -> bool | None:
        """Execute coroutine-based tests when ``pytest-asyncio`` is unavailable.

        The plugin mirrors a tiny subset of ``pytest-asyncio`` by eagerly
        running the collected test coroutine via :func:`asyncio.run`. Returning
        ``True`` tells :mod:`pytest` that the call was fully handled so the
        default sync runner is skipped.
        """

        test_function = pyfuncitem.obj
        if inspect.iscoroutinefunction(test_function):
            asyncio.run(test_function(**pyfuncitem.funcargs))
            return True
        return None


def pytest_configure(config: pytest.Config) -> None:
    """Hook executed by pytest prior to running any tests."""

    _ensure_repo_on_path()
    _ensure_redis_stub_loaded()

    # ``pytest-asyncio`` registers itself under the ``asyncio`` plugin name. In
    # lean environments (such as the kata runner) the dependency might be
    # missing, so we provide a graceful fallback to keep async tests working.
    if not config.pluginmanager.hasplugin("asyncio"):
        config.addinivalue_line(
            "markers",
            "asyncio: fallback marker handled by tests.conftest when pytest-asyncio is absent",
        )
        config.pluginmanager.register(_AsyncioCompatPlugin(), name="asyncio_compat")
