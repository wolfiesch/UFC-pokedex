"""Test suite package configuration.

This module ensures that the repository root is available on ``sys.path`` when
running the test suite. Some CI environments invoke :mod:`pytest` via the
console script entry point which does not always include the project root on
``sys.path``. Without that, absolute imports such as ``import scraper`` fail
even though the package exists locally.
"""

from __future__ import annotations

import sys
from pathlib import Path

# NOTE: ``Path(__file__).resolve()`` already resolves any symlinks, so we can
# reliably climb to the repository root regardless of how the tests are
# executed.
_REPO_ROOT: Path = Path(__file__).resolve().parent.parent


def _ensure_repo_on_path() -> None:
    """Insert the repository root to ``sys.path`` when it is missing.

    The helper performs an ``insert`` instead of ``append`` to make sure the
    local packages shadow any similarly named packages installed in the
    environment.
    """

    repo_root_str: str = str(_REPO_ROOT)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


_ensure_repo_on_path()
