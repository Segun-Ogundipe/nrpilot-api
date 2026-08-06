"""Structured logging utilities and helpers."""

from collections.abc import Callable
from typing import Any, TypeVar

import structlog

F = TypeVar("F", bound=Callable[..., Any])
logger = structlog.get_logger(__name__)


def bind_context(**context: Any) -> None:
    """
    Bind contextual information to all subsequent logs in the current context.

    Usage:
        bind_context(user_id="123", org_id="456")
        logger.info("event_occurred")  # Will include user_id and org_id
    """
    structlog.contextvars.bind_contextvars(**context)


def unbind_context(*keys: str) -> None:
    """
    Remove specific context variables.

    Usage:
        unbind_context("user_id", "org_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all context variables."""
    structlog.contextvars.clear_contextvars()


def get_logger(name: str) -> Any:
    """
    Get a logger instance for the given name.

    Args:
        name: The logger name

    Returns:
        A structlog logger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("event", key="value")
    """
    return structlog.get_logger(name)
