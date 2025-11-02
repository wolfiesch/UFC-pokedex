"""Pytest configuration helpers for the UFC Pokedex project.

The ``pytest`` plugin system automatically imports ``tests.conftest``. We use
that behavior to ensure the repository root is present on ``sys.path`` before
any test modules import application code.
"""

from __future__ import annotations

from tests import _ensure_repo_on_path


def pytest_configure() -> None:
    """Hook executed by pytest prior to running any tests."""

    _ensure_repo_on_path()
