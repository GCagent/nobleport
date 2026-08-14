import pytest

from api.geometric_reasoning import (
    BoundingBox,
    Evidence,
    GeometricEntity,
    Point3D,
    StructuredProjectMemory,
    VerificationStatus,
    centered_on,
    compare_design_asbuilt,
    verification_gate,
)


def entity(name, x, *, store="design", conf=0.96, cross=0.96):
    return GeometricEntity(
        project_id="proj_window_test",
        revision="rev_A",
        store=store,
        **{"class": name},
        centroid=Point3D(x=x, y=0, z=1.2),
        bbox=BoundingBox(
            min=Point3D(x=x - 0.5, y=-0.05, z=0),
            max=Point3D(x=x + 0.5, y=0.05, z=2.4),
        ),
        evidence=Evidence(
            extraction_confidence=conf,
            cross_source_agreement=cross,
        ),
    )


def test_high_confidence_geometry_commits():
    decision = verification_gate(extraction_confidence=0.97, cross_source_agreement=0.96)
    assert decision.status == VerificationStatus.COMMITTED
    assert decision.review_required is False


def test_medium_confidence_is_provisional_and_reviewed():
    decision = verification_gate(extraction_confidence=0.82, cross_source_agreement=0.80)
    assert decision.status == VerificationStatus.PROVISIONAL
    assert decision.review_required is True


def test_hard_clash_is_held_even_with_high_confidence():
    decision = verification_gate(extraction_confidence=0.99, cross_source_agreement=0.99, hard_clash=True)
    assert decision.status == VerificationStatus.HELD


def test_code_critical_fact_requires_human_review():
    decision = verification_gate(extraction_confidence=0.99, cross_source_agreement=0.99, code_critical=True)
    assert decision.status == VerificationStatus.COMMITTED
    assert decision.review_required is True


def test_window_centerline_relationship_is_precise():
    wall = entity("wall", 2.134)
    window = entity("window", 2.134)
    spm = StructuredProjectMemory()
    decision = verification_gate(extraction_confidence=0.97, cross_source_agreement=0.97)
    spm.commit_entity(wall, decision)
    spm.commit_entity(window, decision)
    rel = centered_on(window, wall, tolerance_m=0.00635)
    spm.add_relationship(rel)
    assert rel.geometric_predicate.value == 0.0
    assert rel.geometric_predicate.tolerance == pytest.approx(0.00635)


def test_asbuilt_quarter_inch_delta_passes_quarter_inch_tolerance():
    design = entity("window", 2.134, store="design")
    asbuilt = entity("window", 2.140, store="asbuilt")
    result = compare_design_asbuilt(design, asbuilt, tolerance_m=0.00635)
    assert result.satisfied is True


def test_asbuilt_half_inch_delta_fails_quarter_inch_tolerance():
    design = entity("window", 2.134, store="design")
    asbuilt = entity("window", 2.147, store="asbuilt")
    result = compare_design_asbuilt(design, asbuilt, tolerance_m=0.00635)
    assert result.satisfied is False
    assert result.severity == "hard"


def test_held_geometry_cannot_pollute_memory():
    spm = StructuredProjectMemory()
    bad = entity("beam", 0.0, conf=0.55, cross=0.5)
    decision = verification_gate(extraction_confidence=0.55, cross_source_agreement=0.5)
    with pytest.raises(ValueError):
        spm.commit_entity(bad, decision)
