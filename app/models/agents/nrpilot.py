from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatAnswer(BaseModel):
    answer: str
    conversation_id: UUID


class ChatQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)
    conversation_id: UUID | None = None


class ConversationMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["user", "assistant"]
    content: str
