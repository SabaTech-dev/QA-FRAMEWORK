"""Migration report generator."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from .migrator import DataMigrator

# MigrationStatus is defined as DataMigrator.MigrationStatus
MigrationStatus = DataMigrator.MigrationStatus


logger = logging.getLogger(__name__)


class MigrationReportGenerator:
    """
    Generator for migration reports.

    Creates detailed reports of the migration process including
    statistics, warnings, errors, and recommendations.
    """

    def __init__(self):
        """Initialize the report generator."""
        self._report = {}

    def generate(
        self,
        migrators: list[DataMigrator],
        overall_status: DataMigrator.MigrationStatus,
        execution_time: float,
    ) -> dict[str, Any]:
        """
        Generate a comprehensive migration report.

        Args:
            migrators: List of migrators that participated
            overall_status: Overall migration status
            execution_time: Total time taken for migration in seconds

        Returns:
            Complete migration report dictionary
        """
        self._report = {
            "summary": {
                "overall_status": overall_status.value,
                "execution_time_seconds": round(execution_time, 2),
                "started_at": self._get_first_start_time(migrators),
                "completed_at": datetime.now(UTC).isoformat(),
            },
            "total_records": self._calculate_total_records(migrators),
            "migrated_records": self._calculate_migrated_records(migrators),
            "failed_records": self._calculate_failed_records(migrators),
            "warnings": self._collect_all_warnings(migrators),
            "errors": self._collect_all_errors(migrators),
            "by_component": self._group_by_component(migrators),
            "recommendations": self._generate_recommendations(overall_status, migrators),
            "details": self._generate_component_details(migrators),
        }

        logger.info("Migration report generated")
        return self._report

    def _get_first_start_time(self, migrators: list[DataMigrator]) -> str:
        """Get the first start time from all migrators."""
        start_times = [
            stats.get("started_at")
            for migrator in migrators
            if (stats := migrator.get_stats()) and stats.get("started_at") is not None
        ]
        return min(start_times) if start_times else None

    def _calculate_total_records(self, migrators: list[DataMigrator]) -> int:
        """Calculate total records across all migrators."""
        return sum(
            stats.get("total_records", 0)
            for migrator in migrators
            if (stats := migrator.get_stats())
        )

    def _calculate_migrated_records(self, migrators: list[DataMigrator]) -> int:
        """Calculate total migrated records across all migrators."""
        return sum(
            stats.get("migrated_records", 0)
            for migrator in migrators
            if (stats := migrator.get_stats())
        )

    def _calculate_failed_records(self, migrators: list[DataMigrator]) -> int:
        """Calculate total failed records across all migrators."""
        return sum(
            stats.get("failed_records", 0)
            for migrator in migrators
            if (stats := migrator.get_stats())
        )

    def _collect_all_warnings(self, migrators: list[DataMigrator]) -> list[str]:
        """Collect all warnings from all migrators."""
        warnings = []
        for migrator in migrators:
            if stats := migrator.get_stats():
                warnings.extend(stats.get("warnings", []))
        return warnings

    def _collect_all_errors(self, migrators: list[DataMigrator]) -> list[str]:
        """Collect all errors from all migrators."""
        errors = []
        for migrator in migrators:
            if stats := migrator.get_stats():
                errors.extend(stats.get("errors", []))
        return errors

    def _group_by_component(self, migrators: list[DataMigrator]) -> dict[str, dict[str, Any]]:
        """Group migration stats by component."""

        by_component = {}

        for migrator in migrators:
            if stats := migrator.get_stats():
                # Determine component from migrator class name
                class_name = migrator.__class__.__name__.replace("Migrator", "")
                by_component[class_name] = {
                    "total": stats.get("total_records", 0),
                    "migrated": stats.get("migrated_records", 0),
                    "failed": stats.get("failed_records", 0),
                }

        return by_component

    def _generate_recommendations(
        self, overall_status: DataMigrator.MigrationStatus, migrators: list[DataMigrator]
    ) -> list[str]:
        """
        Generate recommendations based on migration status.

        Args:
            overall_status: Overall migration status
            migrators: List of migrators used

        Returns:
            List of recommendations
        """

        recommendations = []

        if overall_status == DataMigrator.MigrationStatus.COMPLETED:
            recommendations.append(
                "Migration completed successfully. All data migrated to default tenant."
            )
            recommendations.append("Verify data integrity by reviewing the details section below.")
            recommendations.append("Consider setting up backup before production deployment.")

        elif overall_status == DataMigrator.MigrationStatus.FAILED:
            recommendations.append("Migration failed. Review errors section for details.")
            recommendations.append("Check database connections and permissions.")
            recommendations.append("Ensure you have write permissions for all tables involved.")
            recommendations.append("Consider restoring from backup before retrying.")

            # Check for common issues
            all_errors = self._collect_all_errors(migrators)
            if len(all_errors) > 0:
                recommendations.append(
                    f"Found {len(all_errors)} error(s). Review each error carefully."
                )

        # Add warnings-based recommendations
        all_warnings = self._collect_all_warnings(migrators)
        if all_warnings:
            recommendations.append(f"Found {len(all_warnings)} warning(s). Review them carefully.")
            recommendations.append("Some data may have been skipped or migrated with limitations.")

        return recommendations

    def _generate_component_details(self, migrators: list[DataMigrator]) -> dict[str, Any]:
        """Generate detailed information for each component."""
        details = {}

        for migrator in migrators:
            if stats := migrator.get_stats():
                class_name = migrator.__class__.__name__.replace("Migrator", "")

                # Add common stats
                details[class_name] = {
                    "status": (
                        stats.get("status", {}).value
                        if isinstance(stats.get("status"), MigrationStatus)
                        else stats.get("status")
                    ),
                    "total_records": stats.get("total_records", 0),
                    "migrated_records": stats.get("migrated_records", 0),
                    "failed_records": stats.get("failed_records", 0),
                    "started_at": stats.get("started_at"),
                    "completed_at": stats.get("completed_at"),
                }

                # Add component-specific details
                if hasattr(migrator, "get_migrated_suites"):
                    details[class_name]["migrated_items"] = len(migrator.get_migrated_suites())

        return details

    def save_to_file(self, report: dict[str, Any], filepath: str) -> None:
        """
        Save migration report to JSON file.

        Args:
            report: Report dictionary
            filepath: Path to save the report
        """
        try:
            with open(filepath, "w") as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Migration report saved to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save migration report: {e!s}")
            raise

    def print_console(self, report: dict[str, Any]) -> None:
        """
        Print migration report to console.

        Args:
            report: Report dictionary
        """
        print("\n" + "=" * 80)
        print("MIGRATION REPORT")
        print("=" * 80)

        # Summary
        print("\n📊 SUMMARY")
        print("-" * 80)
        summary = report.get("summary", {})
        print(f"Status: {summary.get('overall_status', 'unknown').upper()}")
        print(f"Execution Time: {summary.get('execution_time_seconds', 0):.2f}s")
        print(f"Started: {summary.get('started_at')}")
        print(f"Completed: {summary.get('completed_at')}")

        # Total Records
        print("\n📈 RECORDS")
        print("-" * 80)
        print(f"Total Records: {report.get('total_records', 0)}")
        print(f"Migrated: {report.get('migrated_records', 0)}")
        print(f"Failed: {report.get('failed_records', 0)}")

        # By Component
        print("\n🔧 BY COMPONENT")
        print("-" * 80)
        by_component = report.get("by_component", {})
        for component, data in by_component.items():
            print(f"\n{component.upper()}:")
            print(f"  Total: {data.get('total', 0)}")
            print(f"  Migrated: {data.get('migrated', 0)}")
            print(f"  Failed: {data.get('failed', 0)}")

        # Warnings
        warnings = report.get("warnings", [])
        if warnings:
            print("\n⚠️  WARNINGS")
            print("-" * 80)
            for i, warning in enumerate(warnings, 1):
                print(f"{i}. {warning}")

        # Errors
        errors = report.get("errors", [])
        if errors:
            print("\n❌ ERRORS")
            print("-" * 80)
            for i, error in enumerate(errors, 1):
                print(f"{i}. {error}")

        # Recommendations
        recommendations = report.get("recommendations", [])
        if recommendations:
            print("\n💡 RECOMMENDATIONS")
            print("-" * 80)
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")

        print("\n" + "=" * 80 + "\n")

    def to_json_string(self, report: dict[str, Any]) -> str:
        """
        Convert report to JSON string.

        Args:
            report: Report dictionary

        Returns:
            JSON string representation
        """
        return json.dumps(report, indent=2, default=str)

    def get_summary(self, report: dict[str, Any]) -> str:
        """
        Get a concise summary of the migration report.

        Args:
            report: Report dictionary

        Returns:
            Summary string
        """
        summary = report.get("summary", {})
        _by_component = report.get("by_component", {})

        summary_str = (
            f"Migration {summary.get('overall_status').upper()} | "
            f"{report.get('migrated_records', 0)}/{report.get('total_records', 0)} "
            f"records migrated | "
            f"{summary.get('execution_time_seconds', 0):.1f}s"
        )

        # Add warnings/errors count if present
        if report.get("warnings"):
            summary_str += f" | {len(report['warnings'])} warning(s)"
        if report.get("errors"):
            summary_str += f" | {len(report['errors'])} error(s)"

        return summary_str
