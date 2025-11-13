"""Tests for the image validation API flag filtering endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.sql import literal

from backend.api import image_validation


class _StubScalarResult:
    """Mimic SQLAlchemy's scalar result wrapper for asynchronous contexts."""

    def __init__(self, values: list[Any]) -> None:
        self._values = values

    def all(self) -> list[Any]:
        """Return the collected scalar values."""

        return list(self._values)


class _StubResult:
    """Provide the minimal interface consumed by ``get_fighters_by_flag``."""

    def __init__(
        self,
        *,
        scalars: list[Any] | None = None,
        scalar_one: Any | None = None,
        rows: list[Any] | None = None,
    ) -> None:
        self._scalar_values = scalars or []
        self._scalar_one = scalar_one
        self._rows = rows if rows is not None else self._scalar_values

    def scalars(self) -> _StubScalarResult:
        """Return a helper exposing ``all()`` over the configured values."""

        return _StubScalarResult(self._scalar_values)

    def scalar_one(self) -> Any:
        """Return the singular scalar result for count queries."""

        if self._scalar_one is None:
            raise RuntimeError("No scalar value configured for this stub result.")
        return self._scalar_one

    def __iter__(self):
        """Support iteration for duplicate lookup queries."""

        return iter(self._rows)


def _stub_fighter(
    fighter_id: str,
    name: str,
    *,
    flags: dict[str, Any] | None,
    quality: float | None = None,
    resolution: tuple[int | None, int | None] = (None, None),
) -> SimpleNamespace:
    """Create a light-weight fighter namespace used in stubbed query results."""

    width, height = resolution
    return SimpleNamespace(
        id=fighter_id,
        name=name,
        image_url=f"https://cdn.example.com/{fighter_id}.jpg",
        image_quality_score=quality,
        image_resolution_width=width,
        image_resolution_height=height,
        image_validation_flags=flags or {},
    )


@pytest.mark.asyncio
async def test_get_fighters_by_flag_filters_via_database_predicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The API should honour database-side filtering and response shaping."""

    fighters = [
        _stub_fighter(
            "flag-alpha",
            "Alpha Flag",
            flags={"low_resolution": {"width": 320, "height": 240}},
            resolution=(640, 480),
        ),
        _stub_fighter(
            "flag-beta",
            "Beta Flag",
            flags={"low_resolution": True},
        ),
    ]

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _StubResult(scalars=fighters),
            _StubResult(scalar_one=2),
        ]
    )

    observed_flags: list[str] = []

    def _record_flag(flag: str) -> Any:
        observed_flags.append(flag)
        return literal(True)

    monkeypatch.setattr(image_validation, "_build_flag_predicate", _record_flag)
    monkeypatch.setattr(
        image_validation,
        "resolve_fighter_image",
        lambda fighter_id, image_url: image_url,
    )

    response = await image_validation.get_fighters_by_flag(
        flag="low_resolution",
        limit=10,
        offset=0,
        session=session,
    )

    assert observed_flags == ["low_resolution"]
    assert response["total"] == 2
    assert response["count"] == 2
    assert response["limit"] == 10
    assert response["offset"] == 0
    assert [entry["name"] for entry in response["fighters"]] == [
        "Alpha Flag",
        "Beta Flag",
    ]
    assert response["fighters"][0]["flag_details"] == {"width": 320, "height": 240}
    assert response["fighters"][1]["flag_details"] is True


@pytest.mark.asyncio
async def test_get_fighters_by_flag_preserves_total_during_pagination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Paginated responses should retain the overall total count."""

    paginated = [
        _stub_fighter("flag-beta", "Beta Flag", flags={"low_resolution": True})
    ]

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _StubResult(scalars=paginated),
            _StubResult(scalar_one=2),
        ]
    )

    monkeypatch.setattr(
        image_validation,
        "_build_flag_predicate",
        lambda flag: literal(True),
    )
    monkeypatch.setattr(
        image_validation,
        "resolve_fighter_image",
        lambda fighter_id, image_url: image_url,
    )

    page = await image_validation.get_fighters_by_flag(
        flag="low_resolution",
        limit=1,
        offset=1,
        session=session,
    )

    assert page["total"] == 2
    assert page["count"] == 1
    assert page["limit"] == 1
    assert page["offset"] == 1
    assert [entry["name"] for entry in page["fighters"]] == ["Beta Flag"]
