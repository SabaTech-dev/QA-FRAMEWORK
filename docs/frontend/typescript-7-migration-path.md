# TypeScript 6 → 7 Migration Path — Dashboard Frontend

**Card:** b37d29c8 (TS 7.0 prep)
**Fecha:** 2026-08-25 | **Autor:** Build Agent
**Status:** Phase 1 done (TS 6.0.3 shipped in `chore/ts7-prep`)

## Current state (after this PR)

| Item | Value | Notes |
|------|-------|-------|
| TypeScript | `^5.2.2` → **`^6.0.3`** | Latest stable 6.x line (`6.0.3`, node `>=14.17`) |
| Type-check | `npx tsc --noEmit` green | 11 type errors found & fixed by the bump (see log below) |
| Build | `vite build` green | Vite transpiles via esbuild; it never type-checked — now gated locally |
| `tsconfig` | `baseUrl` removed | Deprecated in TS 6 (TS5101), **removed in TS 7**. `paths` are relative to tsconfig since TS 4.1 |
| Node | local 26.7.0, Docker `node:26-alpine` | TS 7 requires `>=16.20.0` — no constraint for us |
| Lint infra | fixed (see below) | `.eslintrc.json` extends + missing plugin; lint now runs for the first time |

Registry snapshot (2026-08-25): `latest = 7.0.2` (native port, released 2026-08-20), `next = 7.1.0-dev`.

## What TypeScript 7 is (and is not)

TS 7 is the native port of the compiler (project Corsa, Go-based, formerly
`@typescript/native-preview` / `tsgo`). Key facts from the official sources
(TypeScript-Go `CHANGES.md` / `README.md`, release v7.0.2):

- **Type checking is at parity with TS 6.0**: same errors, locations and
  messages. Moving 6 → 7 should not surface new *type* errors in `.ts`/`.tsx`.
- **The compiler API is "not ready"** in the native port. Any tool that links
  against the TS compiler API (`@typescript-eslint` parser, some CLIs) still
  needs the JS-based compiler until they ship native support. **This is the #1
  blocker for this repo**, not our source code.
- Breaking changes are concentrated in **JavaScript/JSDoc checking** (Closure
  features removed, constructor-function expandos removed, CommonJS rules
  tightened) — low impact for us: `src/` is pure TS/TSX and configs are TS.

## Breaking changes 6 → 7 that can affect this repo

Ranked by relevance, from the official `CHANGES.md` (microsoft/TypeScript-Go):

1. **Compiler API not ready** (README status table)
   - `@typescript-eslint/parser@6.x` consumes the TS API. Until
     typescript-eslint ships TS 7 support, `npm run lint` must keep a TS 6
     install available (or the repo pins the parser to whatever it supports).
   - Action: track typescript-eslint's TS 7 support before bumping.
2. **`--skipLibCheck` no longer hides conflicting declarations**
   (`tsconfig.json` has `"skipLibCheck": true`): declaration conflicts now
   error at *all* contributing sites, including non-`.d.ts` files.
   - Action: run a 7.0 probe build and diff errors; fix root causes, don't
     silence with `ignoreDeprecations`.
3. **`strict: false` + omitted arguments**: parameters typed `unknown`/`any`/
   `undefined` can no longer be omitted at call sites (previously allowed with
   `strict: false`). Our `tsconfig` is non-strict and the codebase has ~92
   `any`s — probe build required to size this.
4. **Deprecated options removed**: everything TS 6 flags as TS5101 stops
   functioning in 7 (`baseUrl` here — already migrated). No other deprecated
   flags are present in our tsconfigs (`target: ES2020`,
   `moduleResolution: "bundler"` are fine).
5. **Node positions switch to UTF-8 offsets** (scanner). Affects tooling that
   maps TS positions (linters, coverage); cosmetic for daily development.
6. **Template-literal inference consumes full Unicode code points** (emoji no
   longer split into surrogate halves). Only relevant if we ever rely on
   surrogate-splitting behavior in template literal types (we don't).
7. **`moduleResolution` modes**: "not all resolution modes supported yet" at
   7.0 — `bundler` (ours) is supported; keep it.

Not applicable to this repo (JS-specific): Closure header/types removal,
`@class`/`@enum`/`@author` tag changes, constructor-function expandos,
fallback initialisers, CommonJS export mixing rules.

## `@types/*` dependencies status

| Package | Installed | Range in package.json | Risk for TS 7 |
|---------|-----------|----------------------|---------------|
| `@types/react` | 18.3.28 | `^18.2.0` | Low — plain `.d.ts`, independent of compiler |
| `@types/react-dom` | 18.3.7 | `^18.2.0` | Low |
| `@types/canvas-confetti` | 1.9.0 | `^1.9.0` | Low |

`@types/*` packages are consumed as declaration files; they do not link the
compiler API. The risk concentrates on the **toolchain** packages:

| Tool | Version | TS 7 concern |
|------|---------|--------------|
| `@typescript-eslint/parser` + plugin | 6.10.x | Uses TS compiler API — needs typescript-eslint release with TS 7 support |
| `eslint` | 8.57.1 | Independent of TS |
| `vite` | 5.x (esbuild) | Independent of TS (no type-check) |
| `vitest` | 0.34.x | Independent of TS (esbuild transform) |

## Concrete steps to land 7.x

1. **[Done in this PR] Get to 6.0.3 and make `tsc --noEmit` green.** This is
   the parity baseline: TS 7 reports the same type errors as TS 6, so a green
   6.x build is the strongest predictor of a green 7.x build.
2. **Add `tsc --noEmit` to CI** (not present today — `vite build` doesn't type
   check). Suggested: step in `pr-checks.yml` / `ci-cd.yml` frontend job.
3. **Probe, don't jump**: in a throwaway branch, `npm i -D typescript@7.0.2 &&
   npx tsc --noEmit`. Size the fallout (expect items 2–3 of the list above:
   `skipLibCheck` conflicts and non-strict omitted-argument errors).
4. **Verify toolchain**: confirm `@typescript-eslint` supports TS 7 (their
   release notes / `supportedTypescriptVersions`). Until then either stay on
   6.x or keep lint pinned to 6.x while `tsc` moves to 7.x (split install).
5. **Bump `typescript` to `^7.0.x`** in `package.json` + lockfile, keep
   `vite build` green (esbuild unaffected), run vitest suite + Playwright e2e.
6. **Post-landing cleanups**: enable `strict: true` incrementally (the 92
   `no-explicit-any` warnings are the backlog), then consider dropping
   `skipLibCheck` to keep declaration health visible.

## Appendix: type errors surfaced by the TS 6 bump (this PR)

1. `useNotificationsWebSocket.ts` — stray Python docstring in TS source (TS1005 syntax errors).
2. `tsconfig.json` — `baseUrl` deprecated (TS5101) → removed, `paths` made tsconfig-relative.
3. `Layout.tsx` — `useKeyboardShortcuts({shortcuts: [...]})` passed an object where the hook takes `KeyboardShortcut[]` (latent runtime break: `for..of` over a non-iterable).
4. `DisclosureBanner.test.tsx` — `beforeEach` used but not imported from `vitest` (TS2593).
5. `TokenUsageChart.tsx` — `dashboardAPI.getTokenUsage` didn't exist on the type; method now declared optional (backend endpoint still missing, callers keep the `?.()` + fallback contract).
6. `Analytics.tsx` — `Object.values(...).reduce` inferred as `unknown` under TS 6 inference; `featuresData` now typed `Record<string, { usage_count?: number }>`.
7. `Billing.tsx` — `plansData?.plans` on an `AxiosResponse`; correct access is `plansData?.data?.plans`.
8. `authStore.ts` — `User` interface missing `full_name`, `subscription_plan`, `subscription_status` (all present in the backend model); added as optional nullable fields.
9. `ThemeContext.tsx` — `setMode` received a state-updater function but its type is `(newMode: ThemeMode) => void`; `toggleTheme` now computes from `mode` directly (persistence semantics preserved).

## Lint debt inventory (pre-existing, not paid in this PR)

`npm run lint` was broken before this PR (bad `extends` name + missing
`eslint-plugin-react`). Once fixed it runs for the first time and reports:
**100 errors** (76 `no-unused-vars`, 23 `react/no-unescaped-entities`, 1
`no-empty`) and **92 warnings** (`no-explicit-any`) across ~26 files, plus
`--max-warnings 0` making every warning blocking. Files touched by this PR
are error-free. Recommended: dedicated lint-cleanup PR before enabling lint
as a required CI gate.

## References

- Official 6→7 intentional changes: `microsoft/TypeScript-Go` `CHANGES.md`
- Native port announcement: `devblogs.microsoft.com/typescript/typescript-native-port/`
- TS 7.0.2 release notes: `devblogs.microsoft.com/typescript/announcing-typescript-7-0/`
- TS 6 deprecations pointer: https://aka.ms/ts6 (issue #62508)
