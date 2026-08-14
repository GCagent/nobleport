"""NoblePort Nano Optimization Layer.

Small, auditable optimizations for routing, context selection, latency measurement,
and safe parallel execution. This module does not execute financial, custody,
securities, permit, or other gated writes.
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Iterable, Mapping, Sequence, TypeVar


class ExecutionLane(str, Enum):
    FAST = "FAST"
    STANDARD = "STANDARD"
    REASONING = "REASONING"
    GATED = "GATED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


GATED_TERMS = {
    "ach", "wire", "payment", "release funds", "treasury", "custody",
    "token transfer", "securities", "investor purchase", "permit approval",
    "sign contract", "execute contract", "wallet transfer", "swap", "stake",
}
REASONING_TERMS = {
    "architecture", "red team", "compare", "conflict", "strategy", "design",
    "legal analysis", "compliance analysis", "root cause", "optimize",
}
FAST_TERMS = {
    "extract", "classify", "format", "map fields", "lookup", "summarize status",
    "phone number", "email address", "project id", "address",
}


@dataclass(frozen=True)
class ContextItem:
    key: str
    text: str
    relevance: float = 0.0
    mandatory: bool = False
    evidence_class: str = "REPORTED"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class OptimizationPlan:
    lane: ExecutionLane
    risk: RiskLevel
    requires_human_approval: bool
    selected_keys: tuple[str, ...]
    original_chars: int
    selected_chars: int
    reduction_pct: float
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class TimingResult:
    name: str
    elapsed_ms: float


class NanoOptimizer:
    """Deterministic optimizer designed to be cheap enough to run on every request."""

    def __init__(self, target_context_chars: int = 12_000) -> None:
        if target_context_chars <= 0:
            raise ValueError("target_context_chars must be positive")
        self.target_context_chars = target_context_chars

    def classify_lane(self, request: str) -> tuple[ExecutionLane, RiskLevel, bool]:
        normalized = request.lower().strip()
        if any(term in normalized for term in GATED_TERMS):
            return ExecutionLane.GATED, RiskLevel.CRITICAL, True
        if any(term in normalized for term in REASONING_TERMS):
            return ExecutionLane.REASONING, RiskLevel.HIGH, False
        if any(term in normalized for term in FAST_TERMS):
            return ExecutionLane.FAST, RiskLevel.LOW, False
        return ExecutionLane.STANDARD, RiskLevel.MEDIUM, False

    def select_context(
        self,
        items: Sequence[ContextItem],
        max_chars: int | None = None,
    ) -> tuple[ContextItem, ...]:
        budget = max_chars or self.target_context_chars
        mandatory = [item for item in items if item.mandatory]
        optional = [item for item in items if not item.mandatory]

        selected: list[ContextItem] = []
        used = 0

        # Governance/evidence material is never pruned solely for latency.
        for item in mandatory:
            selected.append(item)
            used += item.size

        # Prefer high relevance per character, then absolute relevance.
        def score(item: ContextItem) -> tuple[float, float]:
            density = item.relevance / max(1.0, math.log2(item.size + 2))
            return density, item.relevance

        for item in sorted(optional, key=score, reverse=True):
            if used + item.size <= budget:
                selected.append(item)
                used += item.size

        return tuple(selected)

    def plan(self, request: str, items: Sequence[ContextItem]) -> OptimizationPlan:
        lane, risk, approval = self.classify_lane(request)
        selected = self.select_context(items)
        original = sum(i.size for i in items)
        selected_chars = sum(i.size for i in selected)
        reduction = 0.0 if original == 0 else (1 - selected_chars / original) * 100

        rationale = [f"lane={lane.value}", f"risk={risk.value}"]
        if approval:
            rationale.append("fail-closed: human approval required")
        if any(i.mandatory for i in items):
            rationale.append("mandatory governance/evidence context preserved")

        return OptimizationPlan(
            lane=lane,
            risk=risk,
            requires_human_approval=approval,
            selected_keys=tuple(i.key for i in selected),
            original_chars=original,
            selected_chars=selected_chars,
            reduction_pct=round(reduction, 2),
            rationale=tuple(rationale),
        )


T = TypeVar("T")


async def run_parallel(
    calls: Mapping[str, Callable[[], Awaitable[T]]],
    timeout_s: float = 2.0,
) -> dict[str, T | Exception]:
    """Run independent reads concurrently with per-call timeout isolation.

    Exceptions are returned per key rather than cancelling sibling work.
    Do not use this helper to parallelize dependent or irreversible writes.
    """

    async def one(name: str, fn: Callable[[], Awaitable[T]]) -> tuple[str, T | Exception]:
        try:
            return name, await asyncio.wait_for(fn(), timeout=timeout_s)
        except Exception as exc:  # caller decides fallback/fail-closed behavior
            return name, exc

    results = await asyncio.gather(*(one(name, fn) for name, fn in calls.items()))
    return dict(results)


async def timed(name: str, awaitable: Awaitable[T]) -> tuple[T, TimingResult]:
    start = time.perf_counter()
    result = await awaitable
    elapsed_ms = (time.perf_counter() - start) * 1000
    return result, TimingResult(name=name, elapsed_ms=round(elapsed_ms, 3))
