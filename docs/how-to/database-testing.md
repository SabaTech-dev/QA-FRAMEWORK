# Database Testing Module

The Database Testing Module provides comprehensive database testing capabilities including SQL validation, data integrity testing, and migration testing.

## Overview

This module helps ensure database quality and reliability:
- **SQL Validation**: Validates SQL queries for syntax, performance, and security
- **Data Integrity**: Tests constraints and data consistency
- **Migration Testing**: Tests database migrations and rollbacks
- **Schema Validation**: Validates database schema structure

## Architecture

```
src/adapters/database/
├── __init__.py              # Module exports
├── database_client.py       # Main database client
├── sql_validator.py        # SQL query validation
├── data_integrity_tester.py # Data integrity testing
└── migration_tester.py     # Migration testing
```

## Quick Start

### SQL Query Validation

```python
from src.adapters.database import SQLValidator

validator = SQLValidator()

# Validate a query
result = validator.validate_query("""
    SELECT id, name, email 
    FROM users 
    WHERE status = 'active'
""")

if not result.is_valid:
    print("Validation errors:")
    for issue in result.issues:
        print(f"  [{issue.severity.value}] {issue.message}")
        print(f"    Suggestion: {issue.suggestion}")

if result.suggestions:
    print("\nOptimization suggestions:")
    for suggestion in result.suggestions:
        print(f"  • {suggestion.message}")
```

### Database Connection (SQLite)

```python
from src.adapters.database import SQLiteClient

async def test_database():
    # Connect to SQLite (in-memory or file)
    client = SQLiteClient(":memory:")  # or "mydatabase.db"
    
    await client.connect()
    
    # Execute queries
    await client.execute_query("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL
        )
    """)
    
    # Insert data
    await client.execute_query("""
        INSERT INTO users (username, email) 
        VALUES ('john_doe', 'john@example.com')
    """)
    
    # Query data
    results = await client.execute_query("SELECT * FROM users")
    for row in results:
        print(f"User: {row[1]}, Email: {row[2]}")
    
    await client.disconnect()
```

### Data Integrity Testing

```python
from src.adapters.database import DataIntegrityTester, IntegrityConstraint
from src.adapters.database.data_integrity_tester import ConstraintType

async def test_integrity():
    client = SQLiteClient("mydb.db")
    await client.connect()
    
    tester = DataIntegrityTester(client)
    
    # Define constraints
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
        ),
        IntegrityConstraint(
            constraint_type=ConstraintType.FOREIGN_KEY,
            column="user_id",
            reference_table="users",
            reference_column="id",
            error_message="User ID must reference valid user"
        )
    ]
    
    # Test integrity
    results = await tester.test_data_integrity(
        table="users",
        constraints=constraints
    )
    
    print(f"Total constraints: {results['total_constraints']}")
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Total violations: {results['total_violations']}")
    
    await client.disconnect()
```

### Migration Testing

```python
from src.adapters.database import MigrationTester

async def test_migration():
    client = SQLiteClient(":memory:")
    await client.connect()
    
    tester = MigrationTester(client)
    
    # Test a migration
    result = await tester.test_migration(
        migration_script="migrations/001_add_users_table.sql",
        rollback_script="migrations/001_add_users_table_rollback.sql"
    )
    
    print(f"Migration: {result.migration_name}")
    print(f"Status: {result.status.value}")
    print(f"Execution time: {result.execution_time:.3f}s")
    
    if result.warnings:
        print(f"Warnings: {result.warnings}")
    
    await client.disconnect()
```

## Components

### SQLValidator

Validates SQL queries for syntax, performance, and security issues:

```python
from src.adapters.database import SQLValidator

validator = SQLValidator()

# Validate syntax
result = validator.validate_syntax("SELECT * FROM users")

# Check performance issues
result = validator.check_performance_issues("SELECT * FROM large_table")

# Check security issues
result = validator.check_security_issues(
    "SELECT * FROM users WHERE id = '" + user_input + "'"
)

# Get query plan analysis
analysis = validator.analyze_query_plan("""
    SELECT u.*, o.* 
    FROM users u 
    JOIN orders o ON u.id = o.user_id 
    WHERE u.status = 'active'
""")

print(f"Tables: {analysis['tables']}")
print(f"Joins: {analysis['joins']}")
print(f"Complexity: {analysis['estimated_complexity']}")
```

### DataIntegrityTester

Tests data integrity constraints:

```python
from src.adapters.database import DataIntegrityTester, IntegrityConstraint
from src.adapters.database.data_integrity_tester import ConstraintType

# Available constraint types:
# - PRIMARY_KEY
# - FOREIGN_KEY
# - UNIQUE
# - NOT_NULL
# - CHECK
# - DEFAULT

constraints = [
    IntegrityConstraint(
        constraint_type=ConstraintType.CHECK,
        column="age",
        condition="age >= 18 AND age <= 120",
        error_message="Age must be between 18 and 120"
    )
]

results = await tester.test_data_integrity("users", constraints)

# Check for orphan records
orphan_results = await tester.check_orphan_records(
    table="orders",
    column="user_id",
    reference_table="users",
    reference_column="id"
)
```

### MigrationTester

Tests database migrations:

```python
from src.adapters.database import MigrationTester

tester = MigrationTester(client)

# Test single migration
result = await tester.test_migration(
    migration_script="path/to/migration.sql",
    rollback_script="path/to/rollback.sql",
    validate_after=True
)

# Test migration chain
migrations = [
    {"migration": "001_create_users.sql", "rollback": "001_rollback.sql"},
    {"migration": "002_create_orders.sql", "rollback": "002_rollback.sql"}
]

chain_results = await tester.test_migration_chain(migrations)

# Check idempotency
idempotency_results = await tester.validate_migration_idempotency(
    migration_script="migration.sql"
)

# Check compatibility
compatibility = await tester.check_migration_compatibility(
    migration_script="migration.sql",
    existing_schema=current_schema
)
```

### DatabaseClient

Base class for database connections:

```python
from src.adapters.database import DatabaseClient

# Implement database-specific client
class PostgreSQLClient(DatabaseClient):
    async def connect(self):
        # Implementation
        pass
    
    async def execute_query(self, query, params=None):
        # Implementation
        pass
    
    async def get_schema_info(self):
        # Implementation
        pass
```

### SQLiteClient

Built-in SQLite implementation:

```python
from src.adapters.database import SQLiteClient

# In-memory database (for testing)
client = SQLiteClient(":memory:")

# File-based database
client = SQLiteClient("production.db")

# Use as context manager
async with SQLiteClient("test.db") as client:
    results = await client.execute_query("SELECT * FROM users")
    schema = await client.get_schema_info()
```

## Configuration

Add to your `config/qa.yaml`:

```yaml
database:
  default_timeout: 30
  
  sql_validation:
    enabled: true
    check_syntax: true
    check_performance: true
    check_security: true
  
  integrity:
    enabled: true
    check_primary_keys: true
    check_foreign_keys: true
    check_unique_constraints: true
    check_not_null: true
    sample_size: 1000
  
  migrations:
    enabled: true
    validate_idempotency: true
    test_rollbacks: true
    backup_before_migration: true
  
  connections:
    sqlite:
      database: "test.db"
    postgresql:
      host: ${DB_HOST:localhost}
      port: ${DB_PORT:5432}
      database: ${DB_NAME:test}
      user: ${DB_USER:postgres}
      password: ${DB_PASSWORD:}
```

## SQL Validation Rules

### Syntax Validation

- Unclosed quotes detection
- Unbalanced parentheses detection
- Invalid statement structure
- Missing semicolons

### Performance Validation

- **SELECT ***: Suggests specifying columns
- **LIKE with wildcards**: Suggests full-text search
- **OR conditions**: Suggests UNION
- **Missing indexes**: Suggests index creation
- **Implicit conversions**: Suggests type matching

### Security Validation

- **String concatenation**: SQL injection risk
- **Dynamic SQL**: Execution risks
- **Hardcoded passwords**: Security vulnerability
- **Missing WHERE**: Dangerous UPDATE/DELETE
- **Dangerous keywords**: DROP, TRUNCATE warnings

## Best Practices

1. **Validate Before Execution**: Always validate SQL before running
2. **Test Migrations**: Test both forward and rollback scripts
3. **Check Constraints**: Regular integrity checks
4. **Use Transactions**: Wrap tests in transactions
5. **Monitor Performance**: Analyze query plans
6. **Test with Real Data**: Use production-like data volumes

## Testing Patterns

### Unit Testing with SQLite

```python
import pytest

@pytest.fixture
async def db():
    client = SQLiteClient(":memory:")
    await client.connect()
    yield client
    await client.disconnect()

async def test_user_creation(db):
    await db.execute_query("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)
    """)
    
    await db.execute_query(
        "INSERT INTO users (name) VALUES (?)",
        {"name": "John"}
    )
    
    results = await db.execute_query("SELECT * FROM users")
    assert len(results) == 1
```

### Migration Testing

```python
async def test_migration():
    async with SQLiteClient(":memory:") as db:
        tester = MigrationTester(db)
        
        # Apply migration
        result = await tester.test_migration("add_column.sql")
        assert result.status == MigrationStatus.SUCCESS
        
        # Verify schema change
        schema = await db.get_schema_info()
        assert "new_column" in [c['name'] for c in schema['columns']['my_table']]
        
        # Test rollback
        assert result.rollback_successful is True
```

## Troubleshooting

### Query Validation Errors

If queries fail validation:
1. Review specific error messages
2. Check line numbers provided
3. Apply suggested fixes
4. Re-validate

### Migration Failures

If migrations fail:
1. Check SQL syntax
2. Verify table/column existence
3. Test rollback separately
4. Check for idempotency issues

### Integrity Test Failures

If integrity tests fail:
1. Review constraint definitions
2. Check for data quality issues
3. Consider data cleanup
4. Update constraints if needed

## Examples

See `examples/database_testing_example.py` for complete working examples.