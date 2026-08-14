# Stripe Integration Testing - Design Doc

**Fecha:** 2026-03-25
**Autor:** coder agent
**Task ID:** 8fcf3665-3018-4a3d-8655-1b149722c2d8
**Estado:** IMPLEMENTING - Tests E2E creados

---

## 1. Goal

Implementar suite de tests E2E para flujos de pago con Stripe en QA-FRAMEWORK.

---

## 2. Contexto Confirmado

- **Proyecto:** QA-FRAMEWORK (`/home/ubuntu/qa-framework`)
- **Stack:** Python (FastAPI) + PostgreSQL + Redis
- **Stripe ya existe:** Solo crear tests, no implementación
- **Testing framework:** pytest + pytest-asyncio + httpx
- **Stripe mode:** Test mode con tarjetas mock

---

## 3. Archivos Creados

### Tests E2E
- `tests/e2e/test_stripe_e2e.py` — Suite completa de tests E2E

### Tests existentes (referencia)
- `dashboard/backend/tests/services/test_stripe_service.py` — Tests unitarios
- `tests/unit/billing/test_billing.py` — Tests unitarios billing

---

## 4. Flujos Testeados

| Flujo | Test Class | Prioridad |
|-------|------------|-----------|
| Checkout básico | `TestStripeCheckoutFlow` | HIGH |
| Checkout free plan | `test_checkout_free_plan_no_payment_required` | HIGH |
| Checkout pro plan | `test_checkout_pro_plan_creates_customer_and_subscription` | HIGH |
| Tarjeta declinada | `test_checkout_with_declined_card_returns_error` | HIGH |
| Upgrade subscription | `TestStripeSubscriptionManagement` | HIGH |
| Downgrade subscription | `test_downgrade_subscription_enterprise_to_pro` | MEDIUM |
| Cancel at period end | `test_cancel_subscription_at_period_end` | HIGH |
| Cancel immediately | `test_cancel_subscription_immediately` | MEDIUM |
| Webhook payment_succeeded | `TestStripeWebhookHandling` | HIGH |
| Webhook payment_failed | `test_webhook_payment_failed_marks_past_due` | HIGH |
| Webhook subscription_updated | `test_webhook_subscription_updated_syncs_status` | HIGH |
| Webhook subscription_deleted | `test_webhook_subscription_deleted_downgrades_to_free` | HIGH |
| Signature validation | `test_webhook_signature_validation` | MEDIUM |
| Error handling | `TestStripeErrorHandling` | HIGH |
| Plan features | `TestStripePlanFeatures` | MEDIUM |
| Complete lifecycle | `TestStripeCompleteFlows` | HIGH |

---

## 5. Test Cards

```python
STRIPE_TEST_CARDS = {
    "success": "4242424242424242",
    "declined": "4000000000000002",
    "insufficient_funds": "4000000000009995",
    "lost_card": "4000000000009987",
    "expired_card": "4000000000000069",
    "incorrect_cvc": "4000000000000127",
    "processing_error": "4000000000000119",
    "3ds_required": "4000002500003155",
}
```

---

## 6. Cómo ejecutar

```bash
# Ejecutar todos los tests E2E de Stripe
cd /home/ubuntu/qa-framework
pytest tests/e2e/test_stripe_e2e.py -v -m e2e

# Con coverage
pytest tests/e2e/test_stripe_e2e.py -v -m e2e --cov=dashboard/backend/services/stripe_service

# Tests específicos
pytest tests/e2e/test_stripe_e2e.py::TestStripeCheckoutFlow -v
pytest tests/e2e/test_stripe_e2e.py::TestStripeWebhookHandling -v
```

---

## 7. DoD Checklist

- [x] Tests E2E creados para checkout flow
- [x] Tests E2E creados para subscription management
- [x] Tests E2E creados para webhook handling
- [x] Tests E2E creados para error handling
- [x] Tests E2E creados para plan features
- [ ] Ejecutar tests y verificar que pasan
- [ ] Commit con resultados

---

**Siguiente paso:** Ejecutar tests y verificar que pasan.
