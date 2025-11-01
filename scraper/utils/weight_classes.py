"""Utility helpers for mapping fighter weights to UFC-style divisions."""

from __future__ import annotations

import re
from typing import Final

_WEIGHT_RE: Final[re.Pattern[str]] = re.compile(r"(\d+(?:\.\d+)?)")

# Upper weight limits (in pounds) mapped to the associated division label.
_WEIGHT_CLASS_BOUNDS: Final[tuple[tuple[float, str], ...]] = (
    (115, "Strawweight"),
    (125, "Flyweight"),
    (135, "Bantamweight"),
    (145, "Featherweight"),
    (155, "Lightweight"),
    (170, "Welterweight"),
    (185, "Middleweight"),
    (205, "Light Heavyweight"),
    (265, "Heavyweight"),
)


def parse_weight_lbs(weight_text: str | None) -> float | None:
    """Extract the numeric pounds value from a weight string like ``185 lbs.``."""
    if not weight_text:
        return None

    match = _WEIGHT_RE.search(weight_text.replace(",", ""))
    if not match:
        return None

    try:
        value = float(match.group(1))
    except ValueError:
        return None

    if value <= 0:
        return None
    return value


def weight_to_division(weight_text: str | None) -> str | None:
    """Derive an approximate division label from a fighter's listed weight."""
    weight_lbs = parse_weight_lbs(weight_text)
    if weight_lbs is None:
        return None

    for upper_limit, division in _WEIGHT_CLASS_BOUNDS:
        if weight_lbs <= upper_limit:
            return division

    return "Super Heavyweight"
