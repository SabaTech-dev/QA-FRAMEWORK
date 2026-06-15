"""Helper fixtures for compliance tests."""
from src.domain.compliance.value_objects import AnnexIVSection, AnnexIVRequirement
from src.domain.compliance.entities import ComplianceEvidence


def make_satisfied_requirements():
    """All 16 requirements satisfied."""
    reqs = []
    for section in AnnexIVSection:
        reqs.append(AnnexIVRequirement(
            section=section,
            title=f"Req {section.value}",
            description="Satisfied",
            is_satisfied=True,
        ))
    return reqs


def make_mixed_requirements():
    """Only 3 satisfied out of 16 (mostly non-compliant)."""
    reqs = []
    for i, section in enumerate(AnnexIVSection):
        reqs.append(AnnexIVRequirement(
            section=section,
            title=f"Req {section.value}",
            description="Mixed",
            is_satisfied=(i < 3),
        ))
    return reqs


def make_passing_evidence():
    """Evidence items that all pass."""
    return [
        ComplianceEvidence(
            annex_section=AnnexIVSection.ACCURACY_ROBUSTNESS,
            evidence_type="accuracy_test",
            title="Pass",
            description="Passed",
            passed=True,
            metric_value=0.9,
            metric_target=0.6,
        ),
        ComplianceEvidence(
            annex_section=AnnexIVSection.TRAINING_METRICS,
            evidence_type="criterion_score",
            title="Pass",
            description="Passed",
            passed=True,
            metric_value=0.8,
            metric_target=0.6,
        ),
    ]
