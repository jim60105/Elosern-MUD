## Context

Part **B1** (first showcase wave; depends on **A2**). The toolchain, `lib/*` wrappers, design tokens,
offline fonts, and the npm/Storybook/`dist` CI gates already exist from A2. B1 turns that scaffolding
into the first real, offline-rendered app: the core component family in Storybook, the component-coverage
manifest, and the two new capabilities the whole migration is built on.

Constraints:
- **Showcase before wiring (roadmap §4/§6.3):** no live Evennia transport here; every story is driven by
  embedded, deterministic mock data. Wave B is a serial chain because the component-coverage `manifest`
  and this capability's required-set are a single coordination point.
- **True-at-archive (roadmap §4):** the two new capabilities are `ADDED` here; later changes
  `MODIFIED`/extend them as archive proceeds, so `openspec validate --strict` and traceability stay green
  at every archive.

## Goals / Non-Goals

**Goals**
- Introduce `webclient-component-showcase` (required-set via a code manifest + before-wiring gate +
  offline deterministic stories) and `webclient-vue-application` (offline SPA load + offline design
  system).
- Build the core narrative family as documented, offline, component-tested SFCs seeded into the manifest.

**Non-Goals**
- No live WebSocket/OOB wiring, no Pinia store binding to transport (C1/C2/C3), no mount into the live
  `webclient.html` template (C3), no base.html change.
- No action/status/world/overlay families (B2–B5). No deferred surfaces (Party, intimate, full inventory,
  event-log toasts) — none is built.

## Decisions

- **D1 — Required set = a code manifest, frozen last.** The "required components" are a checked-in list
  (`web/webclient-app/component-manifest.json`, settled by A2 as the story-title manifest that
  `scripts/component-coverage.mjs` reads), enforced by a deterministic component-coverage script that
  fails when a listed component has no registered/undocumented story. B1
  seeds it with the core family; B2–B4 extend it; B5 freezes it. Kept out of the spec text so the
  requirement ("every manifest component has a documented story") is stable and always true-at-archive,
  while the *list* evolves in code.

- **D2 — Introduce both capabilities now, extend later.** B1 `ADDED`s `webclient-component-showcase`
  (required-set, before-wiring gate, offline stories) and `webclient-vue-application` (offline SPA load +
  design system). The remaining `webclient-vue-application` requirements (reactive store C1; degraded text
  + façade/DOM hooks C2; live mount C3; fully store-bound views C4) are added by their owning changes.
  Alternatives: defer `webclient-vue-application` entirely to C1 — rejected, the offline-load and
  design-system facts are established the moment the app first renders offline (here), so they belong to
  the change that establishes them.

- **D3 — Components are passive, offline, hook-stable.** Each SFC renders only the mock slice passed in,
  emits user-intent events (no store yet), and exposes a stable `data-testid`. `NarrativeFeed` renders
  through the preserved `narrative_markup` pipeline (via the A2 `lib` wrapper), including its
  degrade-to-literal-text path. Design tokens / fonts come from A2; nothing is fetched at render.

## Risks / Trade-offs

- **Manifest drift** (a story added but the manifest not updated, or vice versa) → the component-coverage
  script fails the build in both directions (missing story for a listed key; and a lint that every story
  file maps to a listed key).
- **Store-contract drift** — components are mock-driven now, but must later bind to C1's store → the
  A2 `frontend-vue-architecture.md` pins the slice shapes (component prop ↔ store slice) so B and C1
  target the same contract.
- **Core family is the biggest single slice** (6 components + the capability specs) → kept to the
  root/layout + narrative group; the heavier data/world/overlay families are their own changes (B2–B5).

## Migration Plan

No runtime effect (Storybook/offline only). Rollback: delete the core components/stories/tests and the
seeded manifest; the A2 toolchain and all existing gates are unaffected.

## Open Questions

- None; the required-set and slice shapes are fixed by the manifest and the A2 architecture reference.
