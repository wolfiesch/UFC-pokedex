"""Utilities for working with request-scoped context metadata.

The FastAPI application assigns a unique request identifier to every inbound
HTTP call.  Exposing tiny helper functions around the underlying ``ContextVar``
keeps that workflow consistent across middleware, exception handlers, and the
unit tests that need to stub request identifiers for deterministic assertions.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

__all__ = [
    "REQUEST_ID_CONTEXT",
    "clear_request_id",
    "get_request_id",
    "set_request_id",
]

# The context variable keeps track of the request identifier for the active
# coroutine.  FastAPI runs each request handler in its own task, which means the
# ``ContextVar`` provides an ergonomic and thread-safe way to store per-request
# metadata without relying on global mutable state.  These helpers are a single
# point of truth that both production code and tests can share.
REQUEST_ID_CONTEXT: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(request_id: str) -> Token[str]:
    """Persist the provided request identifier in the context variable.

    Returning the token allows advanced callers (primarily tests) to later
    ``reset`` the context back to its prior value once their assertions finish.
    The FastAPI middleware simply ignores the token because the lifecycle of a
    request naturally ends with the task completing.
    """

    return REQUEST_ID_CONTEXT.set(request_id)


def get_request_id() -> str:
    """Retrieve the current request identifier from the context variable.

    The helper centralises the default value (an empty string) so call sites do
    not have to repeat guard clauses whenever a request ID has not yet been
    assigned.
    """

    return REQUEST_ID_CONTEXT.get()


def clear_request_id(token: Token[str] | None = None) -> None:
    """Reset the request identifier to an empty string.

    Supplying a token mirrors the behaviour of ``ContextVar.reset`` and is most
    helpful when a test temporarily overrides the identifier.  If no token is
    supplied we fall back to explicitly setting an empty string so the context
    remains predictable for the next consumer.
    """

    if token is not None:
        REQUEST_ID_CONTEXT.reset(token)
    else:
        REQUEST_ID_CONTEXT.set("")
