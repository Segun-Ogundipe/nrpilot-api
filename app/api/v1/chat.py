from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.kubernetes.exceptions import (
    KubernetesConnectionError,
    KubernetesError,
)
from app.agents.nrpilot import NRPilotAgent
from app.dependencies import get_nrpilot_agent
from app.models.agents.nrpilot import ChatAnswer, ChatQuestion

router = APIRouter(prefix="/api/v1", tags=["NRPilot Chat"])


@router.post("/chat")
def chat(
    request: ChatQuestion,
    agent: Annotated[NRPilotAgent, Depends(get_nrpilot_agent)],
) -> ChatAnswer:
    return _run(lambda: ChatAnswer(answer=agent.ask(request.question)))


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
