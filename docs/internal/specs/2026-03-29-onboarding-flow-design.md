# Design: User Onboarding Flow

**Date:** 2026-03-29
**Task:** 9ac580c4 — User Onboarding Flow
**Status:** In Progress (re-work)

## Goal
Implement a complete, functional onboarding flow that guides new users through key setup steps after registration, with backend state tracking and proper frontend integration.

## Problem
The existing `OnboardingWizard.tsx` is an orphaned component:
- Not imported or routed in the app
- No backend support for tracking progress
- Steps are visual-only (no real API calls)
- No state persistence
- No tests

## Architecture

### Backend Changes
1. **User Model**: Add `onboarding_state` (JSON) and `onboarding_completed` (Boolean) columns
2. **API Endpoints**:
   - `GET /me/onboarding` → returns current onboarding state
   - `PATCH /me/onboarding` → updates step progress
3. **Migration**: Alembic migration for new columns

### Frontend Changes
1. **OnboardingWizard Rewrite**:
   - Real API calls per step (create suite, run test, etc.)
   - State synced with backend via onboarding endpoints
   - Skip/resume capability
   - Progress bar with step completion tracking
2. **Routing Integration**:
   - Add `/onboarding` route in App.tsx
   - Post-login redirect: if `onboarding_completed === false` → `/onboarding`
   - Protected route (requires auth)
3. **Auth Store**: Add `onboarding_completed` to user state

### Flow
```
Register → Verify Email → Login → Check onboarding state
  → if not completed: redirect to /onboarding
    → Step 1: Welcome (auto-complete)
    → Step 2: Connect Repository (OAuth or URL input)
    → Step 3: Create First Test Suite (real API call)
    → Step 4: Run First Test (trigger execution API)
    → Step 5: Configure Notifications (preferences)
    → Mark onboarding_completed → redirect to /dashboard
  → if completed: redirect to /dashboard
```

## Tech Stack
- Backend: FastAPI + SQLAlchemy + Alembic
- Frontend: React + MUI + React Query + Zustand
- Tests: pytest (backend) + Vitest (frontend)

## Tasks Breakdown
1. Backend: User model + migration + API endpoints + tests
2. Frontend: Rewrite OnboardingWizard + routing + auth integration
3. Integration: E2E validation

## Risks
- Database migration on existing users (default values needed)
- OAuth integration for repo connection (use existing GitHub OAuth if available)
- Time investment vs. simplicity trade-off

## Decisions
- Use JSON column for `onboarding_state` (flexible, avoids schema per step)
- Allow skip per step (not all steps mandatory)
- Onboarding auto-completes after last step or manual skip-all
