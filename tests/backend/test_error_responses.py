"""Tests covering the helper utilities that construct error responses."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from backend.schemas.error import ErrorType, ValidationErrorDetail
from backend.utils import error_responses
from backend.utils.error_responses import (
    build_error_response,
    build_validation_error_response,
)
from backend.utils.request_context import clear_request_id, set_request_id


def _freeze_timestamp(monkeypatch: pytest.MonkeyPatch, fixed: datetime) -> None:
    """Override ``_current_timestamp`` to yield the provided ``datetime``."""

    monkeypatch.setattr(error_responses, "_current_timestamp", lambda: fixed)


def test_build_validation_error_response_includes_context_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The helper should embed the request ID and a timezone-aware timestamp."""

    fixed_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    _freeze_timestamp(monkeypatch, fixed_timestamp)

    token = set_request_id("req-123")
    try:
        errors = [
            ValidationErrorDetail(
                field="body.name",
                message="Field required",
                value=None,
            )
        ]

        response = build_validation_error_response(
            message="Request validation failed",
            detail="1 validation error(s)",
            status_code=422,
            path="/fighters",
            errors=errors,
        )

        assert response.request_id == "req-123"
        assert response.timestamp == fixed_timestamp
        assert response.errors == errors
    finally:
        clear_request_id(token)


def test_build_error_response_allows_request_id_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit request identifiers should take precedence over context values."""

    fixed_timestamp = datetime(2024, 1, 2, 6, 30, 0, tzinfo=UTC)
    _freeze_timestamp(monkeypatch, fixed_timestamp)

    clear_request_id()

    response = build_error_response(
        error_type=ErrorType.INTERNAL_ERROR,
        message="Something went wrong",
        detail="Unexpected condition",
        status_code=500,
        path="/health",
        retry_after=None,
        request_id="override-id",
    )

    assert response.request_id == "override-id"
    assert response.timestamp == fixed_timestamp
    assert response.retry_after is None
