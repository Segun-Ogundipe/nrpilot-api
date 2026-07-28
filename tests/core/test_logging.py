from app.core.logging import (
    bind_context,
    clear_context,
    get_logger,
    unbind_context,
)


def test_context_helpers_bind_unbind_and_clear() -> None:
    bind_context(user_id="123")
    unbind_context("user_id")
    clear_context()

    assert get_logger("test") is not None
