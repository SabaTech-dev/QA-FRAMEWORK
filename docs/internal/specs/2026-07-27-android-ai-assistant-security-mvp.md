# MVP Scope: Android AI Assistant Security Testing Module

**Date:** 2026-07-27
**Author:** Alfred (CEO Agent) for Joker review
**Status:** 🔲 Awaiting Go/No-Go decision
**Target:** 4-6 weeks (2 devs)

---

## 1. Opportunity

EU Digital Markets Act (DMA) forces Android to allow third-party AI assistants system-wide access (voice, notifications, screen content, app intents). **No QA tool exists that tests security of these assistants.** First-mover advantage for QA-FRAMEWORK.

**Existing leverage:**
- `src/adapters/mobile/` — Appium driver (Android + iOS), device profiles
- `src/adapters/security/` — SQLi, XSS, auth, rate-limit testers
- `src/domain/` — Clean architecture, test generation, accuracy testing
- EU AI Act Art. 50 disclosure already implemented (DisclosureBanner.tsx)

---

## 2. MVP — Core Features (Must Have)

### 2.1 Data Exfiltration Detector
Detects when AI assistant sends user data (contacts, location, messages, photos) to unauthorized endpoints.

| Test | What it does |
|------|-------------|
| Network interception | Proxy device traffic, flag PII leaving via assistant APIs |
| Clipboard monitoring | Detect clipboard reads by assistant without user trigger |
| Background sync | Flag assistants uploading data while idle |

**Implementation:** Appium + mitmproxy adapter. Reuses `HTTPXClient` + `SecurityClient` patterns.

### 2.2 Voice Prompt Injection Tester
Tests if assistant executes hidden commands embedded in voice/audio.

| Test | What it does |
|------|-------------|
| Hidden audio commands | Play ultrasonic/embedded audio, check if assistant executes |
| Intent hijack via voice | "Open settings and disable HTTPS" style chained commands |
| Multi-turn manipulation | Conversation that gradually extracts sensitive data |

**Implementation:** Audio injection via ADB + Appium. New `VoiceInjectionTester` class under `src/domain/ai_safety/`.

### 2.3 Permission Abuse Auditor
Validates assistant only accesses permissions it declares and needs.

| Test | What it does |
|------|-------------|
| Manifest diff | Compare declared permissions vs runtime access |
| Permission scope creep | Request MICROPHONE but access CAMERA at runtime |
| System intent abuse | Assistant invoking system intents beyond its scope |

**Implementation:** ADB `dumpsys package` + Android Permission API. New `PermissionAuditor` adapter.

---

## 3. MVP — Nice-to-Have (Defer to v2)

- ❌ Cross-assistant comparative benchmarking (Gemini vs ChatGPT vs Bixby)
- ❌ Model-level adversarial testing (beyond API surface)
- ❌ Real-time monitoring dashboard (MVP = batch reports)
- ❌ iOS support (MVP = Android only, EU DMA is Android-first)
- ❌ Automated remediation suggestions
- ❌ OWASP MASVS L2 full certification (MVP targets L1 subset)

---

## 4. Architecture (fits existing Clean Architecture)

```
src/
├── domain/
│   └── ai_safety/              # NEW domain module
│       ├── entities.py         # SecurityFinding, TestSuite, RiskScore
│       ├── value_objects.py    # FindingSeverity, TestType, DataType
│       ├── interfaces.py       # IAuditor, IInterceptor, IInjector
│       └── use_cases/
│           ├── audit_permissions.py
│           ├── detect_exfiltration.py
│           └── test_voice_injection.py
├── adapters/
│   └── ai_safety/              # NEW adapters
│       ├── mitmproxy_adapter.py    # Traffic interception
│       ├── voice_injector.py       # ADB audio injection
│       ├── permission_scanner.py   # Android manifest + runtime audit
│       └── adb_client.py           # ADB wrapper (reuse existing patterns)
└── dashboard/
    └── backend/
        └── api/
            └── ai_safety.py    # NEW API endpoints
```

**Reuses:** `HTTPXClient`, `SecurityClient` facade, `TestSuite` entity, reporting adapters (Allure, HTML), dashboard auth/billing.

---

## 5. Test Categories → OWASP MASVS / OWASP LLM Top 10 Mapping

| MVP Test | OWASP MASVS | OWASP LLM Top 10 |
|----------|-------------|------------------|
| Data exfiltration | MASVS-STORAGE-2 | LLM02 (Sensitive Information) |
| Voice prompt injection | MASVS-PLATFORM-1 | LLM01 (Prompt Injection) |
| Permission abuse | MASVS-PLATFORM-2 | — |
| Clipboard access | MASVS-PRIVACY-1 | LLM02 |
| Background data sync | MASVS-NETWORK-1 | LLM06 (Excessive Agency) |

---

## 6. Effort Estimation (4-6 weeks, 2 devs)

| Phase | Weeks | Deliverable |
|-------|-------|-------------|
| **Sprint 1** | 1-2 | Domain module + ADB client + permission auditor |
| **Sprint 2** | 3 | mitmproxy adapter + exfiltration detector |
| **Sprint 3** | 4 | Voice injection tester + integration tests |
| **Sprint 4** | 5 | Dashboard API + report generation + docs |
| **Sprint 5** | 6 | Beta hardening + 2 real assistant tests (Gemini, ChatGPT) |

**Dependencies:**
- Android device/emulator (Realme GT 7 Pro available)
- mitmproxy Python lib (pip install, no infra)
- ADB (already on jokerserver)
- No new cloud services required

**Risk:** Google/Apple may change assistant APIs mid-development. Mitigation: abstract behind interfaces, test against stable Android API levels (14-16).

---

## 7. Business Case

| Metric | Value |
|--------|-------|
| Market size | ~50M Android users in EU affected by DMA |
| Competition | 0 dedicated QA tools for AI assistant security |
| Pricing | Add-on module: $49/month on top of QA-FRAMEWORK plan |
| Differentiation | First-mover, OWASP-aligned, EU AI Act compliant |
| Effort | 4-6 weeks (low vs. potential market positioning) |

---

## 8. Go/No-Go Decision Points for Joker

1. **Scope OK?** — Are the 3 core tests the right MVP cut?
2. **Timeline OK?** — 4-6 weeks starting August?
3. **Positioning?** — Standalone module or bundled with existing QA-FRAMEWORK security tier?
4. **Beta target?** — Approach Minsait as first enterprise tester?

---

## 9. AC Checklist (for this card)

- [x] Documento de scope MVP (features core vs nice-to-have) → §2, §3
- [x] Definición de tests: data exfiltration, prompt injection via voice, permission abuse → §2.1-2.3
- [x] Estimación de effort y recursos (4-6 semanas target) → §6
- [ ] Go/no-go decision de Joker → **PENDANT DE TU REVISIÓN**

---

*"The EU just handed us a market. Nobody is testing whether the AI assistant that can read your screen, hear your voice, and access your apps is actually safe. We can be first."*
