"""
Integration smoke: POST /billing/subscribe flow — pure mocks, no Stripe keys.

Exercises the REAL HTTP path (TestClient) through the FastAPI route ->
stripe_service -> (mocked) stripe SDK, including basil-era (API 2025-03-31)
client_secret resolution from Invoice.payments (InvoicePayment resource).

No sk_live_/sk_test_ keys are used or required: stripe.api_key resolves to
None in test settings and every SDK call is patched at the service boundary.

Card 7c37a29f QA leg (Re: 32370). Committed as evidence; safe to keep in PR.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("asyncpg")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.billing_routes import router
from database import get_db_session
from models import User
from services.auth_service import get_current_user


class _BasilSubscription(dict):
    """Stripe v15 SDK object shape: dict-subscriptable AND attribute-accessible.

    items.data[0] carries current_period_start/end (basil contract); the
    subscription root must NOT carry them.
    """

    def __init__(self, *, item, **attrs):
        super().__init__(items={"data": [item]})
        self.__dict__.update(attrs)


def _basil_invoice(secret: str) -> SimpleNamespace:
    """Invoice in basil shape: payment_intent=None, secret in payments.data."""
    return SimpleNamespace(
        payment_intent=None,
        payments=SimpleNamespace(
            data=[SimpleNamespace(payment=SimpleNamespace(client_secret=secret))]
        ),
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_user():
    return User(
        id=1,
        username="smokeuser",
        email="smoke@example.com",
        hashed_password="hashed",
        stripe_customer_id="cus_existing",
        stripe_subscription_id=None,
        subscription_plan="free",
        subscription_status="active",
    )


@pytest.fixture
def client(mock_db, mock_user):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db_session] = lambda: mock_db
    return TestClient(app)


def _subscription_mock(secret="cs_basil_smoke") -> _BasilSubscription:
    item = SimpleNamespace(current_period_start=1704067200, current_period_end=1706745600)
    return _BasilSubscription(
        item=item,
        id="sub_smoke_123",
        status="active",
        latest_invoice=_basil_invoice(secret),
    )


class TestSubscribeSmoke:
    """POST /billing/subscribe — happy path + edge cases + errors (all mocked)."""

    def test_happy_path_pro_resolves_basil_client_secret(self, client, mock_db, mock_user):
        """Pro plan, existing customer: 200 + client_secret from Invoice.payments."""
        sub = _subscription_mock("cs_basil_smoke")
        with patch("services.stripe_service.stripe.Subscription") as sub_api, patch(
            "services.stripe_service.stripe.Customer"
        ):
            sub_api.create.return_value = sub

            resp = client.post("/billing/subscribe", json={"plan_id": "pro"})

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["subscription_id"] == "sub_smoke_123"
        assert body["status"] == "active"
        # Basil dual-shape resolution: secret came from payments.data[0].payment
        assert body["client_secret"] == "cs_basil_smoke"
        # User updated from SubscriptionItem (basil), not the subscription root
        assert mock_user.subscription_plan == "pro"
        assert mock_user.stripe_subscription_id == "sub_smoke_123"
        assert mock_user.subscription_current_period_start is not None
        assert mock_user.subscription_current_period_end is not None
        mock_db.commit.assert_called()
        # Subscription created against the existing customer, price expanded
        call = sub_api.create.call_args[1]
        assert call["customer"] == "cus_existing"
        assert "latest_invoice.payments" in call["expand"]

    def test_creates_customer_when_missing(self, client, mock_db, mock_user):
        """No stripe_customer_id -> Customer.create runs before Subscription.create."""
        mock_user.stripe_customer_id = None
        sub = _subscription_mock()
        with patch("services.stripe_service.stripe.Subscription") as sub_api, patch(
            "services.stripe_service.stripe.Customer"
        ) as cust_api:
            cust_api.create.return_value = SimpleNamespace(id="cus_new_smoke")
            sub_api.create.return_value = sub

            resp = client.post("/billing/subscribe", json={"plan_id": "pro"})

        assert resp.status_code == 200, resp.text
        cust_api.create.assert_called_once()
        assert mock_user.stripe_customer_id == "cus_new_smoke"
        assert sub_api.create.call_args[1]["customer"] == "cus_new_smoke"

    def test_free_plan_skips_stripe_entirely(self, client, mock_db, mock_user):
        """Free tier short-circuits: no SDK calls, status active."""
        with patch("services.stripe_service.stripe.Subscription") as sub_api, patch(
            "services.stripe_service.stripe.Customer"
        ) as cust_api:
            resp = client.post("/billing/subscribe", json={"plan_id": "free"})

        assert resp.status_code == 200, resp.text
        assert resp.json() == {"status": "active", "plan": "free"}
        sub_api.create.assert_not_called()
        cust_api.create.assert_not_called()

    def test_missing_plan_id_returns_400(self, client):
        """Validation edge: empty body -> 400 plan_id required, no SDK calls."""
        with patch("services.stripe_service.stripe.Subscription") as sub_api:
            resp = client.post("/billing/subscribe", json={})
        assert resp.status_code == 400
        assert "plan_id is required" in resp.json()["detail"]
        sub_api.create.assert_not_called()

    def test_invalid_plan_returns_400(self, client):
        """Unknown plan id -> ValueError surfaced as 400."""
        resp = client.post("/billing/subscribe", json={"plan_id": "platinum"})
        assert resp.status_code == 400
        assert "Invalid plan ID" in resp.json()["detail"]

    def test_stripe_error_returns_400(self, client, mock_user):
        """SDK failure mid-flow -> 400 with service message (no 500 leak)."""
        import stripe as stripe_sdk

        mock_user.stripe_customer_id = "cus_existing"
        with patch("services.stripe_service.stripe.Subscription") as sub_api:
            sub_api.create.side_effect = stripe_sdk.error.StripeError("card declined")

            resp = client.post("/billing/subscribe", json={"plan_id": "pro"})

        assert resp.status_code == 400
        assert "Failed to create subscription" in resp.json()["detail"]


class TestSubscribeDualShapeContract:
    """The subscribe response must resolve client_secret across BOTH API shapes."""

    def test_pre_basil_shape_still_resolves(self, client, mock_user):
        """latest_invoice.payment_intent.client_secret (pre-basil) still works."""
        item = SimpleNamespace(current_period_start=1704067200, current_period_end=1706745600)
        sub = _BasilSubscription(
            item=item,
            id="sub_pre_basil",
            status="active",
            latest_invoice=SimpleNamespace(
                payment_intent=SimpleNamespace(client_secret="cs_pre_basil"),
                payments=None,
            ),
        )
        with patch("services.stripe_service.stripe.Subscription") as sub_api, patch(
            "services.stripe_service.stripe.Customer"
        ):
            sub_api.create.return_value = sub
            resp = client.post("/billing/subscribe", json={"plan_id": "pro"})

        assert resp.status_code == 200, resp.text
        assert resp.json()["client_secret"] == "cs_pre_basil"

    def test_invoice_without_payment_returns_null_secret(self, client, mock_user):
        """Neither shape present -> client_secret null, subscription still 200."""
        item = SimpleNamespace(current_period_start=1704067200, current_period_end=1706745600)
        sub = _BasilSubscription(
            item=item,
            id="sub_noinv",
            status="active",
            latest_invoice=SimpleNamespace(),
        )
        with patch("services.stripe_service.stripe.Subscription") as sub_api, patch(
            "services.stripe_service.stripe.Customer"
        ):
            sub_api.create.return_value = sub
            resp = client.post("/billing/subscribe", json={"plan_id": "pro"})

        assert resp.status_code == 200, resp.text
        assert resp.json()["client_secret"] is None


class TestWebhookSignatureRegression:
    """Regression: webhook route must return 400 (not 500) on signature failure.

    Before the fix the route referenced `stripe.error.SignatureVerificationError`,
    which no longer exists in SDK >= 11: a bad signature crashed with
    ModuleNotFoundError -> 500. Card 7c37a29f, PR #230.
    """

    def test_invalid_signature_returns_400_not_500(self, client):
        import stripe

        with patch("api.v1.billing_routes.stripe.Webhook") as webhook_api:
            webhook_api.construct_event.side_effect = stripe.SignatureVerificationError(
                "bad signature", "sig"
            )

            resp = client.post(
                "/billing/webhook",
                content=b'{"type": "checkout.session.completed"}',
                headers={"Stripe-Signature": "t=1,v1=invalid"},
            )

        assert resp.status_code == 400, resp.text
        assert resp.json()["detail"] == "Invalid signature"

    def test_missing_signature_header_returns_400(self, client):
        resp = client.post("/billing/webhook", content=b"{}")
        assert resp.status_code == 400, resp.text
