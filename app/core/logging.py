"""Structured logging utilities and helpers."""

import functools
import time
from collections.abc import Callable
from typing import Any, TypeVar

import structlog

F = TypeVar("F", bound=Callable[..., Any])
logger = structlog.get_logger(__name__)


def log_execution_time[F: Callable[..., Any]](func: F) -> F:
    """
    Decorator to log function execution time.

    Usage:
        @log_execution_time
        def my_function():
            pass
    """

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.time()
        func_name = func.__module__ + "." + func.__qualname__
        logger.info("Function started", function=func_name)
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start
            logger.info(
                "Function completed",
                function=func_name,
                duration_ms=round(duration * 1000, 2),
            )
            return result
        except Exception as exc:
            duration = time.time() - start
            logger.exception(
                "Function failed",
                function=func_name,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
            )
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.time()
        func_name = func.__module__ + "." + func.__qualname__
        logger.info("Function started", function=func_name)
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            logger.info(
                "Function completed",
                function=func_name,
                duration_ms=round(duration * 1000, 2),
            )
            return result
        except Exception as exc:
            duration = time.time() - start
            logger.exception(
                "Function failed",
                function=func_name,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
            )
            raise

    # Return appropriate wrapper based on whether function is async
    import inspect

    if inspect.iscoroutinefunction(func):
        return async_wrapper  # type: ignore
    else:
        return sync_wrapper  # type: ignore


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
