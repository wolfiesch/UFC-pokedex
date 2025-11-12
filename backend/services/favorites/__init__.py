"""Favorites domain components split by responsibility.

This package exposes helpers that isolate persistence concerns from analytics
and caching utilities. Each module contains classes with explicit docstrings so
callers can quickly identify which behaviors they rely on.
"""

from .analytics import FavoritesAnalytics
from .cache import FavoritesCache
from .persistence import FavoritesPersistence

__all__ = [
    "FavoritesAnalytics",
    "FavoritesCache",
    "FavoritesPersistence",
]
