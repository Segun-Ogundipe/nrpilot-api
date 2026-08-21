from asyncio import Lock as AsyncLock
from collections import defaultdict
from collections.abc import AsyncIterator
from threading import Lock, RLock
from uuid import UUID

from app.agents.nrpilot import NRPilotAgent
from app.models.agents.nrpilot import ConversationMessage


class ConversationService:
    """Keeps bounded, in-process chat history for active conversations."""

    def __init__(self, max_turns: int = 20) -> None:
        self._max_messages = max_turns * 2
        self._conversations: dict[UUID, list[ConversationMessage]] = {}
        self._conversation_locks = defaultdict[UUID, RLock](RLock)
        self._stream_locks = defaultdict[UUID, AsyncLock](AsyncLock)
        self._locks_lock = Lock()

    def ask(self, conversation_id: UUID, question: str, agent: NRPilotAgent) -> str:
        """Run a question with its prior context and retain the completed turn."""
        with self._get_conversation_lock(conversation_id):
            history = self._conversations.get(conversation_id, [])
            answer = agent.ask(question, history)
            updated_history = [
                *history,
                ConversationMessage(role="user", content=question),
                ConversationMessage(role="assistant", content=answer),
            ]
            self._conversations[conversation_id] = updated_history[
                -self._max_messages :
            ]
            return answer

    async def stream(
        self, conversation_id: UUID, question: str, agent: NRPilotAgent
    ) -> AsyncIterator[str]:
        """Stream a response with prior context and retain its completed turn."""
        async with self._get_stream_lock(conversation_id):
            history = self._conversations.get(conversation_id, [])
            answer_chunks: list[str] = []
            async for chunk in agent.stream(question, history):
                answer_chunks.append(chunk)
                yield chunk
            self._save_turn(conversation_id, history, question, "".join(answer_chunks))

    def _get_conversation_lock(self, conversation_id: UUID) -> RLock:
        with self._locks_lock:
            return self._conversation_locks[conversation_id]

    def _get_stream_lock(self, conversation_id: UUID) -> AsyncLock:
        with self._locks_lock:
            return self._stream_locks[conversation_id]

    def _save_turn(
        self,
        conversation_id: UUID,
        history: list[ConversationMessage],
        question: str,
        answer: str,
    ) -> None:
        updated_history = [
            *history,
            ConversationMessage(role="user", content=question),
            ConversationMessage(role="assistant", content=answer),
        ]
        self._conversations[conversation_id] = updated_history[-self._max_messages :]
