from __future__ import annotations

from enum import Enum
from math import dist
from typing import Any, Dict, List, Literal, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class VerificationStatus(str, Enum):
    PENDING = "pending"
    PROVISIONAL = "provisional"
    COMMITTED = "committed"
    HELD = "held"


class Point3D(BaseModel):
    x: float
    y: float
    z: float = 0.0

    def tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)


class BoundingBox(BaseModel):
    min: Point3D
    max: Point3D

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        if self.min.x > self.max.x or self.min.y > self.max.y or self.min.z > self.max.z:
            raise ValueError("bbox min must not exceed max")
        return self


class Evidence(BaseModel):
    source_doc_uuid: Optional[str] = None
    source_page: Optional[int] = None
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    cross_source_agreement: float = Field(default=0.0, ge=0.0, le=1.0)
    human_verified: bool = False
    verification_status: VerificationStatus = VerificationStatus.PENDING


class GeometricEntity(BaseModel):
    uuid: str = Field(default_factory=lambda: f"ent_{uuid4().hex}")
    project_id: str
    revision: str
    store: Literal["design", "asbuilt"] = "design"
    class_name: str = Field(alias="class")
    subclass: Optional[str] = None
    centroid: Point3D
    bbox: BoundingBox
    properties: Dict[str, Any] = Field(default_factory=dict)
    evidence: Evidence

    model_config = {"populate_by_name": True}


class GeometricPredicate(BaseModel):
    type: str
    value: float
    unit: str = "m"
    tolerance: float = Field(default=0.0, ge=0.0)


class Relationship(BaseModel):
    uuid: str = Field(default_factory=lambda: f"rel_{uuid4().hex}")
    source_uuid: str
    target_uuid: str
    relation_type: str
    relation_subtype: Optional[str] = None
    geometric_predicate: GeometricPredicate
    confidence: float = Field(ge=0.0, le=1.0)
    inferred: bool = False
    evidence: Dict[str, Any] = Field(default_factory=dict)


class ConstraintResult(BaseModel):
    name: str
    satisfied: bool
    severity: Literal["info", "warning", "hard"]
    measured: Optional[float] = None
    required: Optional[float] = None
    unit: str = "m"


class VerificationDecision(BaseModel):
    status: VerificationStatus
    composite_confidence: float
    review_required: bool
    reason: str


def composite_confidence(extraction: float, cross_source: float, human_verified: bool = False) -> float:
    score = (0.65 * extraction) + (0.35 * cross_source)
    if human_verified:
        score += 0.08
    return round(min(score, 1.0), 4)


def verification_gate(*, extraction_confidence: float, cross_source_agreement: float,
                      human_verified: bool = False, hard_clash: bool = False,
                      code_compliant: bool = True, code_critical: bool = False) -> VerificationDecision:
    confidence = composite_confidence(extraction_confidence, cross_source_agreement, human_verified)
    if hard_clash or not code_compliant:
        return VerificationDecision(status=VerificationStatus.HELD, composite_confidence=confidence,
                                    review_required=True, reason="hard clash or code-compliance failure")
    if confidence >= 0.92:
        return VerificationDecision(status=VerificationStatus.COMMITTED, composite_confidence=confidence,
                                    review_required=code_critical,
                                    reason="verified geometric fact" if not code_critical else "committed; code-critical review required")
    if confidence >= 0.75:
        return VerificationDecision(status=VerificationStatus.PROVISIONAL, composite_confidence=confidence,
                                    review_required=True, reason="provisional fact; human review queued")
    return VerificationDecision(status=VerificationStatus.HELD, composite_confidence=confidence,
                                review_required=True, reason="confidence below commit threshold")


def centerline_offset(a: GeometricEntity, b: GeometricEntity,
                      axis: Literal["x", "y", "z"] = "x") -> float:
    return abs(getattr(a.centroid, axis) - getattr(b.centroid, axis))


def centered_on(opening: GeometricEntity, host: GeometricEntity, *, tolerance_m: float = 0.00635,
                axis: Literal["x", "y", "z"] = "x") -> Relationship:
    offset = centerline_offset(opening, host, axis)
    return Relationship(source_uuid=opening.uuid, target_uuid=host.uuid,
                        relation_type="centered_on", relation_subtype="opening_centered",
                        geometric_predicate=GeometricPredicate(type="centerline_offset",
                                                               value=round(offset, 6), unit="m",
                                                               tolerance=tolerance_m),
                        confidence=min(opening.evidence.extraction_confidence,
                                       host.evidence.extraction_confidence), inferred=False)


def min_clearance(a: GeometricEntity, b: GeometricEntity, required_m: float) -> ConstraintResult:
    measured = dist(a.centroid.tuple(), b.centroid.tuple())
    return ConstraintResult(name="min_clearance", satisfied=measured >= required_m,
                            severity="warning", measured=round(measured, 6), required=required_m)


def compare_design_asbuilt(design: GeometricEntity, asbuilt: GeometricEntity, *,
                           tolerance_m: float) -> ConstraintResult:
    measured = dist(design.centroid.tuple(), asbuilt.centroid.tuple())
    return ConstraintResult(name="design_asbuilt_centroid_delta", satisfied=measured <= tolerance_m,
                            severity="warning" if measured <= tolerance_m else "hard",
                            measured=round(measured, 6), required=tolerance_m)


class StructuredProjectMemory:
    """Minimal in-memory SPM adapter for deterministic testing and API integration."""

    def __init__(self) -> None:
        self.entities: Dict[str, GeometricEntity] = {}
        self.relationships: Dict[str, Relationship] = {}
        self.constraints: List[ConstraintResult] = []

    def commit_entity(self, entity: GeometricEntity, decision: VerificationDecision) -> GeometricEntity:
        if decision.status not in {VerificationStatus.COMMITTED, VerificationStatus.PROVISIONAL}:
            raise ValueError("held geometry cannot enter structured project memory")
        entity.evidence.verification_status = decision.status
        self.entities[entity.uuid] = entity
        return entity

    def add_relationship(self, relationship: Relationship) -> Relationship:
        if relationship.source_uuid not in self.entities or relationship.target_uuid not in self.entities:
            raise ValueError("relationships require committed/provisional entities")
        self.relationships[relationship.uuid] = relationship
        return relationship

    def add_constraint(self, result: ConstraintResult) -> ConstraintResult:
        self.constraints.append(result)
        return result

    def relations_for(self, entity_uuid: str) -> List[Relationship]:
        return [rel for rel in self.relationships.values()
                if rel.source_uuid == entity_uuid or rel.target_uuid == entity_uuid]
