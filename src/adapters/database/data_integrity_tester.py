"""Data integrity testing module"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class ConstraintType(Enum):
    """Types of integrity constraints."""

    PRIMARY_KEY = "primary_key"
    FOREIGN_KEY = "foreign_key"
    UNIQUE = "unique"
    NOT_NULL = "not_null"
    CHECK = "check"
    DEFAULT = "default"


@dataclass
class IntegrityConstraint:
    """
    Data integrity constraint definition.

    Attributes:
        constraint_type: Type of constraint
        column: Column name(s) affected
        reference_table: For foreign keys, the referenced table
        reference_column: For foreign keys, the referenced column
        condition: For CHECK constraints, the condition
        error_message: Custom error message if constraint is violated
    """

    constraint_type: ConstraintType
    column: str
    reference_table: Optional[str] = None
    reference_column: Optional[str] = None
    condition: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class IntegrityTestResult:
    """
    Result from data integrity test.

    Attributes:
        constraint: Constraint that was tested
        passed: Whether test passed
        violations: List of violations found
        sample_violations: Sample of violating records
        total_records: Total records checked
    """

    constraint: IntegrityConstraint
    passed: bool
    violations: List[Dict[str, Any]]
    sample_violations: List[Dict[str, Any]]
    total_records: int

    @property
    def violation_count(self) -> int:
        """Get total number of violations."""
        return len(self.violations)


class DataIntegrityTester:
    """
    Tester for database data integrity constraints.

    This class provides methods to test and validate data integrity
    constraints including primary keys, foreign keys, unique constraints,
    and check constraints.

    Example:
        tester = DataIntegrityTester(database_client)

        constraints = [
            IntegrityConstraint(
                constraint_type=ConstraintType.NOT_NULL,
                column="email",
                error_message="Email cannot be null"
            ),
            IntegrityConstraint(
                constraint_type=ConstraintType.UNIQUE,
                column="username",
                error_message="Username must be unique"
            )
        ]

        results = await tester.test_data_integrity(
            table="users",
            constraints=constraints
        )

        for result in results:
            if not result.passed:
                print(f"Constraint failed: {result.constraint.column}")
    """

    def __init__(self, database_client: Any):
        """
        Initialize data integrity tester.

        Args:
            database_client: Database client with query execution capability
        """
        self.db = database_client
        self._results: List[IntegrityTestResult] = []

    async def test_data_integrity(
        self, table: str, constraints: List[IntegrityConstraint]
    ) -> Dict[str, Any]:
        """
        Test data integrity constraints on a table.

        Args:
            table: Table name to test
            constraints: List of constraints to validate

        Returns:
            Dictionary with integrity test results
        """
        self._results = []

        for constraint in constraints:
            result = await self._test_constraint(table, constraint)
            self._results.append(result)

        # Analyze results
        passed_tests = [r for r in self._results if r.passed]
        failed_tests = [r for r in self._results if not r.passed]

        total_violations = sum(r.violation_count for r in failed_tests)

        return {
            "table": table,
            "total_constraints": len(constraints),
            "passed": len(passed_tests),
            "failed": len(failed_tests),
            "total_violations": total_violations,
            "results": [
                {
                    "constraint_type": r.constraint.constraint_type.value,
                    "column": r.constraint.column,
                    "passed": r.passed,
                    "violations": r.violation_count,
                    "sample_violations": r.sample_violations[:5],  # First 5
                }
                for r in self._results
            ],
            "recommendations": self._get_recommendations(failed_tests),
        }

    async def _test_constraint(
        self, table: str, constraint: IntegrityConstraint
    ) -> IntegrityTestResult:
        """
        Test a single integrity constraint.

        Args:
            table: Table name
            constraint: Constraint to test

        Returns:
            IntegrityTestResult with test details
        """
        test_methods = {
            ConstraintType.PRIMARY_KEY: self._test_primary_key,
            ConstraintType.FOREIGN_KEY: self._test_foreign_key,
            ConstraintType.UNIQUE: self._test_unique,
            ConstraintType.NOT_NULL: self._test_not_null,
            ConstraintType.CHECK: self._test_check,
            ConstraintType.DEFAULT: self._test_default,
        }

        test_method = test_methods.get(constraint.constraint_type)

        if test_method:
            return await test_method(table, constraint)
        else:
            return IntegrityTestResult(
                constraint=constraint,
                passed=False,
                violations=[{"error": f"Unknown constraint type: {constraint.constraint_type}"}],
                sample_violations=[],
                total_records=0,
            )

    async def _test_primary_key(
        self, table: str, constraint: IntegrityConstraint
    ) -> IntegrityTestResult:
        """Test primary key constraint."""
        query = f"""
            SELECT {constraint.column}, COUNT(*) as count
            FROM {table}
            GROUP BY {constraint.column}
            HAVING COUNT(*) > 1 OR {constraint.column} IS NULL
        """

        try:
            violations = await self.db.execute_query(query)
            violations_list = list(violations) if violations else []

            return IntegrityTestResult(
                constraint=constraint,
                passed=len(violations_list) == 0,
                violations=violations_list,
                sample_violations=violations_list[:10],
                total_records=await self._get_table_count(table),
            )
        except Exception as e:
            return IntegrityTestResult(
                constraint=constraint,
                passed=False,
                violations=[{"error": str(e)}],
                sample_violations=[],
                total_records=0,
            )

    async def _test_foreign_key(
        self, table: str, constraint: IntegrityConstraint
    ) -> IntegrityTestResult:
        """Test foreign key constraint."""
        if not constraint.reference_table or not constraint.reference_column:
            return IntegrityTestResult(
                constraint=constraint,
                passed=False,
                violations=[
                    {"error": "Foreign key constraint missing reference_table or reference_column"}
                ],
                sample_violations=[],
                total_records=0,
            )

        query = f"""
            SELECT t.{constraint.column}
            FROM {table} t
            LEFT JOIN {constraint.reference_table} r
                ON t.{constraint.column} = r.{constraint.reference_column}
            WHERE t.{constraint.column} IS NOT NULL
                AND r.{constraint.reference_column} IS NULL
        """

        try:
            violations = await self.db.execute_query(query)
            violations_list = list(violations) if violations else []

            return IntegrityTestResult(
                constraint=constraint,
                passed=len(violations_list) == 0,
                violations=violations_list,
                sample_violations=violations_list[:10],
                total_records=await self._get_table_count(table),
            )
        except Exception as e:
            return IntegrityTestResult(
                constraint=constraint,
                passed=False,
                violations=[{"error": str(e)}],
                sample_violations=[],
                total_records=0,
            )

    async def _test_unique(
        self, table: str, constraint: IntegrityConstraint
    ) -> IntegrityTestResult:
        """Test unique constraint."""
        query = f"""
            SELECT {constraint.column}, COUNT(*) as count
            FROM {table}
            GROUP BY {constraint.column}
            HAVING COUNT(*) > 1
        """

        try:
            violations = await self.db.execute_query(query)
            violations_list = list(violations) if violations else []

            return IntegrityTestResult(
                constraint=constraint,
                passed=len(violations_list) == 0,
                violations=violations_list,
                sample_violations=violations_list[:10],
                total_records=await self._get_table_count(table),
            )
        except Exception as e:
            return IntegrityTestResult(
                constraint=constraint,
                passed=False,
                violations=[{"error": str(e)}],
                sample_violations=[],
                total_records=0,
            )

    async def _test_not_null(
        self, table: str, constraint: IntegrityConstraint
    ) -> IntegrityTestResult:
        """Test not null constraint."""
        query = f"""
            SELECT *
            FROM {table}
            WHERE {constraint.column} IS NULL
        """

        try:
            violations = await self.db.execute_query(query)
            violations_list = list(violations) if violations else []

            return IntegrityTestResult(
                constraint=constraint,
                passed=len(violations_list) == 0,
                violations=violations_list,
                sample_violations=violations_list[:10],
                total_records=await self._get_table_count(table),
            )
        except Exception as e:
            return IntegrityTestResult(
                constraint=constraint,
                passed=False,
                violations=[{"error": str(e)}],
                sample_violations=[],
                total_records=0,
            )

    async def _test_check(self, table: str, constraint: IntegrityConstraint) -> IntegrityTestResult:
        """Test check constraint."""
        if not constraint.condition:
            return IntegrityTestResult(
                constraint=constraint,
                passed=False,
                violations=[{"error": "CHECK constraint missing condition"}],
                sample_violations=[],
                total_records=0,
            )

        query = f"""
            SELECT *
            FROM {table}
            WHERE NOT ({constraint.condition})
        """

        try:
            violations = await self.db.execute_query(query)
            violations_list = list(violations) if violations else []

            return IntegrityTestResult(
                constraint=constraint,
                passed=len(violations_list) == 0,
                violations=violations_list,
                sample_violations=violations_list[:10],
                total_records=await self._get_table_count(table),
            )
        except Exception as e:
            return IntegrityTestResult(
                constraint=constraint,
                passed=False,
                violations=[{"error": str(e)}],
                sample_violations=[],
                total_records=0,
            )

    async def _test_default(
        self, table: str, constraint: IntegrityConstraint
    ) -> IntegrityTestResult:
        """Test default value constraint."""
        # Default constraints are typically applied on insert,
        # so we just verify the column exists
        query = f"""
            SELECT COUNT(*) as count
            FROM {table}
            WHERE {constraint.column} IS NULL
        """

        try:
            result = await self.db.execute_query(query)
            _ = 0  # count result not used for DEFAULT constraints
            if result:
                row = next(iter(result))
                _ = row[0] if isinstance(row, (list, tuple)) else row.get("count", 0)

            return IntegrityTestResult(
                constraint=constraint,
                passed=True,  # Default constraints don't fail, they apply values
                violations=[],
                sample_violations=[],
                total_records=await self._get_table_count(table),
            )
        except Exception as e:
            return IntegrityTestResult(
                constraint=constraint,
                passed=False,
                violations=[{"error": str(e)}],
                sample_violations=[],
                total_records=0,
            )

    async def _get_table_count(self, table: str) -> int:
        """Get total record count for a table."""
        try:
            result = await self.db.execute_query(f"SELECT COUNT(*) FROM {table}")
            if result:
                row = next(iter(result))
                return int(row[0]) if isinstance(row, (list, tuple)) else int(row.get("count", 0))
            return 0
        except Exception:
            return 0

    def _get_recommendations(self, failed_tests: List[IntegrityTestResult]) -> List[str]:
        """Generate recommendations for failed tests."""
        if not failed_tests:
            return ["All data integrity constraints passed. Good job!"]

        recommendations = [
            f"Data integrity issues found in {len(failed_tests)} constraint(s)",
            "",
            "Recommended Actions:",
        ]

        for result in failed_tests:
            constraint = result.constraint
            recommendations.append(
                f"- {constraint.constraint_type.value.upper()} on '{constraint.column}': "
                f"{result.violation_count} violation(s)"
            )

            if constraint.constraint_type == ConstraintType.FOREIGN_KEY:
                recommendations.append(
                    f"  → Check referential integrity with {constraint.reference_table}.{constraint.reference_column}"
                )
            elif constraint.constraint_type == ConstraintType.UNIQUE:
                recommendations.append(
                    "  → Remove duplicate values or add composite unique constraint"
                )
            elif constraint.constraint_type == ConstraintType.NOT_NULL:
                recommendations.append("  → Update NULL values or modify constraint")

        recommendations.extend(
            [
                "",
                "Prevention:",
                "- Define constraints at database level",
                "- Validate data before insertion in application layer",
                "- Run integrity checks regularly",
            ]
        )

        return recommendations

    async def check_orphan_records(
        self, table: str, column: str, reference_table: str, reference_column: str
    ) -> Dict[str, Any]:
        """
        Check for orphan records in foreign key relationships.

        Args:
            table: Table to check
            column: Foreign key column
            reference_table: Referenced table
            reference_column: Referenced column

        Returns:
            Dictionary with orphan record analysis
        """
        query = f"""
            SELECT t.*
            FROM {table} t
            LEFT JOIN {reference_table} r
                ON t.{column} = r.{reference_column}
            WHERE t.{column} IS NOT NULL
                AND r.{reference_column} IS NULL
        """

        try:
            orphans = await self.db.execute_query(query)
            orphan_list = list(orphans) if orphans else []

            return {
                "table": table,
                "column": column,
                "reference": f"{reference_table}.{reference_column}",
                "orphan_count": len(orphan_list),
                "has_orphans": len(orphan_list) > 0,
                "sample_orphans": orphan_list[:10],
                "recommendation": (
                    "Delete orphan records or fix foreign key references"
                    if orphan_list
                    else "No orphan records found"
                ),
            }
        except Exception as e:
            return {"table": table, "column": column, "error": str(e)}
