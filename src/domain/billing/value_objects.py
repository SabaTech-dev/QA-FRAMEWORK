"""
Billing Value Objects

Immutable value objects used in the billing domain.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum


class Currency(Enum):
    """Supported currencies"""

    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class BillingPeriod(Enum):
    """Billing period types"""

    MONTHLY = "monthly"
    YEARLY = "yearly"
    QUARTERLY = "quarterly"


class BillingStatus(Enum):
    """Billing status for invoices/subscriptions"""

    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    UNCOLLECTIBLE = "uncollectible"
    VOID = "void"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Money:
    """
    Represents monetary values with proper decimal handling.

    Immutable value object that ensures accurate currency calculations.

    Example:
        >>> price = Money(amount=Decimal("99.99"), currency=Currency.USD)
        >>> print(price)  # $99.99 USD
    """

    amount: Decimal
    currency: Currency = Currency.USD

    def __post_init__(self):
        """Ensure amount is properly quantized"""
        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(
            self, "amount", Decimal(self.amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )

    @classmethod
    def from_cents(cls, cents: int, currency: Currency = Currency.USD) -> "Money":
        """Create Money from cents"""
        return cls(amount=Decimal(cents) / 100, currency=currency)

    def to_cents(self) -> int:
        """Convert to cents for Stripe API"""
        return int(self.amount * 100)

    def add(self, other: "Money") -> "Money":
        """Add two money values"""
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: "Money") -> "Money":
        """Subtract two money values"""
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, multiplier: Decimal) -> "Money":
        """Multiply by a factor"""
        return Money(self.amount * multiplier, self.currency)

    def is_zero(self) -> bool:
        """Check if amount is zero"""
        return self.amount == 0

    def is_positive(self) -> bool:
        """Check if amount is positive"""
        return self.amount > 0

    def is_negative(self) -> bool:
        """Check if amount is negative"""
        return self.amount < 0

    def __str__(self) -> str:
        """String representation"""
        if self.currency == Currency.USD:
            return f"${self.amount:.2f}"
        elif self.currency == Currency.EUR:
            return f"€{self.amount:.2f}"
        elif self.currency == Currency.GBP:
            return f"£{self.amount:.2f}"
        return f"{self.amount:.2f} {self.currency.value}"

    def __repr__(self) -> str:
        return f"Money(amount={self.amount}, currency={self.currency})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def __lt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError("Cannot compare different currencies")
        return self.amount < other.amount


@dataclass(frozen=True)
class BillingPeriodRange:
    """
    Represents a billing period with start and end dates.

    Immutable value object.
    """

    start_date: datetime
    end_date: datetime

    def __post_init__(self):
        """Validate dates"""
        if self.end_date <= self.start_date:
            raise ValueError("End date must be after start date")

    def contains(self, date: datetime) -> bool:
        """Check if date falls within this billing period"""
        return self.start_date <= date <= self.end_date

    def duration_days(self) -> int:
        """Get the duration of the period in days"""
        return (self.end_date - self.start_date).days

    @classmethod
    def current_month(cls) -> "BillingPeriodRange":
        """Create billing period for current month"""
        now = datetime.now(UTC)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if now.month == 12:
            end = start.replace(year=now.year + 1, month=1)
        else:
            end = start.replace(month=now.month + 1)
        return cls(start, end)

    def __str__(self) -> str:
        return f"{self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}"


@dataclass(frozen=True)
class UsageLimit:
    """
    Represents usage limits for a plan.

    Example:
        >>> limits = UsageLimit(
        ...     max_tests_per_month=10000,
        ...     max_users=10,
        ...     max_suites=50
        ... )
    """

    max_tests_per_month: int = -1  # -1 = unlimited
    max_users: int = -1
    max_suites: int = -1
    max_cases_per_suite: int = -1
    storage_gb: int = -1
    ai_features: bool = False
    api_access: bool = False
    priority_support: bool = False

    def is_unlimited(self, metric: str) -> bool:
        """Check if a metric is unlimited"""
        value = getattr(self, metric, None)
        return value == -1 if value is not None else False

    def exceeds_limit(self, metric: str, value: int) -> bool:
        """Check if value exceeds the limit for a metric"""
        limit = getattr(self, metric, -1)
        if limit == -1:
            return False  # Unlimited
        return value > limit
