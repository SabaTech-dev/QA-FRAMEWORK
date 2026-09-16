"""
Database Testing Example - QA-FRAMEWORK

This example demonstrates how to use the Database Testing Module
to validate SQL queries, test data integrity, and verify migrations.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.adapters.database import (
    DatabaseClient,
    SQLiteClient,
    SQLValidator,
    DataIntegrityTester,
    MigrationTester,
    IntegrityConstraint,
)
from src.adapters.database.data_integrity_tester import ConstraintType


async def example_sql_validation():
    """
    Example 1: Validate SQL queries.

    This demonstrates how to validate SQL queries for syntax,
    performance issues, and security vulnerabilities.
    """
    print("=" * 60)
    print("EXAMPLE 1: SQL Query Validation")
    print("=" * 60)

    validator = SQLValidator()

    # Example queries to validate
    queries = [
        # Valid query
        "SELECT id, name, email FROM users WHERE status = 'active'",
        # Query with potential performance issues
        "SELECT * FROM users WHERE name LIKE '%john%'",
        # Query with security issues
        "SELECT * FROM users WHERE id = " + "1 OR 1=1",  # nosec B608 — deliberate injection demo, never executed
        # Query with syntax error (unclosed quote)
        "SELECT * FROM users WHERE name = 'john",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\nQuery {i}:")
        print(f"  SQL: {query[:50]}...")

        # Validate the query
        result = validator.validate_query(query)

        print(f"  Valid: {result.is_valid}")
        print(f"  Has Errors: {result.has_errors()}")
        print(f"  Has Warnings: {result.has_warnings()}")

        if result.issues:
            print(f"  Issues:")
            for issue in result.issues[:2]:  # Show first 2 issues
                print(f"    [{issue.severity.value.upper()}] {issue.message}")

        if result.suggestions:
            print(f"  Suggestions:")
            for suggestion in result.suggestions[:1]:
                print(f"    • {suggestion.message}")


async def example_database_connection():
    """
    Example 2: Connect to database and execute queries.

    This demonstrates how to use the SQLiteClient to connect
    to a database and execute queries.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Database Connection")
    print("=" * 60)

    # Use in-memory SQLite database for testing
    client = SQLiteClient(":memory:")

    try:
        # Connect to database
        await client.connect()
        print("\nConnected to in-memory SQLite database")

        # Create a test table
        await client.execute_query("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL,
                age INTEGER,
                status TEXT DEFAULT 'active'
            )
        """)
        print("Created 'users' table")

        # Insert test data
        await client.execute_query("""
            INSERT INTO users (username, email, age) VALUES
            ('john_doe', 'john@example.com', 30),
            ('jane_doe', 'jane@example.com', 25),
            ('bob_smith', 'bob@example.com', 35)
        """)
        print("Inserted test data")

        # Query data
        results = await client.execute_query("SELECT * FROM users")
        print(f"\nUsers in database: {len(results)}")
        for row in results:
            print(f"  ID: {row[0]}, Username: {row[1]}, Email: {row[2]}")

        # Get schema info
        schema = await client.get_schema_info()
        print(f"\nSchema Info:")
        print(f"  Tables: {schema['tables']}")

        await client.disconnect()
        print("\nDisconnected from database")

    except Exception as e:
        print(f"Error: {e}")


async def example_data_integrity():
    """
    Example 3: Test data integrity constraints.

    This demonstrates how to validate that data follows
    defined integrity constraints.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Data Integrity Testing")
    print("=" * 60)

    client = SQLiteClient(":memory:")

    try:
        await client.connect()

        # Create table with constraints
        await client.execute_query("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending'
            )
        """)

        # Create reference table
        await client.execute_query("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE
            )
        """)

        # Insert users
        await client.execute_query("""
            INSERT INTO users (id, username) VALUES (1, 'user1'), (2, 'user2')
        """)

        # Insert valid orders
        await client.execute_query("""
            INSERT INTO orders (id, user_id, total_amount) VALUES
            (1, 1, 100.00),
            (2, 2, 200.00),
            (3, 1, 150.00)
        """)

        # Insert order with NULL (to test NOT NULL constraint)
        await client.execute_query("""
            INSERT INTO orders (id, user_id, total_amount) VALUES (4, NULL, 50.00)
        """)

        print("\nDatabase setup complete")

        # Define integrity constraints
        constraints = [
            IntegrityConstraint(
                constraint_type=ConstraintType.NOT_NULL,
                column="user_id",
                error_message="User ID cannot be null",
            ),
            IntegrityConstraint(
                constraint_type=ConstraintType.NOT_NULL,
                column="total_amount",
                error_message="Total amount cannot be null",
            ),
            IntegrityConstraint(
                constraint_type=ConstraintType.FOREIGN_KEY,
                column="user_id",
                reference_table="users",
                reference_column="id",
                error_message="User ID must reference valid user",
            ),
        ]

        # Test data integrity
        results = await client.test_data_integrity(table="orders", constraints=constraints)

        print(f"\nIntegrity Test Results:")
        print(f"  Table: {results['table']}")
        print(f"  Total Constraints: {results['total_constraints']}")
        print(f"  Passed: {results['passed']}")
        print(f"  Failed: {results['failed']}")
        print(f"  Total Violations: {results['total_violations']}")

        print(f"\n  Constraint Results:")
        for result in results["results"]:
            status = "✓ PASS" if result["passed"] else "✗ FAIL"
            print(f"    {status}: {result['constraint_type']} on '{result['column']}'")
            if result["violations"] > 0:
                print(f"       Violations: {result['violations']}")

        await client.disconnect()

    except Exception as e:
        print(f"Error: {e}")


async def example_migration_testing():
    """
    Example 4: Test database migrations.

    This demonstrates how to test migration scripts for
    correctness and rollback capability.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Migration Testing")
    print("=" * 60)

    client = SQLiteClient(":memory:")

    try:
        await client.connect()

        # Create initial schema
        await client.execute_query("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        print("\nInitial schema created")

        # Define migration SQL (add price column)
        migration_sql = """
            ALTER TABLE products ADD COLUMN price REAL DEFAULT 0.0;
            ALTER TABLE products ADD COLUMN category TEXT;
        """

        # Define rollback SQL
        rollback_sql = """
            -- SQLite doesn't support DROP COLUMN directly
            -- In real scenario, you'd recreate the table
        """

        print("Running migration...")

        # Test migration
        # Note: For this example, we'll validate the SQL rather than execute
        validator = SQLValidator()
        validation = validator.validate_query(migration_sql)

        print(f"\nMigration Validation:")
        print(f"  Valid SQL: {validation.is_valid}")
        print(f"  Changes: Add 'price' column, Add 'category' column")

        # Execute migration
        await client.execute_query(migration_sql)
        print("  Migration executed successfully")

        # Verify schema change
        schema = await client.get_schema_info()
        products_columns = [c["name"] for c in schema["columns"].get("products", [])]
        print(f"  Products table columns: {products_columns}")

        await client.disconnect()

    except Exception as e:
        print(f"Error: {e}")


async def example_orphan_records():
    """
    Example 5: Check for orphan records.

    This demonstrates how to identify orphan records
    in foreign key relationships.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Orphan Records Detection")
    print("=" * 60)

    client = SQLiteClient(":memory:")

    try:
        await client.connect()

        # Create tables with foreign key relationship
        await client.execute_query("""
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)

        await client.execute_query("""
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                department_id INTEGER
            )
        """)

        # Insert departments
        await client.execute_query("""
            INSERT INTO departments (id, name) VALUES
            (1, 'Engineering'),
            (2, 'Sales')
        """)

        # Insert employees (some with invalid department_id)
        await client.execute_query("""
            INSERT INTO employees (id, name, department_id) VALUES
            (1, 'Alice', 1),
            (2, 'Bob', 1),
            (3, 'Charlie', 2),
            (4, 'David', 999),  -- Orphan: department 999 doesn't exist
            (5, 'Eve', 999)     -- Orphan: department 999 doesn't exist
        """)

        print("\nDatabase setup complete")
        print("  Departments: 2")
        print("  Employees: 5 (2 with invalid department_id)")

        # Check for orphan records
        orphan_check = await client.check_orphan_records(
            table="employees",
            column="department_id",
            reference_table="departments",
            reference_column="id",
        )

        print(f"\nOrphan Records Check:")
        print(f"  Table: {orphan_check['table']}")
        print(f"  Column: {orphan_check['column']}")
        print(f"  Reference: {orphan_check['reference']}")
        print(f"  Orphan Count: {orphan_check['orphan_count']}")
        print(f"  Has Orphans: {orphan_check['has_orphans']}")

        if orphan_check["has_orphans"]:
            print(f"\n  Sample Orphans:")
            for orphan in orphan_check["sample_orphans"][:3]:
                print(f"    Employee ID: {orphan[0]}, Name: {orphan[1]}, Dept ID: {orphan[2]}")

        print(f"\n  Recommendation: {orphan_check['recommendation']}")

        await client.disconnect()

    except Exception as e:
        print(f"Error: {e}")


async def example_query_performance_analysis():
    """
    Example 6: Analyze query performance.

    This demonstrates how to analyze SQL queries for
    performance characteristics.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Query Performance Analysis")
    print("=" * 60)

    validator = SQLValidator()

    # Example queries to analyze
    queries = [
        ("SELECT * FROM users", "SELECT * query"),
        ("SELECT id, name FROM users WHERE email = 'test@example.com'", "Specific column query"),
        ("SELECT * FROM orders WHERE customer_name LIKE '%john%'", "LIKE with wildcard"),
        (
            "SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id WHERE u.status = 'active' ORDER BY o.created_at",
            "Complex join query",
        ),
    ]

    for sql, description in queries:
        print(f"\nQuery: {description}")
        print(f"  SQL: {sql[:60]}...")

        # Analyze query plan
        analysis = validator.analyze_query_plan(sql)

        print(f"  Analysis:")
        print(f"    Type: {analysis['query_type']}")
        print(f"    Tables: {analysis['tables']}")
        print(f"    Joins: {len(analysis['joins'])}")
        print(f"    Where Conditions: {analysis['where_conditions']}")
        print(f"    Order By: {analysis['order_by_columns']}")
        print(f"    Complexity: {analysis['estimated_complexity']}")

        if analysis["suggestions"]:
            print(f"    Suggestions:")
            for suggestion in analysis["suggestions"]:
                print(f"      • {suggestion}")


async def main():
    """Run all examples."""
    print("QA-FRAMEWORK: Database Testing Examples")
    print("=" * 60)

    # Run examples
    await example_sql_validation()
    await example_database_connection()
    await example_data_integrity()
    await example_migration_testing()
    await example_orphan_records()
    await example_query_performance_analysis()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
