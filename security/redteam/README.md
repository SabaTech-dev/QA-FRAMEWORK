# 🔒 QA-FRAMEWORK Red-Team Suite

**Security Audit:** 2026-06-20 (Card e595968d → 7d01e74c)
**Tool:** Promptfoo v0.121.17 (MIT License)
**Coverage:** OWASP LLM Top 10, GDPR, NIST AI RMF

## Quick Start

```bash
# 1. Install promptfoo (already global)
npm install -g promptfoo

# 2. Set env vars
export QA_FRAMEWORK_BASE_URL="http://localhost:8000"
export QA_FRAMEWORK_JWT_TOKEN="your-test-token"

# 3. Run red-team scan
cd security/redteam
npx promptfoo redteam run

# 4. Generate report
npx promptfoo redteam report

# 5. View results
open output/redteam-report.html
```

## Structure

```
security/redteam/
├── promptfooconfig.yaml          # Main config (8 strategies, 12 plugins)
├── targets/
│   └── qa-framework-http-provider.py  # Custom HTTP provider
├── output/                       # Scan results (gitignored)
└── README.md                     # This file
```

## Test Coverage

| Category | Plugin | Tests | Severity |
|----------|--------|-------|----------|
| Prompt Injection | prompt-injection | 15 | Critical |
| Jailbreak | jailbreak, jailbreak:meta, jailbreak:hydra | 10 | High |
| PII Leakage | pii:direct, pii:session, pii:social, pii:api-db | 31 | High |
| Excessive Agency | excessive-agency | 8 | High |
| System Prompt | imitation | 5 | Medium |
| Hallucination | hallucination | 5 | Medium |
| GDPR | gdpr | 5 | Medium |
| NIST | nist:ai:measure | 3 | Low |

**Total: ~82 adversarial test cases**

## Bypass Strategies

- `jailbreak:meta` — Single-turn adaptive attacks
- `jailbreak:hydra` — Multi-turn adaptive conversations
- `prompt-injection` — Direct injection wrapper
- `base64` — Base64 encoding bypass
- `rot13` — ROT13 encoding bypass
- `homoglyph` — Unicode homoglyph substitution

## CI/CD Integration

See `.github/workflows/redteam.yml` — runs weekly on Mondays at 6AM UTC.

## Limitations

- Requires a running QA-FRAMEWORK instance (mock mode available)
- Adversarial generation uses OpenAI API (~$5-15/scan)
- Red-teaming proves presence, not absence of vulnerabilities
- LLMs are non-deterministic — run multiple times for confidence

## References

- [Promptfoo GitHub](https://github.com/promptfoo/promptfoo)
- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
