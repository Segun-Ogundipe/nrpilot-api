from pydantic import BaseModel, Field


class ChatAnswer(BaseModel):
    answer: str


class ChatQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)
