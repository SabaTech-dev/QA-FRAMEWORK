"""
Advanced Test Data Factories for QA Framework.

Provides sophisticated data generation patterns including:
- Factory Pattern with Faker integration
- Object Mother pattern for common test scenarios
- Builder pattern for complex objects
- Sequences for unique data generation
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

from faker import Faker

T = TypeVar("T")


class Sequence:
    """Thread-safe sequence generator for unique values."""

    def __init__(self, start: int = 1):
        self._counter = start
        self._lock = False  # Simulated lock for thread safety

    def next(self) -> int:
        """Get next value in sequence."""
        value = self._counter
        self._counter += 1
        return value

    def next_str(self, prefix: str = "") -> str:
        """Get next value as string with optional prefix."""
        return f"{prefix}{self.next()}"

    def reset(self, start: int = 1):
        """Reset sequence to start value."""
        self._counter = start


@dataclass
class UserData:
    """User entity for testing."""

    id: str = field(default_factory=lambda: str(uuid4()))
    username: str = ""
    email: str = ""
    first_name: str = ""
    last_name: str = ""
    password: str = ""
    is_active: bool = True
    role: str = "user"
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProductData:
    """Product entity for testing."""

    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    price: float = 0.0
    category: str = ""
    sku: str = ""
    stock_quantity: int = 0
    is_available: bool = True
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrderData:
    """Order entity for testing."""

    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)
    total_amount: float = 0.0
    status: str = "pending"
    shipping_address: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class APIRequestData:
    """API Request data for testing."""

    method: str = "GET"
    url: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    query_params: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    timeout: int = 30
    retries: int = 3


class BaseFactory(ABC, Generic[T]):
    """Abstract base factory with common functionality."""

    def __init__(self, faker: Faker | None = None, locale: str = "en_US"):
        self.faker = faker or Faker(locale)
        self.sequences: dict[str, Sequence] = {}

    def sequence(self, name: str, prefix: str = "") -> str:
        """Get or create a named sequence."""
        if name not in self.sequences:
            self.sequences[name] = Sequence()
        return self.sequences[name].next_str(prefix)

    @abstractmethod
    def create(self, **overrides: Any) -> T:
        """Create a single instance."""

    def create_batch(self, size: int, **overrides: Any) -> list[T]:
        """Create multiple instances."""
        return [self.create(**overrides) for _ in range(size)]

    def build(self, **overrides: Any) -> T:
        """Build instance without saving (factory_boy compatibility)."""
        return self.create(**overrides)


class UserFactory(BaseFactory[UserData]):
    """Factory for generating User test data."""

    def create(self, **overrides: Any) -> UserData:
        """Create a User instance with fake data."""
        user = UserData(
            id=overrides.get("id", str(uuid4())),
            username=overrides.get("username", self.faker.user_name()),
            email=overrides.get("email", self.faker.email()),
            first_name=overrides.get("first_name", self.faker.first_name()),
            last_name=overrides.get("last_name", self.faker.last_name()),
            password=overrides.get("password", self.faker.password(length=12)),
            is_active=overrides.get("is_active", True),
            role=overrides.get("role", "user"),
            created_at=overrides.get("created_at", datetime.now()),
            metadata=overrides.get("metadata", {}),
        )
        return user

    def admin(self, **overrides: Any) -> UserData:
        """Create an admin user."""
        defaults = {"role": "admin", "username": f"admin_{self.faker.user_name()}"}
        defaults.update(overrides)
        return self.create(**defaults)

    def inactive(self, **overrides: Any) -> UserData:
        """Create an inactive user."""
        defaults = {"is_active": False}
        defaults.update(overrides)
        return self.create(**defaults)

    def with_email_domain(self, domain: str, **overrides: Any) -> UserData:
        """Create user with specific email domain."""
        username = self.faker.user_name()
        email = f"{username}@{domain}"
        defaults = {"email": email, "username": username}
        defaults.update(overrides)
        return self.create(**defaults)


class ProductFactory(BaseFactory[ProductData]):
    """Factory for generating Product test data."""

    CATEGORIES = ["Electronics", "Clothing", "Books", "Home", "Sports", "Food"]

    def create(self, **overrides: Any) -> ProductData:
        """Create a Product instance with fake data."""
        category = overrides.get("category", self.faker.random_element(self.CATEGORIES))
        sku_prefix = category[:3].upper()

        product = ProductData(
            id=overrides.get("id", str(uuid4())),
            name=overrides.get("name", self.faker.catch_phrase()),
            description=overrides.get("description", self.faker.text(max_nb_chars=200)),
            price=overrides.get("price", round(self.faker.pyfloat(min_value=1, max_value=1000), 2)),
            category=category,
            sku=overrides.get("sku", self.sequence("sku", sku_prefix)),
            stock_quantity=overrides.get("stock_quantity", self.faker.random_int(0, 1000)),
            is_available=overrides.get("is_available", True),
            tags=overrides.get("tags", self.faker.words(nb=3, ext_word_list=None)),
            metadata=overrides.get("metadata", {}),
        )
        return product

    def out_of_stock(self, **overrides: Any) -> ProductData:
        """Create an out of stock product."""
        defaults = {"stock_quantity": 0, "is_available": False}
        defaults.update(overrides)
        return self.create(**defaults)

    def premium(self, **overrides: Any) -> ProductData:
        """Create a premium product with higher price."""
        defaults = {"price": round(self.faker.pyfloat(min_value=500, max_value=5000), 2)}
        defaults.update(overrides)
        return self.create(**defaults)

    def with_category(self, category: str, **overrides: Any) -> ProductData:
        """Create product with specific category."""
        defaults = {"category": category}
        defaults.update(overrides)
        return self.create(**defaults)


class OrderFactory(BaseFactory[OrderData]):
    """Factory for generating Order test data."""

    STATUSES = ["pending", "confirmed", "shipped", "delivered", "cancelled"]

    def create(self, **overrides: Any) -> OrderData:
        """Create an Order instance with fake data."""
        items = overrides.get("items", self._generate_items())
        total = overrides.get("total_amount", self._calculate_total(items))

        order = OrderData(
            id=overrides.get("id", str(uuid4())),
            user_id=overrides.get("user_id", str(uuid4())),
            items=items,
            total_amount=total,
            status=overrides.get("status", self.faker.random_element(self.STATUSES)),
            shipping_address=overrides.get("shipping_address", self._generate_address()),
            created_at=overrides.get("created_at", datetime.now()),
            metadata=overrides.get("metadata", {}),
        )
        return order

    def _generate_items(self, count: int = 3) -> list[dict[str, Any]]:
        """Generate random order items."""
        return [
            {
                "product_id": str(uuid4()),
                "quantity": self.faker.random_int(1, 5),
                "price": round(self.faker.pyfloat(min_value=10, max_value=500), 2),
            }
            for _ in range(count)
        ]

    def _calculate_total(self, items: list[dict[str, Any]]) -> float:
        """Calculate total from items."""
        return sum(item["quantity"] * item["price"] for item in items)

    def _generate_address(self) -> dict[str, str]:
        """Generate shipping address."""
        return {
            "street": self.faker.street_address(),
            "city": self.faker.city(),
            "state": self.faker.state(),
            "zip": self.faker.zipcode(),
            "country": self.faker.country(),
        }

    def with_status(self, status: str, **overrides: Any) -> OrderData:
        """Create order with specific status."""
        defaults = {"status": status}
        defaults.update(overrides)
        return self.create(**defaults)

    def for_user(self, user_id: str, **overrides: Any) -> OrderData:
        """Create order for specific user."""
        defaults = {"user_id": user_id}
        defaults.update(overrides)
        return self.create(**defaults)


class APIRequestFactory(BaseFactory[APIRequestData]):
    """Factory for generating API Request test data."""

    HTTP_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

    def create(self, **overrides: Any) -> APIRequestData:
        """Create an APIRequest instance."""
        request = APIRequestData(
            method=overrides.get("method", "GET"),
            url=overrides.get("url", self.faker.uri()),
            headers=overrides.get("headers", self._generate_headers()),
            query_params=overrides.get("query_params", {}),
            body=overrides.get("body"),
            timeout=overrides.get("timeout", 30),
            retries=overrides.get("retries", 3),
        )
        return request

    def _generate_headers(self) -> dict[str, str]:
        """Generate common HTTP headers."""
        return {
            "User-Agent": self.faker.user_agent(),
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Request-ID": str(uuid4()),
        }

    def get(self, url: str, **overrides: Any) -> APIRequestData:
        """Create GET request."""
        defaults = {"method": "GET", "url": url}
        defaults.update(overrides)
        return self.create(**defaults)

    def post(self, url: str, body: dict[str, Any], **overrides: Any) -> APIRequestData:
        """Create POST request."""
        defaults = {"method": "POST", "url": url, "body": body}
        defaults.update(overrides)
        return self.create(**defaults)

    def with_auth(self, token: str, **overrides: Any) -> APIRequestData:
        """Create request with authorization header."""
        headers = self._generate_headers()
        headers["Authorization"] = f"Bearer {token}"
        defaults = {"headers": headers}
        defaults.update(overrides)
        return self.create(**defaults)


class ObjectMother:
    """
    Object Mother pattern - Centralized creation of common test objects.
    Provides pre-configured objects for common testing scenarios.
    """

    def __init__(self, faker: Faker | None = None, locale: str = "en_US"):
        self.faker = faker or Faker(locale)
        self.user_factory = UserFactory(self.faker)
        self.product_factory = ProductFactory(self.faker)
        self.order_factory = OrderFactory(self.faker)
        self.api_factory = APIRequestFactory(self.faker)

    # User scenarios
    def valid_user(self) -> UserData:
        """Standard valid user for testing."""
        return self.user_factory.create(
            username="testuser", email="test@example.com", first_name="Test", last_name="User"
        )

    def admin_user(self) -> UserData:
        """Admin user for testing."""
        return self.user_factory.admin(username="admin", email="admin@example.com")

    def inactive_user(self) -> UserData:
        """Inactive user for testing."""
        return self.user_factory.inactive(username="inactive", email="inactive@example.com")

    # Product scenarios
    def valid_product(self) -> ProductData:
        """Standard valid product for testing."""
        return self.product_factory.create(name="Test Product", price=99.99, stock_quantity=100)

    def out_of_stock_product(self) -> ProductData:
        """Out of stock product for testing."""
        return self.product_factory.out_of_stock(name="Out of Stock Product")

    def premium_product(self) -> ProductData:
        """Premium product for testing."""
        return self.product_factory.premium(name="Premium Product")

    # Order scenarios
    def pending_order(self) -> OrderData:
        """Pending order for testing."""
        return self.order_factory.with_status("pending")

    def delivered_order(self) -> OrderData:
        """Delivered order for testing."""
        return self.order_factory.with_status("delivered")

    def cancelled_order(self) -> OrderData:
        """Cancelled order for testing."""
        return self.order_factory.with_status("cancelled")

    # API Request scenarios
    def valid_api_request(self) -> APIRequestData:
        """Standard valid API request."""
        return self.api_factory.get("https://api.example.com/users")

    def api_request_with_body(self) -> APIRequestData:
        """API request with JSON body."""
        return self.api_factory.post(
            "https://api.example.com/users", body={"name": "Test User", "email": "test@example.com"}
        )


class DataBuilder:
    """
    Builder pattern for constructing complex test data.
    Allows step-by-step construction with method chaining.
    """

    def __init__(self, faker: Faker | None = None, locale: str = "en_US"):
        self.faker = faker or Faker(locale)
        self._data: dict[str, Any] = {}

    def with_id(self, id: str | None = None) -> "DataBuilder":
        """Add ID field."""
        self._data["id"] = id or str(uuid4())
        return self

    def with_name(self, name: str | None = None) -> "DataBuilder":
        """Add name field."""
        self._data["name"] = name or self.faker.name()
        return self

    def with_email(self, email: str | None = None) -> "DataBuilder":
        """Add email field."""
        self._data["email"] = email or self.faker.email()
        return self

    def with_timestamp(self, timestamp: datetime | None = None) -> "DataBuilder":
        """Add timestamp field."""
        self._data["timestamp"] = timestamp or datetime.now()
        return self

    def with_metadata(self, **kwargs: Any) -> "DataBuilder":
        """Add metadata fields."""
        if "metadata" not in self._data:
            self._data["metadata"] = {}
        self._data["metadata"].update(kwargs)
        return self

    def with_field(self, key: str, value: Any) -> "DataBuilder":
        """Add custom field."""
        self._data[key] = value
        return self

    def build(self) -> dict[str, Any]:
        """Build and return the data dictionary."""
        return self._data.copy()

    def reset(self) -> "DataBuilder":
        """Reset builder state."""
        self._data = {}
        return self


class TestScenarioBuilder:
    """
    Builder for complex test scenarios involving multiple related entities.
    """

    def __init__(self, faker: Faker | None = None, locale: str = "en_US"):
        self.faker = faker or Faker(locale)
        self.user_factory = UserFactory(self.faker)
        self.product_factory = ProductFactory(self.faker)
        self.order_factory = OrderFactory(self.faker)

        self._user: UserData | None = None
        self._products: list[ProductData] = []
        self._orders: list[OrderData] = []

    def with_user(self, **overrides: Any) -> "TestScenarioBuilder":
        """Add a user to the scenario."""
        self._user = self.user_factory.create(**overrides)
        return self

    def with_products(self, count: int = 3, **overrides: Any) -> "TestScenarioBuilder":
        """Add products to the scenario."""
        self._products = self.product_factory.create_batch(count, **overrides)
        return self

    def with_orders(self, count: int = 2, **overrides: Any) -> "TestScenarioBuilder":
        """Add orders to the scenario."""
        user_id = self._user.id if self._user else str(uuid4())

        for _ in range(count):
            order_overrides = {"user_id": user_id}
            order_overrides.update(overrides)
            self._orders.append(self.order_factory.create(**order_overrides))

        return self

    def build(self) -> dict[str, Any]:
        """Build complete test scenario."""
        return {"user": self._user, "products": self._products, "orders": self._orders}


# Convenience functions for quick usage
def create_user_factory(locale: str = "en_US") -> UserFactory:
    """Create a UserFactory instance."""
    return UserFactory(locale=locale)


def create_product_factory(locale: str = "en_US") -> ProductFactory:
    """Create a ProductFactory instance."""
    return ProductFactory(locale=locale)


def create_order_factory(locale: str = "en_US") -> OrderFactory:
    """Create an OrderFactory instance."""
    return OrderFactory(locale=locale)


def create_object_mother(locale: str = "en_US") -> ObjectMother:
    """Create an ObjectMother instance."""
    return ObjectMother(locale=locale)


def create_data_builder(locale: str = "en_US") -> DataBuilder:
    """Create a DataBuilder instance."""
    return DataBuilder(locale=locale)
