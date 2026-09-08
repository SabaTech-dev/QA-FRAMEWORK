"""
Contract tests for the stripe-python v15 migration (API 2025-03-31.basil).

Covers the two mandatory code changes documented in
reports/opencode/qafw-stripe-migration-plan-2026-08-27.md:

- R1: current_period_start/end now live on SubscriptionItem (items.data[0])
- R2: Invoice.payment_intent was replaced by the InvoicePayment resource
      (Invoice.payments); client_secret must be resolved from both shapes.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("stripe", reason="stripe not installed. Install with: pip install stripe")

# The billing service lives under dashboard/backend (imported as `services.*`
# with that directory on sys.path, matching how the FastAPI app runs).
BACKEND_ROOT = Path(__file__).resolve().parents[3] / "dashboard" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from services.stripe_service import _resolve_client_secret


def _pre_basil_invoice(client_secret: str):
    return SimpleNamespace(
        payment_intent=SimpleNamespace(client_secret=client_secret), payments=None
    )


def _basil_invoice(client_secret: str):
    return SimpleNamespace(
        payment_intent=None,
        payments=SimpleNamespace(
            data=[SimpleNamespace(payment=SimpleNamespace(client_secret=client_secret))]
        ),
    )


class TestResolveClientSecret:
    def test_pre_basil_shape(self):
        invoice = _pre_basil_invoice("cs_test_pre_basil")
        assert _resolve_client_secret(invoice) == "cs_test_pre_basil"

    def test_basil_shape(self):
        invoice = _basil_invoice("cs_test_basil")
        assert _resolve_client_secret(invoice) == "cs_test_basil"

    def test_missing_invoice_returns_none(self):
        assert _resolve_client_secret(None) is None

    def test_invoice_without_payment_returns_none(self):
        assert _resolve_client_secret(SimpleNamespace()) is None


class TestBasilSubscriptionShape:
    def test_period_fields_live_on_subscription_item(self):
        """Documents the dahlia/basil contract: the Subscription root no longer
        carries current_period_start/end; they are on items.data[0]."""
        sub = SimpleNamespace(
            items=SimpleNamespace(
                data=[
                    SimpleNamespace(current_period_start=1700000000, current_period_end=1702592000)
                ]
            )
        )
        assert not hasattr(sub, "current_period_start")
        assert not hasattr(sub, "current_period_end")
        first_item = sub.items.data[0]
        assert first_item.current_period_start == 1700000000
        assert first_item.current_period_end == 1702592000
