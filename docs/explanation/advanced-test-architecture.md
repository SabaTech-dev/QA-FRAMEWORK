# Advanced Test Architecture Guide

## Overview

This guide documents the advanced test architecture patterns implemented in the QA Framework, providing sophisticated testing capabilities while maintaining Clean Architecture principles.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    TEST LAYER (Pytest)                      │
├─────────────────────────────────────────────────────────────┤
│                   PATTERN LAYER                              │
│  AAA Pattern  │  BDD Pattern  │  Table-Driven  │  Builder   │
├─────────────────────────────────────────────────────────────┤
│                   FACTORY LAYER                              │
│  UserFactory  │  ProductFactory │  OrderFactory │  APIReq   │
├─────────────────────────────────────────────────────────────┤
│                   FIXTURE LAYER                              │
│  Core │ Infrastructure │ Adapters │ Test Data │ Utils      │
├─────────────────────────────────────────────────────────────┤
│                   ADAPTER LAYER                              │
│  HTTP │ UI │ Database │ Security │ Performance │ Reporting  │
└─────────────────────────────────────────────────────────────┘
```

## Test Data Factories

### Factory Pattern Implementation

Factories provide a clean way to generate test data with sensible defaults while allowing customization:

```python
from tests.fixtures import UserFactory, ProductFactory, OrderFactory

# Basic usage
user = user_factory.create()
product = product_factory.create()
order = order_factory.create()

# With overrides
admin = user_factory.create(role="admin", username="custom_admin")
premium = product_factory.create(price=999.99, category="Premium")

# Batch creation
users = user_factory.create_batch(10, role="customer")
products = product_factory.create_batch(5, category="Electronics")
```

### Specialized Factory Methods

Each factory provides specialized methods for common scenarios:

```python
# UserFactory variations
admin = user_factory.admin(email="admin@company.com")
inactive = user_factory.inactive()
custom_domain = user_factory.with_email_domain("company.com")

# ProductFactory variations
out_of_stock = product_factory.out_of_stock()
premium = product_factory.premium()
electronics = product_factory.with_category("Electronics")

# OrderFactory variations
pending = order_factory.with_status("pending")
delivered = order_factory.with_status("delivered")
user_order = order_factory.for_user(user_id="12345")
```

## Object Mother Pattern

The Object Mother pattern centralizes creation of pre-configured test objects for common scenarios:

```python
from tests.fixtures import ObjectMother

def test_user_scenarios(object_mother: ObjectMother):
    # Get pre-configured valid user
    valid_user = object_mother.valid_user()
    
    # Get admin user
    admin = object_mother.admin_user()
    
    # Get inactive user
    inactive = object_mother.inactive_user()

def test_product_scenarios(object_mother: ObjectMother):
    # Different product states
    valid = object_mother.valid_product()
    out_of_stock = object_mother.out_of_stock_product()
    premium = object_mother.premium_product()

def test_order_scenarios(object_mother: ObjectMother):
    # Different order states
    pending = object_mother.pending_order()
    delivered = object_mother.delivered_order()
    cancelled = object_mother.cancelled_order()
```

## AAA Pattern (Arrange-Act-Assert)

The AAA pattern provides a clear structure for organizing tests:

```python
from tests.fixtures import AAAPattern

def test_user_creation_with_aaa(aaa_pattern: AAAPattern):
    # Arrange - Set up preconditions and inputs
    aaa_pattern.arrange(
        username="testuser",
        email="test@example.com",
        password="SecurePass123!"
    )
    
    # Act - Execute the action being tested
    def create_user(username: str, email: str, password: str):
        return {"id": "123", "username": username, "created": True}
    
    aaa_pattern.act(
        create_user,
        aaa_pattern.get_arranged('username'),
        aaa_pattern.get_arranged('email'),
        aaa_pattern.get_arranged('password')
    )
    
    # Assert - Verify expected outcomes
    result = aaa_pattern.get_result()
    aaa_pattern.assert_that(result['created'] is True)
    aaa_pattern.assert_equals("testuser", result['username'])
    aaa_pattern.assert_not_none(result['id'])
```

## BDD Pattern (Given-When-Then)

Behavior-Driven Development style tests for better readability:

```python
from tests.fixtures import GivenWhenThen

def test_user_login_scenario(bdd_scenario: GivenWhenThen):
    scenario = (bdd_scenario
        .given("a registered user exists", user_id="123", username="john_doe")
        .given("the user is on the login page")
        .when("the user enters valid credentials",
              action=lambda: {"success": True, "token": "abc123"})
        .then("the user should be logged in")
        .then("a session token should be generated")
    )
    
    # Access context data
    context = scenario.get_context()
    assert context['user_id'] == "123"
    assert context['result']['success'] is True
    
    # Get full scenario description
    print(scenario.get_scenario_description())
```

## Table-Driven Tests

Execute the same test logic with multiple inputs:

```python
from tests.fixtures import TableDrivenTests

def test_calculator_operations():
    table = TableDrivenTests()
    table.add_case("add positive", (2, 3), 5)
    table.add_case("add negative", (-2, -3), -5)
    table.add_case("add zero", (0, 5), 5)
    table.add_case("subtract", (5, 3, "sub"), 2)
    
    def calculator(input_data):
        a, b, *rest = input_data
        if rest and rest[0] == "sub":
            return a - b
        return a + b
    
    results = table.run(calculator)
    
    for result in results:
        assert result['passed'], f"Failed: {result['name']}"
```

## Data Builder Pattern

Build complex objects step by step:

```python
from tests.fixtures import DataBuilder, TestScenarioBuilder

def test_data_builder():
    builder = DataBuilder()
    data = (builder
        .with_id()
        .with_name("Test Product")
        .with_email()
        .with_metadata(category="Electronics", priority="high")
        .with_field("custom_field", "custom_value")
        .build()
    )
    
def test_scenario_builder():
    scenario = (TestScenarioBuilder()
        .with_user(username="john", email="john@example.com")
        .with_products(count=5, category="Books")
        .with_orders(count=2, status="pending")
        .build()
    )
```

## Test Isolation

Ensure tests don't interfere with each other:

```python
from tests.fixtures import TestIsolationManager

def test_isolated_resources():
    isolation = TestIsolationManager()
    
    # Register setup and teardown hooks
    isolation.on_setup(lambda: print("Setting up..."))
    isolation.on_teardown(lambda: print("Cleaning up..."))
    
    # Use context manager for automatic cleanup
    with isolation.isolated_context():
        # Test code here
        pass
    # Teardown runs automatically
```

## Retry Pattern

Handle flaky operations with retry logic:

```python
from tests.fixtures import RetryPattern

def test_with_retry():
    retry = RetryPattern(max_retries=3, delay=1.0, backoff=2.0)
    
    def flaky_operation():
        # Might fail occasionally
        return "success"
    
    # Execute with retry
    result = retry.execute(flaky_operation)
    
    # Or use as decorator
    @retry.decorator
    def another_flaky_op():
        return "success"
```

## Advanced Fixtures Organization

Fixtures are organized by architectural layers:

### Core Layer Fixtures
```python
@pytest.fixture
def faker_instance(worker_id: str) -> Faker:
    # Worker-seeded faker for reproducibility
    pass

@pytest.fixture
def test_config() -> Dict[str, Any]:
    # Test configuration
    pass
```

### Infrastructure Layer Fixtures
```python
@pytest.fixture
def mock_database() -> MagicMock:
    # Mock database for unit tests
    pass

@pytest.fixture
def mock_cache() -> MagicMock:
    # Mock cache
    pass

@pytest.fixture
def resource_lock() -> threading.Lock:
    # Thread-safe lock
    pass
```

### Adapter Layer Fixtures
```python
@pytest.fixture
def mock_http_client() -> MagicMock:
    # Mock HTTP client
    pass

@pytest.fixture
def mock_ui_driver() -> MagicMock:
    # Mock UI driver
    pass
```

### Test Data Fixtures
```python
@pytest.fixture
def user_factory(faker_instance: Faker) -> UserFactory:
    # User factory instance
    pass

@pytest.fixture
def object_mother(faker_instance: Faker) -> ObjectMother:
    # Object mother instance
    pass
```

## Best Practices

### 1. Use Factories for Test Data

```python
# Good
def test_user_creation(user_factory):
    user = user_factory.create(role="admin")
    assert user.role == "admin"

# Avoid
def test_user_creation():
    user = User(
        id=str(uuid4()),
        username="test",
        email="test@test.com",
        # ... many more fields
    )
```

### 2. Use AAA Pattern for Structure

```python
# Good
def test_api_response(aaa_pattern):
    # Arrange
    aaa_pattern.arrange(expected_status=200)
    
    # Act
    aaa_pattern.act(make_api_call)
    
    # Assert
    aaa_pattern.assert_equals(200, aaa_pattern.get_result().status)

# Avoid
def test_api_response():
    expected_status = 200
    response = make_api_call()
    assert response.status == expected_status
```

### 3. Use Object Mother for Common Scenarios

```python
# Good
def test_admin_access(object_mother):
    admin = object_mother.admin_user()
    assert has_admin_access(admin)

# Avoid
def test_admin_access(user_factory):
    admin = user_factory.create(role="admin", username="admin", ...)
    assert has_admin_access(admin)
```

### 4. Isolate Tests Properly

```python
# Good
def test_database_operation(test_isolation, mock_database):
    with test_isolation.isolated_context():
        # Test with isolated resources
        pass

# Avoid
def test_database_operation():
    # Directly using shared resources
    db.execute("DELETE FROM users")  # Dangerous!
```

## Integration with CI/CD

The advanced test architecture is fully integrated with the CI/CD pipeline:

- **Unit Tests**: Run with `pytest tests/unit -n auto`
- **Integration Tests**: Run with `pytest tests/integration`
- **Parallel Execution**: Uses pytest-xdist for faster feedback
- **Coverage**: Integrated with Codecov for coverage reporting

## Performance Considerations

1. **Factory Caching**: Faker instances are cached per worker
2. **Lazy Evaluation**: Test data is generated only when needed
3. **Parallel Safety**: All fixtures are designed for parallel execution
4. **Resource Cleanup**: Automatic cleanup via context managers

## Conclusion

The advanced test architecture provides:

- ✅ **Clean Architecture**: Maintains separation of concerns
- ✅ **SOLID Principles**: Single responsibility, open/closed, etc.
- ✅ **Maintainability**: Easy to understand and modify
- ✅ **Scalability**: Supports parallel execution
- ✅ **Flexibility**: Multiple patterns for different scenarios
- ✅ **Type Safety**: Full type hints throughout

For more examples, see `tests/examples/test_advanced_patterns.py`.
