## Context

AVG design section 2 requires proportional 2560x1440 behavior while preserving 1440x900 and 1280x720; report Cross-cutting and type/radius sprawl. Existing prose/band already use vh, so global zoom would double-scale them.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Scale desktop chrome with the 1080p reference without double-scaling prose or stage art.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Use S = clamp(1, viewportHeight / 1080, 1.4) for desktop chrome. At 2560x1440 S=4/3; at the smaller acceptance sizes S=1. Define the unitless factor once from a ResizeObserver/window-resize owner, write one root CSS property, and remove the listener/observer on teardown. Do not read layout on every frame.

Scale the common type, spacing, radius, header-height, island-width, icon/control dimensions and fixed max-width tokens via calc(base * S). Audit fixed dimensions of the named surfaces and migrate them to the same tokens in one mechanical pass. Band height, prose vh size, standing-portrait vh geometry and full-bleed backdrop already respond to viewport dimensions: do NOT multiply them again. Reader prose preference remains a separate multiplier and does not change chrome. No CSS zoom/whole-root transform: these complicate hit-testing, SVG fit and accessibility zoom.

For the minimap only, scale its outward 208px square by S while keeping SVG user-unit geometry unchanged; this is a uniform display scale, never coordinate recomputation. The full-map fitted view measures its real available body normally. Scale drawer/creation art/form width caps once, not their percentages.

Consolidate ordinary rectangular radii to small/default/pill tokens while preserving circles, intentional square map cells, and geometric masks as geometry, not radius variants. Existing named display and prose type exceptions remain. This is a presentation-only mechanical conversion after the smaller surface changes, not a responsive redesign. At smaller acceptance sizes preserve readable text floors and internal scrolling rather than shrinking chrome below S=1.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
