## Why

This is change **B1**, the first of the offline component-showcase wave, of the Vue SPA WebClient
migration (see `docs/superpowers/specs/2026-08-19-webclient-vue-migration-roadmap-design.md`; depends
on **A2** `webclient-vue-01-foundation`). The migration is "showcase before wiring": the entire
component set is designed and built in Storybook before any live transport exists. B1 establishes that
phase — it introduces the two new capabilities the migration is built around, and it builds the first
component family, the core narrative (root/layout + narrative), so the Storybook, the component-coverage
manifest, and the offline design system are all exercised end-to-end.

## What Changes

- **New capability `webclient-component-showcase`** — every required UI component is a Vue SFC with a
  documented Storybook story (props, emitted events/actions, primary states); the required set is the
  application-surface division fixed by the roadmap's "Delivers" column (roadmap §5) and
  `2026-08-02-webclient-ui-design.md` §7, enforced by a code manifest plus a deterministic
  component-coverage check; the showcase is completed **before** live wiring and is a **mandatory CI
  gate**; stories use deterministic offline data only (no live server, LLM, or imagegen). The surface set
  is backed only by the current OOB allowlist or the text stream; a surface with no backing read model
  stays out of scope and is never mocked.
- **New capability `webclient-vue-application`** — the app loads a self-contained offline Vue 3 SPA
  (Vite bundle served from the project origin, no remote runtime request, desktop-only, mount retires the
  stock/pre-JS text fallback) and renders with the design system carried over from the 設計稿
  (ink-night palette + single seal-red accent, self-hosted fonts, status never color-only, reduced-motion
  honored).
- **Core component family** as SFCs + Storybook stories + Vitest tests: `AppShell`, `TopBar`/`Header`,
  `ConnectOverlay`, `NarrativeFeed` (rendered through the preserved `narrative_markup` pipeline),
  `UnreadIndicator`, `CommandDrawer` — each with a stable `data-testid` and bound to A2's design tokens.
- **The component-coverage manifest** is seeded with these core families so the coverage gate is active.

## Capabilities

### New Capabilities
- `webclient-component-showcase`: the before-wiring, offline, Storybook-documented component set and its
  mandatory coverage gate.
- `webclient-vue-application`: the offline Vue SPA shell (load, mount/fallback, desktop bounds, design
  system) — the store, transport, and façade layers are added by later changes (C1/C2/C3).

### Modified Capabilities
(none — both capabilities are new and introduced here.)

## Impact

- **New:** `web/webclient-app/components/` + `stories/` + Vitest tests for the core family; the
  component-coverage `manifest` (seeded) and its coverage script; the offline design-system wiring
  (consumes A2's tokens); the two new capability specs; the Python evidence tests wrapping the
  build/Storybook/`dist`/coverage executions (`web/webclient/tests/test_vue_showcase_evidence.py`), and
  the B1 browser acceptance in the Vue-branch suite (`web/tests/browser/test_vue_foundation.py`: B1
  stage, retired-fallback round-trip, bounded render at both supported viewports, shard-registered).
- **Depends on (A2):** `package.json`/lock, `vite.config` (stable entry names, CJS interop — B1 scopes
  A2's stable-entry-CSS hook to the app build; see design D5), `.storybook/`, `web/webclient-app/lib/*`
  wrappers, the design tokens + fonts, and the npm/Storybook/`dist` CI gates.
- **Preserved:** the preserved `js/elosern/*` logic (NarrativeFeed consumes `narrative_markup` via the A2
  wrapper); no server, OOB, transport, or `base.html` change — the app renders offline in Storybook only.
