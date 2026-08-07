"""FastAPI surface for the NoblePort Nano Optimization Layer."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .nano_optimizer import ContextItem, NanoOptimizer

router = APIRouter(prefix="/api/nano", tags=["nano-optimization"])
optimizer = NanoOptimizer()


class ContextPayload(BaseModel):
    key: str
    text: str
    relevance: float = Field(default=0.0, ge=0.0)
    mandatory: bool = False
    evidence_class: str = "REPORTED"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlanRequest(BaseModel):
    request: str
    context: List[ContextPayload] = Field(default_factory=list)


@router.get("/health")
async def nano_health() -> dict[str, str]:
    return {
        "status": "operational",
        "mode": "advisory",
        "financial_execution": "disabled",
        "promotion_authority": "none",
    }


@router.post("/plan")
async def build_plan(payload: PlanRequest) -> dict[str, Any]:
    items = [
        ContextItem(
            key=item.key,
            text=item.text,
            relevance=item.relevance,
            mandatory=item.mandatory,
            evidence_class=item.evidence_class,
            metadata=item.metadata,
        )
        for item in payload.context
    ]
    plan = optimizer.plan(payload.request, items)
    return {
        "lane": plan.lane.value,
        "risk": plan.risk.value,
        "requires_human_approval": plan.requires_human_approval,
        "selected_keys": list(plan.selected_keys),
        "original_chars": plan.original_chars,
        "selected_chars": plan.selected_chars,
        "reduction_pct": plan.reduction_pct,
        "rationale": list(plan.rationale),
        "evidence_status": "RUNTIME_RESULT",
        "note": "This endpoint plans optimization only; it does not execute gated actions.",
    }
