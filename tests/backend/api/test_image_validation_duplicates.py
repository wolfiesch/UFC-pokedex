"""Tests for duplicate image API query behavior."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from backend.api.image_validation import get_duplicate_images


class _StubResult:
    """Result object compatible with the expectations of the API helpers."""

    def __init__(
        self, *, scalars: list[Any] | None = None, rows: list[Any] | None = None
    ) -> None:
        self._scalars = scalars or []
        self._rows = rows if rows is not None else self._scalars

    def scalars(self):
        class _Wrapper:
            def __init__(self, values: list[Any]) -> None:
                self._values = values

            def all(self) -> list[Any]:
                return list(self._values)

        return _Wrapper(self._scalars)

    def __iter__(self):
        return iter(self._rows)


@pytest.mark.asyncio
async def test_get_duplicate_images_aggregates_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure duplicate aggregation performs a single lookup and maps names correctly."""

    primary_one = SimpleNamespace(
        id="primary-1",
        name="Primary One",
        image_url="https://cdn.example.com/primary-1.jpg",
        image_quality_score=None,
        image_validation_flags={"potential_duplicates": ["dup-1", "dup-2", "dup-3"]},
    )
    primary_two = SimpleNamespace(
        id="primary-2",
        name="Primary Two",
        image_url="https://cdn.example.com/primary-2.jpg",
        image_quality_score=None,
        image_validation_flags={"potential_duplicates": ["dup-2", "dup-3", "missing"]},
    )

    duplicate_rows = [
        SimpleNamespace(id="dup-1", name="Duplicate One"),
        SimpleNamespace(id="dup-2", name="Duplicate Two"),
        SimpleNamespace(id="dup-3", name="Duplicate Three"),
    ]

    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _StubResult(scalars=[primary_one, primary_two]),
            _StubResult(rows=duplicate_rows),
        ]
    )

    monkeypatch.setattr(
        "backend.api.image_validation.resolve_fighter_image",
        lambda fighter_id, image_url: image_url,
    )

    response = await get_duplicate_images(limit=10, offset=0, session=session)

    # Two async ``execute`` invocations: one for the primary fighters and one for the duplicate lookup.
    assert session.execute.await_count == 2

    assert response["count"] == 2
    first_entry = response["fighters"][0]
    second_entry = response["fighters"][1]

    assert [dup["name"] for dup in first_entry["duplicates"]] == [
        "Duplicate One",
        "Duplicate Two",
        "Duplicate Three",
    ]
    assert [dup["name"] for dup in second_entry["duplicates"]] == [
        "Duplicate Two",
        "Duplicate Three",
        "Unknown Fighter",
    ]
