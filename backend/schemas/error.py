"""Error response schemas for consistent error handling."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorType(str, Enum):
    """Types of errors that can occur."""

    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    DATABASE_ERROR = "database_error"
    NETWORK_ERROR = "network_error"
    INTERNAL_ERROR = "internal_error"
    TIMEOUT_ERROR = "timeout_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"


class ErrorResponse(BaseModel):
    """Standardized error response model."""

    error_type: ErrorType = Field(..., description="Category of error")
    message: str = Field(..., description="Human-readable error message")
    detail: str | None = Field(None, description="Additional error details or context")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When error occurred")
    request_id: str | None = Field(None, description="Unique request identifier for tracking")
    path: str | None = Field(None, description="Request path that caused the error")
    retry_after: int | None = Field(
        None, description="Seconds to wait before retrying (for rate limit/timeout errors)"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "error_type": "database_error",
                "message": "Database connection failed",
                "detail": "Unable to connect to PostgreSQL database at localhost:5432",
                "status_code": 503,
                "timestamp": "2025-11-03T10:30:00Z",
                "request_id": "req_abc123xyz",
                "path": "/fighters/",
                "retry_after": 5,
            }
        }


class ValidationErrorDetail(BaseModel):
    """Details for validation errors."""

    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    value: Any = Field(None, description="Value that failed validation")


class ValidationErrorResponse(ErrorResponse):
    """Extended error response for validation errors."""

    error_type: ErrorType = Field(default=ErrorType.VALIDATION_ERROR)
    errors: list[ValidationErrorDetail] = Field(
        default_factory=list, description="List of validation errors"
    )

    class Config:
        """Pydantic config."""

        json_schema_extra = {
            "example": {
                "error_type": "validation_error",
                "message": "Request validation failed",
                "detail": "Invalid query parameters provided",
                "status_code": 422,
                "timestamp": "2025-11-03T10:30:00Z",
                "request_id": "req_abc123xyz",
                "path": "/search/",
                "errors": [
                    {"field": "limit", "message": "Must be between 1 and 100", "value": 150},
                    {"field": "q", "message": "Query parameter is required", "value": None},
                ],
            }
        }
