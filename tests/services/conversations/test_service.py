from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from app.models.agents.nrpilot import ConversationMessage
from app.services.conversations.service import ConversationService


class FakeAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[ConversationMessage] | None]] = []

    def ask(
        self, question: str, history: list[ConversationMessage] | None = None
    ) -> str:
        self.calls.append((question, history))
        return f"answer to {question}"


class FakeStreamingAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[ConversationMessage] | None]] = []

    async def stream(
        self, question: str, history: list[ConversationMessage] | None = None
    ) -> AsyncIterator[str]:
        self.calls.append((question, history))
        yield "answer to "
        yield question


def test_conversation_service_supplies_prior_turn_to_follow_up() -> None:
    service = ConversationService()
    agent = FakeAgent()
    conversation_id = uuid4()

    service.ask(conversation_id, "Why is api failing?", agent)  # type: ignore[arg-type]
    service.ask(conversation_id, "What should I check next?", agent)  # type: ignore[arg-type]

    assert agent.calls[1] == (
        "What should I check next?",
        [
            ConversationMessage(role="user", content="Why is api failing?"),
            ConversationMessage(
                role="assistant", content="answer to Why is api failing?"
            ),
        ],
    )


def test_conversation_service_keeps_conversations_isolated() -> None:
    service = ConversationService()
    agent = FakeAgent()

    service.ask(uuid4(), "First conversation", agent)  # type: ignore[arg-type]
    service.ask(uuid4(), "Second conversation", agent)  # type: ignore[arg-type]

    assert agent.calls[1][1] == []


@pytest.mark.asyncio
async def test_conversation_service_stream_supplies_and_persists_history() -> None:
    service = ConversationService()
    agent = FakeStreamingAgent()
    conversation_id = uuid4()

    first_answer = "".join(
        [
            chunk
            async for chunk in service.stream(
                conversation_id,
                "Why is api failing?",
                agent,  # type: ignore[arg-type]
            )
        ]
    )
    second_answer = "".join(
        [
            chunk
            async for chunk in service.stream(
                conversation_id,
                "What should I check next?",
                agent,  # type: ignore[arg-type]
            )
        ]
    )

    assert first_answer == "answer to Why is api failing?"
    assert second_answer == "answer to What should I check next?"
    assert agent.calls[1] == (
        "What should I check next?",
        [
            ConversationMessage(role="user", content="Why is api failing?"),
            ConversationMessage(
                role="assistant", content="answer to Why is api failing?"
            ),
        ],
    )
