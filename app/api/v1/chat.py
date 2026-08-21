import json
from collections.abc import AsyncIterator, Callable
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

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


@router.post("/chat", response_model=ChatAnswer)
def chat(
    request: ChatQuestion,
    http_request: Request,
    agent: Annotated[NRPilotAgent, Depends(get_nrpilot_agent)],
    conversation_service: Annotated[
        ConversationService, Depends(get_conversation_service)
    ],
) -> ChatAnswer | StreamingResponse:
    if "text/event-stream" in http_request.headers.get("accept", ""):
        return _stream_response(
            agent,
            conversation_service,
            request.conversation_id or uuid4(),
            request.question,
        )
    conversation_id = request.conversation_id or uuid4()
    answer = _run(
        lambda: conversation_service.ask(conversation_id, request.question, agent)
    )
    return ChatAnswer(answer=answer, conversation_id=conversation_id)


@router.post("/chat/stream")
async def stream_chat(
    request: ChatQuestion,
    agent: Annotated[NRPilotAgent, Depends(get_nrpilot_agent)],
    conversation_service: Annotated[
        ConversationService, Depends(get_conversation_service)
    ],
) -> StreamingResponse:
    """Stream answer chunks as server-sent events.

    A leading ``conversation`` event supplies the conversation ID. Each ``message``
    event contains an ``answer`` field. A terminal ``done`` event marks a successful
    response; an ``error`` event contains a user-safe message.
    """
    return _stream_response(
        agent,
        conversation_service,
        request.conversation_id or uuid4(),
        request.question,
    )


def _stream_response(
    agent: NRPilotAgent,
    conversation_service: ConversationService,
    conversation_id: UUID,
    question: str,
) -> StreamingResponse:
    return StreamingResponse(
        _stream_events(agent, conversation_service, conversation_id, question),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_events(
    agent: NRPilotAgent,
    conversation_service: ConversationService,
    conversation_id: UUID,
    question: str,
) -> AsyncIterator[str]:
    try:
        yield _sse_event("conversation", {"conversation_id": str(conversation_id)})
        async for chunk in conversation_service.stream(
            conversation_id, question, agent
        ):
            yield _sse_event("message", {"answer": chunk})
    except KubernetesConnectionError:
        yield _sse_event("error", {"detail": "Kubernetes cluster is unavailable"})
    except KubernetesError:
        yield _sse_event("error", {"detail": "Kubernetes resource was not found"})
    except DocumentationUnavailableError:
        yield _sse_event("error", {"detail": "NRP documentation is unavailable"})
    else:
        yield _sse_event("done", {})


def _sse_event(event: str, data: dict[str, str]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


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
