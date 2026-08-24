"""SQL query validation module"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class SQLIssue:
    """
    SQL validation issue.

    Attributes:
        severity: Issue severity level
        message: Issue description
        line_number: Line where issue was found
        suggestion: Suggested fix
    """

    severity: ValidationSeverity
    message: str
    line_number: int
    suggestion: str


@dataclass
class SQLValidationResult:
    """
    SQL validation result.

    Attributes:
        is_valid: Whether query passed all validations
        issues: List of found issues
        warnings: List of warnings
        suggestions: List of optimization suggestions
    """

    is_valid: bool
    issues: list[SQLIssue]
    warnings: list[SQLIssue]
    suggestions: list[SQLIssue]

    def has_errors(self) -> bool:
        """Check if result has any errors."""
        return any(i.severity == ValidationSeverity.ERROR for i in self.issues)

    def has_warnings(self) -> bool:
        """Check if result has any warnings."""
        return len(self.warnings) > 0


class SQLValidator:
    """
    Validator for SQL queries.

    This class provides comprehensive SQL validation including syntax checking,
    performance analysis, and security vulnerability detection.

    Example:
        validator = SQLValidator()

        result = validator.validate_query(
            "SELECT * FROM users WHERE id = 1"
        )

        if not result.is_valid:
            for issue in result.issues:
                print(f"{issue.severity.value}: {issue.message}")
    """

    # SQL keywords that indicate potential issues
    DANGEROUS_KEYWORDS = [
        "DROP",
        "DELETE",
        "TRUNCATE",
        "ALTER",
        "EXEC",
        "EXECUTE",
        "UNION",
        "INSERT",
        "UPDATE",
    ]

    # Performance anti-patterns
    PERFORMANCE_PATTERNS = [
        (r"SELECT\s+\*", "SELECT * can impact performance, specify columns explicitly"),
        (r'LIKE\s+[\'"]%', "Leading wildcard in LIKE prevents index usage"),
        (r"OR\s+\w+\s*=\s*\w+", "OR conditions can prevent index usage, consider UNION"),
        (r"NOT\s+IN\s*\(", "NOT IN with subqueries can be slow, use NOT EXISTS"),
        (r"HAVING\s+\w+\s*=", "HAVING with equality filter, use WHERE instead"),
    ]

    # Security patterns
    SECURITY_PATTERNS = [
        (r"\$\w+|%s|\?\?", "Potential SQL injection - use parameterized queries"),
        (r'EXEC\s*\(\s*["\']', "Dynamic SQL execution, verify input sanitization"),
        (r"xp_", "Extended stored procedures, potential security risk"),
        (r"--.*|\/\*.*\*\/", "Comments in SQL, potential SQL injection vector"),
    ]

    def __init__(self) -> None:
        """Initialize SQL validator."""
        self._issues: list[SQLIssue] = []
        self._warnings: list[SQLIssue] = []
        self._suggestions: list[SQLIssue] = []

    def validate_syntax(self, query: str) -> SQLValidationResult:
        """
        Validate SQL query syntax.

        Args:
            query: SQL query to validate

        Returns:
            SQLValidationResult with validation details
        """
        self._reset()

        if not query or not query.strip():
            self._issues.append(
                SQLIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Query is empty",
                    line_number=0,
                    suggestion="Provide a valid SQL query",
                )
            )
            return SQLValidationResult(False, self._issues, self._warnings, self._suggestions)

        # Basic syntax checks
        lines = query.split("\n")

        # Check for unclosed quotes
        for i, line in enumerate(lines, 1):
            single_quotes = line.count("'") - line.count("\\'")
            double_quotes = line.count('"') - line.count('\\"')

            if single_quotes % 2 != 0:
                self._issues.append(
                    SQLIssue(
                        severity=ValidationSeverity.ERROR,
                        message=f"Unclosed single quote on line {i}",
                        line_number=i,
                        suggestion="Close the string literal with a single quote",
                    )
                )

            if double_quotes % 2 != 0:
                self._warnings.append(
                    SQLIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Unclosed double quote on line {i}",
                        line_number=i,
                        suggestion="Close the identifier with a double quote or use single quotes for strings",
                    )
                )

        # Check for unclosed parentheses
        open_parens = query.count("(")
        close_parens = query.count(")")
        if open_parens != close_parens:
            self._issues.append(
                SQLIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Unbalanced parentheses: {open_parens} open, {close_parens} close",
                    line_number=0,
                    suggestion="Ensure all opening parentheses have matching closing parentheses",
                )
            )

        # Check basic query structure
        query_upper = query.upper().strip()

        if not any(
            query_upper.startswith(kw)
            for kw in ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "WITH"]
        ):
            self._warnings.append(
                SQLIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Query doesn't start with a standard SQL keyword",
                    line_number=1,
                    suggestion="Ensure query starts with SELECT, INSERT, UPDATE, DELETE, etc.",
                )
            )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in self._issues)

        return SQLValidationResult(is_valid, self._issues, self._warnings, self._suggestions)

    def check_performance_issues(self, query: str) -> SQLValidationResult:
        """
        Check for common SQL performance issues.

        Args:
            query: SQL query to analyze

        Returns:
            SQLValidationResult with performance issues found
        """
        self._reset()

        query_upper = query.upper()

        # Check performance patterns
        for pattern, message in self.PERFORMANCE_PATTERNS:
            matches = re.finditer(pattern, query_upper, re.IGNORECASE)
            for match in matches:
                line_num = self._get_line_number(query, match.start())
                self._suggestions.append(
                    SQLIssue(
                        severity=ValidationSeverity.WARNING,
                        message=message,
                        line_number=line_num,
                        suggestion=self._get_performance_suggestion(pattern),
                    )
                )

        # Check for missing WHERE clause in UPDATE/DELETE
        if re.search(r"^\s*(UPDATE|DELETE)", query_upper):
            if "WHERE" not in query_upper:
                self._issues.append(
                    SQLIssue(
                        severity=ValidationSeverity.ERROR,
                        message="UPDATE or DELETE without WHERE clause - will affect all rows!",
                        line_number=1,
                        suggestion="Add a WHERE clause to limit affected rows",
                    )
                )

        # Check for DISTINCT overuse
        if re.search(r"SELECT\s+DISTINCT", query_upper):
            self._warnings.append(
                SQLIssue(
                    severity=ValidationSeverity.WARNING,
                    message="DISTINCT can be expensive, consider if it's necessary",
                    line_number=self._get_line_number(query_upper, query_upper.find("DISTINCT")),
                    suggestion="Review if DISTINCT is needed or if query can be rewritten",
                )
            )

        # Check for implicit conversions
        if re.search(r'WHERE\s+\w+\s*=\s*["\']\d+["\']', query, re.IGNORECASE):
            self._warnings.append(
                SQLIssue(
                    severity=ValidationSeverity.WARNING,
                    message="Implicit type conversion in WHERE clause",
                    line_number=1,
                    suggestion="Match column and value types to avoid implicit conversion",
                )
            )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in self._issues)

        return SQLValidationResult(is_valid, self._issues, self._warnings, self._suggestions)

    def check_security_issues(self, query: str) -> SQLValidationResult:
        """
        Check for SQL security issues like injection vulnerabilities.

        Args:
            query: SQL query to analyze

        Returns:
            SQLValidationResult with security issues found
        """
        self._reset()

        query_upper = query.upper()

        # Check for string concatenation (potential injection)
        if re.search(r'["\']\s*\+\s*\w+', query) or re.search(r'\w+\s*\+\s*["\']', query):
            self._issues.append(
                SQLIssue(
                    severity=ValidationSeverity.ERROR,
                    message="String concatenation detected - SQL injection risk!",
                    line_number=self._get_line_number(query, query.find("+")),
                    suggestion="Use parameterized queries or prepared statements",
                )
            )

        # Check for dangerous keywords without proper context
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                self._warnings.append(
                    SQLIssue(
                        severity=ValidationSeverity.WARNING,
                        message=f"Dangerous keyword '{keyword}' found",
                        line_number=self._get_line_number(query_upper, query_upper.find(keyword)),
                        suggestion=f"Ensure {keyword} operation is properly authorized and logged",
                    )
                )

        # Check security patterns
        for pattern, message in self.SECURITY_PATTERNS:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                line_num = self._get_line_number(query, match.start())
                self._issues.append(
                    SQLIssue(
                        severity=ValidationSeverity.ERROR,
                        message=message,
                        line_number=line_num,
                        suggestion="Use parameterized queries with bound variables",
                    )
                )

        # Check for password in query (shouldn't happen!)
        if re.search(r'(password|pwd|passwd)\s*=\s*["\'][^"\']+["\']', query, re.IGNORECASE):
            self._issues.append(
                SQLIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Hardcoded password detected in query!",
                    line_number=1,
                    suggestion="Never hardcode passwords. Use secure credential storage",
                )
            )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in self._issues)

        return SQLValidationResult(is_valid, self._issues, self._warnings, self._suggestions)

    def analyze_query_plan(self, query: str) -> dict[str, Any]:
        """
        Analyze query execution plan (simplified version).

        Note: This is a basic analysis. For actual execution plans,
        you would need database-specific EXPLAIN commands.

        Args:
            query: SQL query to analyze

        Returns:
            Dictionary with query plan analysis
        """
        analysis: dict[str, Any] = {
            "query_type": None,
            "tables": [],
            "columns": [],
            "joins": [],
            "where_conditions": 0,
            "order_by_columns": [],
            "group_by_columns": [],
            "estimated_complexity": "low",
            "suggestions": [],
        }

        query_upper = query.upper()

        # Determine query type
        if query_upper.strip().startswith("SELECT"):
            analysis["query_type"] = "SELECT"
        elif query_upper.strip().startswith("INSERT"):
            analysis["query_type"] = "INSERT"
        elif query_upper.strip().startswith("UPDATE"):
            analysis["query_type"] = "UPDATE"
        elif query_upper.strip().startswith("DELETE"):
            analysis["query_type"] = "DELETE"

        # Extract table names
        from_match = re.search(r"FROM\s+(\w+)", query_upper)
        if from_match:
            analysis["tables"].append(from_match.group(1))

        join_matches = re.findall(r"JOIN\s+(\w+)", query_upper)
        analysis["tables"].extend(join_matches)
        analysis["joins"] = join_matches

        # Count WHERE conditions
        where_conditions = re.findall(
            r"WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)", query_upper, re.DOTALL
        )
        if where_conditions:
            analysis["where_conditions"] = (
                len(re.findall(r"\bAND\b|\bOR\b", where_conditions[0])) + 1
            )

        # Extract ORDER BY columns
        order_match = re.search(r"ORDER\s+BY\s+(.+?)(?:LIMIT|$)", query_upper, re.DOTALL)
        if order_match:
            analysis["order_by_columns"] = [c.strip() for c in order_match.group(1).split(",")]

        # Extract GROUP BY columns
        group_match = re.search(
            r"GROUP\s+BY\s+(.+?)(?:ORDER|HAVING|LIMIT|$)", query_upper, re.DOTALL
        )
        if group_match:
            analysis["group_by_columns"] = [c.strip() for c in group_match.group(1).split(",")]

        # Estimate complexity
        complexity_score = 0
        complexity_score += len(analysis["joins"]) * 2
        complexity_score += analysis["where_conditions"]
        complexity_score += len(analysis["order_by_columns"])
        complexity_score += len(analysis["group_by_columns"]) * 2

        if complexity_score > 10:
            analysis["estimated_complexity"] = "high"
            analysis["suggestions"].append("Consider query optimization or caching")
        elif complexity_score > 5:
            analysis["estimated_complexity"] = "medium"

        return analysis

    def validate_query(self, query: str) -> SQLValidationResult:
        """
        Perform complete query validation (syntax + performance + security).

        Args:
            query: SQL query to validate

        Returns:
            SQLValidationResult with all validation issues
        """
        # Run all validations
        syntax_result = self.validate_syntax(query)
        performance_result = self.check_performance_issues(query)
        security_result = self.check_security_issues(query)

        # Combine all issues
        all_issues = syntax_result.issues + performance_result.issues + security_result.issues
        all_warnings = (
            syntax_result.warnings + performance_result.warnings + security_result.warnings
        )
        all_suggestions = (
            syntax_result.suggestions + performance_result.suggestions + security_result.suggestions
        )

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in all_issues)

        return SQLValidationResult(is_valid, all_issues, all_warnings, all_suggestions)

    def _reset(self) -> None:
        """Reset all issue lists."""
        self._issues = []
        self._warnings = []
        self._suggestions = []

    def _get_line_number(self, text: str, position: int) -> int:
        """Get line number for a character position."""
        return text[:position].count("\n") + 1

    def _get_performance_suggestion(self, pattern: str) -> str:
        """Get suggestion for performance issue."""
        suggestions = {
            r"SELECT\s+\*": "Specify only needed columns: SELECT col1, col2 FROM...",
            r'LIKE\s+[\'"]%': "Remove leading wildcard or use full-text search",
            r"OR\s+\w+\s*=\s*\w+": "Use IN clause or UNION instead of multiple OR conditions",
            r"NOT\s+IN\s*\(": "Use NOT EXISTS or LEFT JOIN with IS NULL",
            r"HAVING\s+\w+\s*=": "Move filter to WHERE clause when possible",
        }
        return suggestions.get(pattern, "Review query for optimization opportunities")
