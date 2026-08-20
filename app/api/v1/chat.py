from collections.abc import Callable
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.kubernetes.exceptions import (
    KubernetesConnectionError,
    KubernetesError,
)
from app.agents.nrpilot import NRPilotAgent
from app.dependencies import get_conversation_service, get_nrpilot_agent
from app.domain.documentation.exceptions import DocumentationUnavailableError
from app.models.agents.nrpilot import ChatAnswer, ChatQuestion
from app.services.conversations.service import ConversationService

router = APIRouter(prefix="/api/v1", tags=["NRPilot Chat"])


@router.post("/chat")
def chat(
    request: ChatQuestion,
    agent: Annotated[NRPilotAgent, Depends(get_nrpilot_agent)],
    conversation_service: Annotated[
        ConversationService, Depends(get_conversation_service)
    ],
) -> ChatAnswer:
    conversation_id = request.conversation_id or uuid4()
    answer = _run(
        lambda: conversation_service.ask(conversation_id, request.question, agent)
    )
    return ChatAnswer(answer=answer, conversation_id=conversation_id)


def _run[T](operation: Callable[[], T]) -> T:
    try:
        return operation()
    except KubernetesConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Kubernetes cluster is unavailable",
        ) from exc
    except KubernetesError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kubernetes resource was not found",
        ) from exc
    except DocumentationUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="NRP documentation is unavailable",
        ) from exc
