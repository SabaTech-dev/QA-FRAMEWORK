# Accuracy Response Provider — Implementation Plan (card 2f9afe89)

Design: `docs/specs/2026-08-24-accuracy-response-provider-design.md`

## Tasks (TDD: RED → GREEN → REFACTOR per task)

1. **RED** — `tests/unit/infrastructure/test_llm_gateway_provider.py`
   - `TestRequestContract`: OpenAI payload (model, system+user messages,
     temperature, max_tokens), Bearer header, browser UA, target URL.
   - `TestGetResponse`: returns `choices[0].message.content`.
   - `TestModelOverride`: per-call `model` wins over configured model.
   - `TestErrorMapping`: HTTP >= 400, timeout, connect error, malformed
     JSON, empty choices → `LLMGatewayProviderError` with sanitized
     message (no upstream body).
   - `TestFactory`: env matrix (no key → None; provider key; fallback
     `OPENCODE_GO_API_KEY`; URL/model/timeout overrides; invalid
     timeout → default).
2. **RED** — endpoint contract extension: provider failure → 502 with
   generic detail; canary: upstream body absent from response.
3. **RED** — provider+endpoint integration (DI): router built with a
   factory-configured provider + injected MockTransport → POST 200.
4. **GREEN** — implement `src/infrastructure/accuracy_testing/llm_gateway_provider.py`
   (error, provider, factory) + 502 mapping in `endpoint.py` +
   `__init__.py` exports.
5. **Vendor sync** — copy `src/infrastructure/accuracy_testing/*.py` →
   `dashboard/backend/src/infrastructure/accuracy_testing/`; wire
   `response_provider=create_response_provider_from_env()` in
   `dashboard/backend/main.py`; extend
   `dashboard/backend/tests/test_accuracy_wiring.py` (reload with
   provider env → clean assembly).
6. **REFACTOR** — style pass (ruff/black, line length 100), no behavior
   change; all tests green; coverage ≥ 80% on the new file.
7. **Docs** — `docs/accuracy-testing.md`: provider section + env table
   + curl example; CHANGELOG entry.
8. **Ship** — conventional commits, push, PR with AC summary.

## Acceptance criteria mapping

| AC | Proof |
|---|---|
| 1. POST 200 with provider | integration test (task 3) + wiring test (task 5) |
| 2. Injectable provider, unit tests sin red | MockTransport DI (tasks 1–3) |
| 3. E2E left to qa-tester | endpoint functional + curl recipe in docs |
| 4. Docs | task 7 |

## Risks

- Vendored drift → mitigated by the vendor-parity test (fails loudly).
- Gateway latency in POST → bounded by `ACCURACY_PROVIDER_TIMEOUT_S`,
  failures map to 502 instead of hanging or leaking 500s.
- Secret hygiene → key read only from env, never logged, never
  committed (same rule as `OPENCODE_GO_API_KEY`).
