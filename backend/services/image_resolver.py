"""Helpers for resolving fighter image paths regardless of database state.

This module centralizes the logic for marrying a fighter's stored
``image_url`` with the filesystem cache under ``data/images``. When working
with the SQLite fallback database we often seed only core fighter metadata,
leaving the ``image_url`` column empty. The helpers here provide a graceful
fallback by checking the cached image directory and emitting a relative path
that the FastAPI app exposes at ``/images``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Final

# Directory that stores cached fighter images. We compute it relative to the
# repository root so the helper keeps working no matter where the application
# is launched from (tests, local dev server, background workers, etc.).
_IMAGE_ROOT: Final[Path] = (
    Path(__file__).resolve().parents[2] / "data" / "images" / "fighters"
)

# Order matters: we prefer JPEG assets first because the majority of our
# scraped library is JPEG, but we gracefully fall back to PNG and WebP variants
# for fighters whose imagery was exported in a different format.
_SUPPORTED_EXTENSIONS: Final[tuple[str, ...]] = (".jpg", ".jpeg", ".png", ".webp")

# Relative prefix exposed by the FastAPI static file mount. Returning paths that
# already include this prefix lets the frontend's existing ``resolveImageUrl``
# helper build a proper absolute URL.
_RELATIVE_PREFIX: Final[str] = "images/fighters"


def resolve_fighter_image(fighter_id: str, stored_path: str | None) -> str | None:
    """Return the best image reference for a fighter.

    Args:
        fighter_id: Primary key for the fighter record. Also used as the
            filename stem when checking the local cache.
        stored_path: The ``image_url`` column as persisted in the database.

    Returns:
        Either the original ``stored_path`` (when truthy), a relative path to a
        cached image (when discovered), or ``None`` if neither source yields an
        asset.

    The function first honors explicitly stored paths. When those are absent—
    which is common after seeding the lightweight SQLite database—it searches
    the local ``data/images/fighters`` directory for a matching file. Results
    The fallback filesystem lookup is cached via :func:`functools.lru_cache`
    to avoid redundant disk checks across large list responses.
    """

    if stored_path:
        return stored_path

    return _find_local_image(fighter_id)


@lru_cache(maxsize=2048)
def _find_local_image(fighter_id: str) -> str | None:
    """Locate a cached fighter image by trying the known extensions."""

    for extension in _SUPPORTED_EXTENSIONS:
        candidate = _IMAGE_ROOT / f"{fighter_id}{extension}"
        if candidate.exists():
            return f"{_RELATIVE_PREFIX}/{candidate.name}"
    return None


__all__ = ["resolve_fighter_image"]
