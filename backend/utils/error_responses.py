"""Helper functions for constructing structured API error responses.

Keeping response construction in one module avoids duplicated boilerplate in
each FastAPI exception handler.  The utilities below embed the request ID and a
timezone-aware timestamp automatically so that every payload shares a consistent
shape regardless of where the error originated.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from backend.schemas.error import (
    ErrorResponse,
    ErrorType,
    ValidationErrorDetail,
    ValidationErrorResponse,
)
from backend.utils.request_context import get_request_id

__all__ = [
    "build_error_response",
    "build_validation_error_response",
]


def _current_timestamp() -> datetime:
    """Return a timezone-aware timestamp for error payloads.

    Splitting the call into a tiny helper makes it trivial for unit tests to
    monkeypatch the clock and assert against deterministic values.
    """

    return datetime.now(UTC)


def build_validation_error_response(
    *,
    errors: Sequence[ValidationErrorDetail],
    message: str,
    detail: str,
    status_code: int,
    path: str,
    error_type: ErrorType = ErrorType.VALIDATION_ERROR,
    request_id: str | None = None,
) -> ValidationErrorResponse:
    """Construct a ``ValidationErrorResponse`` enriched with metadata.

    The ``errors`` iterable is eagerly converted to a list to shield callers
    from accidentally reusing a generator after the response has been created.
    """

    resolved_request_id = request_id or get_request_id()
    return ValidationErrorResponse(
        error_type=error_type,
        message=message,
        detail=detail,
        status_code=status_code,
        timestamp=_current_timestamp(),
        request_id=resolved_request_id,
        path=path,
        errors=list(errors),
    )


def build_error_response(
    *,
    error_type: ErrorType,
    message: str,
    detail: str,
    status_code: int,
    path: str,
    retry_after: int | None = None,
    request_id: str | None = None,
) -> ErrorResponse:
    """Construct a generic ``ErrorResponse`` enriched with metadata.

    ``retry_after`` remains optional so that call sites can omit it for
    non-retryable failures while still benefiting from centralised timestamp and
    request-id handling.
    """

    resolved_request_id = request_id or get_request_id()
    return ErrorResponse(
        error_type=error_type,
        message=message,
        detail=detail,
        status_code=status_code,
        timestamp=_current_timestamp(),
        request_id=resolved_request_id,
        path=path,
        retry_after=retry_after,
    )
