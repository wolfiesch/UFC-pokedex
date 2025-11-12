"""Utilities for looking up gym locations from the curated CSV mapping."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class GymLocation:
    """Normalized representation of a training gym location."""

    name: str
    city: str | None = None
    country: str | None = None
    iso2: str | None = None


def _normalize(name: str) -> str:
    """Return a normalized key for case/spacing insensitive lookups."""

    return re.sub(r"[^a-z0-9]", "", name.lower())


@lru_cache(maxsize=1)
def _load_mapping(csv_path: str = "data/manual/gym_locations.csv") -> dict[str, GymLocation]:
    """Load the curated gym -> location mapping once per process."""

    path = Path(csv_path)
    if not path.exists():
        return {}

    mapping: dict[str, GymLocation] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            gym_name = (row.get("gym_name") or "").strip()
            if not gym_name:
                continue
            location = GymLocation(
                name=gym_name,
                city=(row.get("city") or "").strip() or None,
                country=(row.get("country") or "").strip() or None,
                iso2=(row.get("iso2") or "").strip().upper() or None,
            )
            for key in {gym_name, _normalize(gym_name)}:
                mapping[key] = location
    return mapping


def _candidate_keys(name: str) -> Iterable[str]:
    """Generate possible keys that might match the curated CSV."""

    yield name
    yield _normalize(name)
    if name.endswith(" HQ"):
        yield name[:-3].strip()
        yield _normalize(name[:-3])


def resolve_gym_location(name: str | None) -> GymLocation | None:
    """Return the curated location info for ``name`` if available."""

    if not name:
        return None

    mapping = _load_mapping()
    for key in _candidate_keys(name.strip()):
        if key in mapping:
            return mapping[key]

    return None


__all__ = ["GymLocation", "resolve_gym_location"]
