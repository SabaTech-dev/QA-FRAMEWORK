"""
Default Annex IV Requirements

Maps all Annex IV sections to structured requirements that
the technical documentation must address.

Reference: EU AI Act Annex IV (Regulation 2024/1689)
"""

from src.domain.compliance.value_objects import (
    AnnexIVSection,
    AnnexIVRequirement,
)


def create_default_requirements() -> list[AnnexIVRequirement]:
    """
    Create the complete set of Annex IV documentation requirements.

    Returns requirements for all 16 sections of Annex IV.
    Sections 5-7 and 11-12 are testable with QA-FRAMEWORK evidence;
    others require manual documentation.
    """
    return [
        AnnexIVRequirement(
            section=AnnexIVSection.SYSTEM_DESCRIPTION,
            title="Description of the AI system",
            description=(
                "General description of the AI system including its intended "
                "purpose, name, version, and provider information."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.INTENDED_PURPOSE,
            title="Intended purpose of the AI system",
            description=(
                "Detailed description of the specific purposes and contexts "
                "for which the AI system is intended to be used."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.PERSONS_AFFECTED,
            title="Persons likely to be affected",
            description=(
                "Description of the persons, groups or categories of persons "
                "likely to be affected by the AI system."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.ACTORS_ROLES,
            title="Actors in operation and use",
            description=(
                "Description of the actors involved in the operation and use "
                "of the AI system, including their roles and responsibilities."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.TRAINING_VALIDATION_TESTING,
            title="Datasets and data governance",
            description=(
                "Description of the datasets used for training, validation, "
                "and testing, including data collection, labeling, and governance."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.TRAINING_METRICS,
            title="Relevant training and validation metrics",
            description=(
                "Description of the relevant metrics calculated for training, "
                "validation, and testing of the AI system."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.VALIDATION_TESTING,
            title="Pre-determined testing methodology",
            description=(
                "Description of the pre-determined testing methodology applied "
                "to the AI system, including explainability and interpretability."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.DESIGN_SPECS,
            title="Design specifications of the system",
            description=(
                "Description of the design specifications of the AI system, "
                "including trade-offs and assumptions made."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.SYSTEM_ARCHITECTURE,
            title="System architecture",
            description=(
                "Description of the system architecture explaining how software "
                "components build on or feed into each other."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.HUMAN_OVERSIGHT,
            title="Human oversight measures",
            description=(
                "Description of the human oversight measures (Art. 14) "
                "facilitating correct interpretation and effective oversight."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.ACCURACY_ROBUSTNESS,
            title="Accuracy and robustness (Art. 15)",
            description=(
                "Description of the accuracy and robustness metrics and "
                "evaluations performed, including results of testing."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.CYBERSECURITY,
            title="Cybersecurity measures (Art. 15)",
            description=(
                "Description of the cybersecurity measures (Art. 15(5)) "
                "implemented to protect the AI system."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.QUALITY_MANAGEMENT,
            title="Quality management system",
            description=(
                "Detailed information about the quality management system "
                "(Art. 17) implemented by the provider."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.TECHNICAL_LOGS,
            title="Technical logs",
            description=(
                "Description of the elements of the technical logs "
                "(Art. 12) automatically kept by the AI system."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.EU_DECLARATION,
            title="EU declaration of conformity reference",
            description=(
                "Reference to the EU declaration of conformity (Art. 47) "
                "and information about notified body involvement."
            ),
        ),
        AnnexIVRequirement(
            section=AnnexIVSection.POST_MARKET,
            title="Post-market monitoring plan",
            description=(
                "Description of the post-market monitoring plan (Art. 72) "
                "including procedures to monitor the AI system's performance."
            ),
        ),
    ]
