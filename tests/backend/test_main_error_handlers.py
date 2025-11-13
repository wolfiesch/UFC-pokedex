"""Tests asserting ``backend.main`` exception handlers delegate to helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import DBAPIError
from starlette.datastructures import Headers

import backend.main as backend_main
from backend.schemas.error import ErrorResponse, ErrorType, ValidationErrorResponse
from backend.utils.request_context import clear_request_id, set_request_id


def _build_request(path: str = "/resource") -> Request:
    """Create a minimal ``Request`` suitable for invoking handlers."""

    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": Headers().raw,
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_validation_exception_handler_uses_builder(monkeypatch):
    """Ensure request validation handler delegates to the helper utility."""

    token = set_request_id("req-1")
    request = _build_request("/fighters")
    exc = RequestValidationError(
        [
            {
                "loc": ["query", "name"],
                "msg": "Invalid",
                "input": "John",
            }
        ]
    )

    called: dict[str, object] = {}

    def fake_builder(**kwargs):
        called["kwargs"] = kwargs
        return ValidationErrorResponse(
            error_type=ErrorType.VALIDATION_ERROR,
            message="Request validation failed",
            detail="1 validation error(s)",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            request_id="req-1",
            path="/fighters",
            errors=[],
        )

    monkeypatch.setattr(backend_main, "build_validation_error_response", fake_builder)

    try:
        response = await backend_main.validation_exception_handler(request, exc)
    finally:
        clear_request_id(token)

    assert called["kwargs"]["path"] == "/fighters"
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    json_content = json.loads(response.body.decode())
    assert json_content["message"] == "Request validation failed"


@pytest.mark.asyncio
async def test_database_connection_exception_handler_uses_builder(monkeypatch):
    """Ensure database connection handler delegates to the helper utility."""

    token = set_request_id("req-2")
    request = _build_request("/db")
    exc = DBAPIError("statement", {}, Exception("boom"))

    called: dict[str, object] = {}

    def fake_builder(**kwargs):
        called["kwargs"] = kwargs
        return ErrorResponse(
            error_type=ErrorType.DATABASE_ERROR,
            message="Database connection failed",
            detail="Unable to connect",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            timestamp=datetime(2024, 1, 1, tzinfo=UTC),
            request_id="req-2",
            path="/db",
            retry_after=5,
        )

    monkeypatch.setattr(backend_main, "build_error_response", fake_builder)

    try:
        response = await backend_main.database_connection_exception_handler(
            request, exc
        )
    finally:
        clear_request_id(token)

    assert called["kwargs"]["path"] == "/db"
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    json_content = json.loads(response.body.decode())
    assert json_content["message"] == "Database connection failed"
