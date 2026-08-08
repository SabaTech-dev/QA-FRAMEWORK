"""
German AI Liability Benchmarks

Predefined benchmarks based on the BGH ruling on AI liability
(BGH, Urteil vom 28.01.2025 - VI ZR 67/24 — German Federal Court
of Justice decision on liability for AI-generated content).

Key legal principles:
1. AI outputs can constitute a "product" under Produkthaftungsgesetz
2. The producer of an AI system is responsible for output safety
3. Burden of proof reversal applies in certain AI damage cases
4. Users must exercise reasonable diligence when relying on AI output
"""

from src.domain.accuracy_testing.entities import AccuracyBenchmark
from src.domain.accuracy_testing.value_objects import (
    EvaluationCriterion,
    LegalDomain,
)


def create_german_ai_liability_benchmarks() -> list[AccuracyBenchmark]:
    """Create benchmark set for the German AI liability ruling."""
    return [
        AccuracyBenchmark(
            name="DE-AI-001: AI as Product Liability",
            description="Tests whether AI correctly identifies AI systems as products under German product liability law",
            legal_domain=LegalDomain.AI_LIABILITY,
            jurisdiction="DE",
            question=(
                "Under German law, can an AI system's output be considered a 'product' "
                "under the Produkthaftungsgesetz (ProdHaftG)? Who bears liability?"
            ),
            ground_truth=(
                "According to the BGH ruling (VI ZR 67/24, January 2025), AI outputs "
                "can constitute a 'product' under the German Product Liability Act "
                "(Produkthaftungsgesetz - ProdHaftG). The producer (Hersteller) of the "
                "AI system bears liability for defective outputs under § 1 ProdHaftG. "
                "This extends strict product liability to AI-generated content when it "
                "causes damage to protected legal interests (life, body, health, property)."
            ),
            key_points=[
                "AI output qualifies as a 'product' under ProdHaftG",
                "Strict liability applies to the AI producer",
                "Protected interests: life, body, health, property",
                "§ 1 ProdHaftG applies to AI-generated content",
                "The BGH ruling establishes precedent for AI product liability",
            ],
            legal_references=[
                "BGH, Urteil vom 28.01.2025 - VI ZR 67/24",
                "§ 1 Produkthaftungsgesetz (ProdHaftG)",
                "§ 4 ProdHaftG (producer definition)",
            ],
            criteria=[
                EvaluationCriterion.FACTUAL_ACCURACY,
                EvaluationCriterion.LEGAL_REASONING,
                EvaluationCriterion.CITATION_CORRECTNESS,
                EvaluationCriterion.COMPLETENESS,
                EvaluationCriterion.NUANCE_HANDLING,
            ],
            passing_threshold=0.6,
            source="BGH Urteil vom 28.01.2025 - VI ZR 67/24",
            difficulty="medium",
            tags=["product-liability", "ai-output", "german-law", "bgh"],
        ),
        AccuracyBenchmark(
            name="DE-AI-002: Burden of Proof Reversal",
            description="Tests knowledge of burden of proof reversal in AI damage cases",
            legal_domain=LegalDomain.AI_LIABILITY,
            jurisdiction="DE",
            question=(
                "Does German law provide for a reversal of the burden of proof "
                "in cases involving damages caused by AI systems?"
            ),
            ground_truth=(
                "The BGH ruling establishes that in AI-related damage cases, "
                "courts may apply a reversal of the burden of proof (Beweislastumkehr). "
                "Given the opacity of AI decision-making processes, the injured party "
                "typically cannot prove which specific defect in the AI caused the damage. "
                "Therefore, the producer may need to demonstrate that the AI system was "
                "not defective and that the damage was not caused by the AI. This mirrors "
                "existing principles in pharmaceutical liability (§ 84 AMG analog) and "
                "environmental liability."
            ),
            key_points=[
                "Burden of proof reversal applies in AI damage cases",
                "AI opacity justifies shifting proof burden to producer",
                "Analogy to pharmaceutical and environmental liability",
                "Producer must prove AI was not defective",
                "Consumer protection rationale underpins the reversal",
            ],
            legal_references=[
                "BGH, Urteil vom 28.01.2025 - VI ZR 67/24",
                "§ 84 Arzneimittelgesetz (AMG) - analogous",
                "Umwelthaftungsgesetz (UmweltHG) - analogous",
            ],
            criteria=[
                EvaluationCriterion.FACTUAL_ACCURACY,
                EvaluationCriterion.LEGAL_REASONING,
                EvaluationCriterion.CITATION_CORRECTNESS,
                EvaluationCriterion.COMPLETENESS,
                EvaluationCriterion.NUANCE_HANDLING,
            ],
            passing_threshold=0.6,
            source="BGH Urteil vom 28.01.2025 - VI ZR 67/24",
            difficulty="hard",
            tags=["burden-of-proof", "beweislastumkehr", "ai-opacity", "german-law"],
        ),
        AccuracyBenchmark(
            name="DE-AI-003: User Due Diligence Obligations",
            description="Tests whether AI correctly describes user obligations when relying on AI output",
            legal_domain=LegalDomain.AI_LIABILITY,
            jurisdiction="DE",
            question=(
                "What obligations do users of AI systems have under German law "
                "regarding verification of AI-generated output? Can users claim "
                "full reliance on AI without liability?"
            ),
            ground_truth=(
                "Under the BGH ruling framework, users of AI systems have a duty "
                "of reasonable verification (Prüfungspflicht) of AI outputs. Users "
                "cannot blindly rely on AI-generated content, especially in high-stakes "
                "domains like legal advice, medical diagnosis, or financial decisions. "
                "The extent of the verification duty depends on: (1) the risk level of "
                "the use case, (2) the user's expertise, and (3) the foreseeable "
                "consequences of incorrect AI output. Contributory negligence (§ 254 BGB) "
                "may reduce or exclude the user's damages claim if verification duties "
                "were breached."
            ),
            key_points=[
                "Users have verification duties (Prüfungspflicht)",
                "Blind reliance on AI is not protected",
                "Verification scope depends on risk, expertise, and consequences",
                "§ 254 BGB contributory negligence may apply",
                "High-stakes domains require stricter verification",
            ],
            legal_references=[
                "BGH, Urteil vom 28.01.2025 - VI ZR 67/24",
                "§ 254 BGB (contributory negligence)",
                "General duty of care (Verkehrssicherungspflichten)",
            ],
            criteria=[
                EvaluationCriterion.FACTUAL_ACCURACY,
                EvaluationCriterion.LEGAL_REASONING,
                EvaluationCriterion.COMPLETENESS,
                EvaluationCriterion.NUANCE_HANDLING,
            ],
            passing_threshold=0.6,
            source="BGH Urteil vom 28.01.2025 - VI ZR 67/24",
            difficulty="medium",
            tags=["user-obligations", "due-diligence", "contributory-negligence", "german-law"],
        ),
        AccuracyBenchmark(
            name="DE-AI-004: EU AI Act Interaction",
            description="Tests understanding of how the German ruling interacts with the EU AI Act",
            legal_domain=LegalDomain.EU_AI_ACT,
            jurisdiction="DE",
            question=(
                "How does the German BGH ruling on AI liability interact with "
                "the EU AI Act (Regulation 2024/1689)? Are there overlapping obligations?"
            ),
            ground_truth=(
                "The BGH ruling on AI liability and the EU AI Act operate on different "
                "legal bases but are complementary. The EU AI Act (Regulation 2024/1689) "
                "establishes a risk-based regulatory framework requiring compliance "
                "obligations (transparency, documentation, human oversight) before AI "
                "systems enter the market. The BGH ruling addresses civil liability "
                "ex post — when AI causes damage. Key interactions: (1) Compliance with "
                "EU AI Act requirements may serve as evidence of due diligence in "
                "liability proceedings; (2) Non-compliance with the AI Act may indicate "
                "a defect under ProdHaftG; (3) High-risk AI systems under the AI Act "
                "face stricter liability exposure under the BGH framework; (4) The EU "
                "is separately working on an AI Liability Directive that will harmonize "
                "these rules across member states."
            ),
            key_points=[
                "EU AI Act = ex ante regulation; BGH ruling = ex post liability",
                "AI Act compliance may evidence due diligence",
                "Non-compliance may indicate product defect",
                "High-risk AI = stricter liability exposure",
                "Upcoming EU AI Liability Directive will harmonize",
            ],
            legal_references=[
                "BGH, Urteil vom 28.01.2025 - VI ZR 67/24",
                "Regulation (EU) 2024/1689 (AI Act)",
                "Proposed AI Liability Directive (COM/2022/496)",
            ],
            criteria=[
                EvaluationCriterion.FACTUAL_ACCURACY,
                EvaluationCriterion.LEGAL_REASONING,
                EvaluationCriterion.CITATION_CORRECTNESS,
                EvaluationCriterion.COMPLETENESS,
                EvaluationCriterion.NUANCE_HANDLING,
            ],
            passing_threshold=0.6,
            source="BGH Urteil + EU AI Act interaction analysis",
            difficulty="hard",
            tags=["eu-ai-act", "interaction", "regulatory-framework", "cross-reference"],
        ),
    ]
