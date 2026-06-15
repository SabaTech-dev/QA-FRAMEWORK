"""
Interfaces for AI Act Compliance Domain

Abstract interfaces defining contracts for compliance exporters
and persistence.
"""

from abc import ABC, abstractmethod
from typing import Optional, Protocol

from .entities import AnnexIVReport, SARIFReport
from .value_objects import ComplianceStatus


class IAnnexIVExporter(Protocol):
    """Protocol for exporting Annex IV compliance reports."""

    def export(
        self,
        system_description,
        testing_methodology,
        test_session,
    ) -> AnnexIVReport:
        """
        Generate an Annex IV report from testing results.

        Args:
            system_description: AI system metadata (domain entity)
            testing_methodology: Testing approach documentation
            test_session: AccuracyTestSession with evaluation results

        Returns:
            AnnexIVReport with populated evidence and requirements
        """
        ...


class ISARIFExporter(Protocol):
    """Protocol for exporting SARIF 2.1.0 reports."""

    def export(
        self,
        test_session,
        system_description=None,
    ) -> SARIFReport:
        """
        Generate a SARIF 2.1.0 report from testing results.

        Args:
            test_session: AccuracyTestSession with evaluation results
            system_description: Optional system metadata for context

        Returns:
            SARIFReport with one run containing all test results
        """
        ...


class IComplianceRepository(ABC):
    """Abstract repository for compliance report persistence."""

    @abstractmethod
    async def save_annex_iv(self, report: AnnexIVReport) -> AnnexIVReport:
        """Save an Annex IV report."""
        pass

    @abstractmethod
    async def get_annex_iv(self, report_id: str) -> Optional[AnnexIVReport]:
        """Retrieve an Annex IV report by ID."""
        pass

    @abstractmethod
    async def save_sarif(self, report: SARIFReport) -> SARIFReport:
        """Save a SARIF report."""
        pass

    @abstractmethod
    async def get_sarif(self, report_id: str) -> Optional[SARIFReport]:
        """Retrieve a SARIF report by ID."""
        pass
