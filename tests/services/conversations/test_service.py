from uuid import uuid4

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
