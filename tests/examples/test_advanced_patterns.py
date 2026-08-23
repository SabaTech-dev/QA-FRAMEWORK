"""
Examples demonstrating advanced test architecture patterns.

This module showcases:
- AAA Pattern usage
- BDD/Gherkin style tests
- Table-driven tests
- Factory patterns
- Test data builders
"""

import pytest

from tests.fixtures.factories import ObjectMother, UserFactory
from tests.fixtures.patterns import (
    AAAPattern,
    GivenWhenThen,
    TableDrivenTests,
    create_isolation_manager,
)


class TestAAAPattern:
    """Examples using Arrange-Act-Assert pattern."""

    def test_user_creation_with_aaa(self, aaa_pattern: AAAPattern) -> None:
        """Example: Create user using AAA pattern."""
        # Arrange
        aaa_pattern.arrange(
            username="testuser", email="test@example.com", password="SecurePass123!"
        )

        # Act
        def create_user(username: str, email: str, password: str) -> dict:
            return {"id": "12345", "username": username, "email": email, "created": True}

        aaa_pattern.act(
            create_user,
            aaa_pattern.get_arranged("username"),
            aaa_pattern.get_arranged("email"),
            aaa_pattern.get_arranged("password"),
        )

        # Assert
        result = aaa_pattern.get_result()
        aaa_pattern.assert_that(result["created"] is True, "User should be created")
        aaa_pattern.assert_equals("testuser", result["username"])
        aaa_pattern.assert_not_none(result["id"])

    def test_api_response_with_aaa(self, aaa_pattern: AAAPattern) -> None:
        """Example: Test API response using AAA pattern."""
        # Arrange
        expected_status = 200
        expected_data = {"users": [], "total": 0}

        # Act
        def mock_api_call() -> dict:
            return {"status": 200, "data": {"users": [], "total": 0}}

        aaa_pattern.act(mock_api_call)

        # Assert
        response = aaa_pattern.get_result()
        aaa_pattern.assert_equals(expected_status, response["status"])
        aaa_pattern.assert_equals(expected_data, response["data"])


class TestBDDPattern:
    """Examples using BDD (Given-When-Then) pattern."""

    def test_user_login_scenario(self, bdd_scenario: GivenWhenThen) -> None:
        """Example: User login scenario in BDD style."""
        scenario = (
            bdd_scenario.given("a registered user exists", user_id="123", username="john_doe")
            .given("the user is on the login page")
            .when(
                "the user enters valid credentials",
                action=lambda: {"success": True, "token": "abc123"},
            )
            .then("the user should be logged in", assertion=lambda: True)
            .then("a session token should be generated")
        )

        print(f"\n{scenario.get_scenario_description()}")

        # Verify context
        context = scenario.get_context()
        assert context["user_id"] == "123"
        assert "result" in context

    def test_product_purchase_scenario(self, bdd_scenario: GivenWhenThen) -> None:
        """Example: Product purchase scenario in BDD style."""
        bdd_scenario.given("a user has items in their cart", items_count=3).given(
            "the user is on the checkout page"
        ).when(
            "the user confirms the purchase",
            action=lambda: {"order_id": "ORD-123", "status": "confirmed"},
        ).then(
            "an order should be created"
        ).then(
            "the cart should be emptied"
        ).and_(
            "a confirmation email should be sent"
        )


class TestTableDriven:
    """Examples using Table-Driven test pattern."""

    def test_calculator_with_table(self) -> None:
        """Example: Table-driven test for calculator."""
        table = TableDrivenTests()
        table.add_case("add positive", (2, 3), 5, "Adding positive numbers").add_case(
            "add negative", (-2, -3), -5, "Adding negative numbers"
        ).add_case("add zero", (0, 5), 5, "Adding zero").add_case(
            "add mixed", (5, 3), 8, "Adding mixed positive numbers"
        )

        def calculator(input_data: tuple) -> int:
            a, b = input_data
            return a + b  # Simple addition for demo

        results = table.run(calculator)

        for result in results:
            assert result["passed"], f"Test case '{result['name']}' failed: {result['error']}"

    def test_validation_with_table(self) -> None:
        """Example: Table-driven validation test."""
        table = TableDrivenTests()
        table.add_case("valid email", "user@example.com", True, "Valid email format").add_case(
            "invalid email", "invalid-email", False, "Invalid email format"
        ).add_case("empty email", "", False, "Empty email should be invalid")

        def validate_email(email: str) -> bool:
            import re

            pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
            return bool(re.match(pattern, email))

        results = table.run(validate_email)

        for result in results:
            assert result["passed"], f"Test case '{result['name']}' failed"


class TestDataTablePattern:
    """Examples using Data Table pattern."""

    def test_user_roles_with_data_table(self, test_data_table: callable) -> None:
        """Example: Test user permissions with data table."""
        table = test_data_table(["role", "can_read", "can_write", "can_delete"])
        table.add_row(role="admin", can_read=True, can_write=True, can_delete=True).add_row(
            role="editor", can_read=True, can_write=True, can_delete=False
        ).add_row(role="viewer", can_read=True, can_write=False, can_delete=False)

        # Test each role
        for row in table.to_list():
            role = row["role"]
            if role == "admin":
                assert row["can_read"] and row["can_write"] and row["can_delete"]
            elif role == "editor":
                assert row["can_read"] and row["can_write"] and not row["can_delete"]
            elif role == "viewer":
                assert row["can_read"] and not row["can_write"] and not row["can_delete"]


class TestFactoryPattern:
    """Examples using Factory pattern for test data."""

    def test_user_factory_basic(self, user_factory: UserFactory) -> None:
        """Example: Create user with factory."""
        user = user_factory.create()

        assert user.id is not None
        assert user.username is not None
        assert user.email is not None
        assert user.is_active is True

    def test_user_factory_batch(self, user_factory: UserFactory) -> None:
        """Example: Create multiple users."""
        users = user_factory.create_batch(5, role="customer")

        assert len(users) == 5
        assert all(u.role == "customer" for u in users)

    def test_user_factory_variations(self, user_factory: UserFactory) -> None:
        """Example: Create different user types."""
        admin = user_factory.admin()
        inactive = user_factory.inactive()
        custom_domain = user_factory.with_email_domain("company.com")

        assert admin.role == "admin"
        assert not inactive.is_active
        assert custom_domain.email.endswith("@company.com")

    def test_product_factory_with_category(self, product_factory: UserFactory) -> None:
        """Example: Create products with specific categories."""
        electronics = product_factory.with_category("Electronics")
        clothing = product_factory.with_category("Clothing")

        assert electronics.category == "Electronics"
        assert clothing.category == "Clothing"


class TestObjectMotherPattern:
    """Examples using Object Mother pattern."""

    def test_valid_user_scenario(self, object_mother: ObjectMother) -> None:
        """Example: Get pre-configured valid user."""
        user = object_mother.valid_user()

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True

    def test_admin_user_scenario(self, object_mother: ObjectMother) -> None:
        """Example: Get pre-configured admin user."""
        admin = object_mother.admin_user()

        assert admin.role == "admin"
        assert admin.username == "admin"

    def test_product_scenarios(self, object_mother: ObjectMother) -> None:
        """Example: Different product scenarios."""
        valid = object_mother.valid_product()
        out_of_stock = object_mother.out_of_stock_product()
        premium = object_mother.premium_product()

        assert valid.stock_quantity > 0
        assert out_of_stock.stock_quantity == 0
        assert premium.price >= 500

    def test_order_scenarios(self, object_mother: ObjectMother) -> None:
        """Example: Different order scenarios."""
        pending = object_mother.pending_order()
        delivered = object_mother.delivered_order()
        cancelled = object_mother.cancelled_order()

        assert pending.status == "pending"
        assert delivered.status == "delivered"
        assert cancelled.status == "cancelled"


class TestIsolationPattern:
    """Examples using Test Isolation pattern."""

    def test_isolated_resource_access(self) -> None:
        """Example: Test with isolated resources."""
        isolation = create_isolation_manager()

        resource_value = {"count": 0}

        def setup():
            resource_value["count"] = 0

        def cleanup():
            resource_value["count"] = -1

        isolation.on_setup(setup).on_teardown(cleanup)

        with isolation.isolated_context():
            # Test operations
            resource_value["count"] += 1
            assert resource_value["count"] == 1

        # After context, cleanup should have run
        assert resource_value["count"] == -1


class TestRetryPattern:
    """Examples using Retry pattern for flaky operations."""

    def test_retry_with_success(self, retry_handler: callable) -> None:
        """Example: Retry pattern with eventual success."""
        call_count = [0]

        def flaky_operation():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = retry_handler.execute(flaky_operation)

        assert result == "success"
        assert call_count[0] == 3


class TestBuilderPattern:
    """Examples using Builder pattern for complex objects."""

    def test_complex_object_builder(self, object_mother: ObjectMother) -> None:
        """Example: Build complex test scenario."""
        from tests.fixtures.factories import TestScenarioBuilder

        builder = TestScenarioBuilder()
        scenario = (
            builder.with_user(username="john_doe", email="john@example.com")
            .with_products(count=5, category="Electronics")
            .with_orders(count=2, status="pending")
            .build()
        )

        assert scenario["user"] is not None
        assert len(scenario["products"]) == 5
        assert len(scenario["orders"]) == 2


# Example of parameterized test using the new fixtures
@pytest.mark.parametrize(
    "role,expected_permission",
    [
        ("admin", "all"),
        ("editor", "read_write"),
        ("viewer", "read_only"),
    ],
)
def test_role_permissions_with_parametrization(
    role: str, expected_permission: str, user_factory: UserFactory
) -> None:
    """Example: Parameterized test with factory."""
    user = user_factory.create(role=role)

    assert user.role == role

    # Permission logic would be tested here
    permissions = {"admin": "all", "editor": "read_write", "viewer": "read_only"}

    assert permissions.get(role) == expected_permission
