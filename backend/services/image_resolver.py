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
from urllib.parse import urlsplit

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

# Historical seed data occasionally preserved absolute ``http://localhost`` URLs
# in the ``image_url`` column. When those values leak into API responses the
# production frontend attempts to load images from a developer machine.
# Normalising those artifacts into relative paths keeps responses deployment
# agnostic.
_LOCAL_HOSTNAMES: Final[frozenset[str]] = frozenset(
    {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
)


def _strip_local_origin(candidate: str) -> str | None:
    """Return ``candidate`` without a localhost-style origin when present."""

    parsed = urlsplit(candidate)
    hostname = (parsed.hostname or "").lower()
    if not hostname or hostname not in _LOCAL_HOSTNAMES:
        return None

    relative_path = parsed.path.lstrip("/")
    if not relative_path:
        return None

    if parsed.query:
        return f"{relative_path}?{parsed.query}"
    return relative_path


def _prepare_path(path: str | None) -> str | None:
    """Trim whitespace and collapse legacy localhost URLs into relative paths."""

    if not path:
        return None

    candidate = path.strip()
    if not candidate:
        return None

    normalized = _strip_local_origin(candidate)
    return normalized or candidate


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

    prepared_path = _prepare_path(stored_path)
    if prepared_path:
        return prepared_path

    return _find_local_image(fighter_id)


def resolve_fighter_image_cropped(
    fighter_id: str,
    stored_path: str | None,
    cropped_path: str | None,
) -> str | None:
    """Return the best cropped image reference for a fighter.

    This function prioritizes cropped (face-focused) images and is intended
    for use in contexts where a tight portrait is preferred, such as opponent
    images in fight history graphs.

    Args:
        fighter_id: Primary key for the fighter record.
        stored_path: The ``image_url`` column as persisted in the database.
        cropped_path: The ``cropped_image_url`` column from the database.

    Returns:
        Either the ``cropped_path`` (when available), falling back to the
        original image resolution logic if no cropped version exists.

    Priority:
        1. Cropped image from database (``cropped_path``)
        2. Cropped image from filesystem cache (``cropped/{fighter_id}.jpg``)
        3. Original image (via ``resolve_fighter_image``)
    """
    # First priority: database-stored cropped path
    prepared_cropped = _prepare_path(cropped_path)
    if prepared_cropped:
        return prepared_cropped

    # Second priority: check filesystem for cropped image
    cropped_local = _find_local_cropped_image(fighter_id)
    if cropped_local:
        return cropped_local

    # Fallback to original image
    return resolve_fighter_image(fighter_id, stored_path)


@lru_cache(maxsize=2048)
def _find_local_image(fighter_id: str) -> str | None:
    """Locate a cached fighter image by trying the known extensions."""

    for extension in _SUPPORTED_EXTENSIONS:
        candidate = _IMAGE_ROOT / f"{fighter_id}{extension}"
        if candidate.exists():
            return f"{_RELATIVE_PREFIX}/{candidate.name}"
    return None


@lru_cache(maxsize=2048)
def _find_local_cropped_image(fighter_id: str) -> str | None:
    """Locate a cached cropped fighter image by checking the cropped subdirectory."""

    # Cropped images are stored in data/images/fighters/cropped/
    cropped_dir = _IMAGE_ROOT / "cropped"

    for extension in _SUPPORTED_EXTENSIONS:
        candidate = cropped_dir / f"{fighter_id}{extension}"
        if candidate.exists():
            return f"{_RELATIVE_PREFIX}/cropped/{candidate.name}"
    return None


__all__ = ["resolve_fighter_image", "resolve_fighter_image_cropped"]
