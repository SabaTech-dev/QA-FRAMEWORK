"""Migration infrastructure for multi-tenant data migration."""

# Export MigrationStatus enum
from .migrator import DataMigrator
from .migrator import DataMigrator as DataMigratorType
from .migrator import DataMigrator as _DataMigrator
from .report_generator import MigrationReportGenerator
from .test_migrator import TestMigrator
from .user_migrator import UserMigrator

__all__ = [
    "DataMigrator",
    "DataMigratorType",
    "MigrationReportGenerator",
    "MigrationStatus",
    "TestMigrator",
    "UserMigrator",
]

MigrationStatus = _DataMigrator.MigrationStatus
