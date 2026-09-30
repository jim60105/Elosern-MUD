## Context

CreationOverlay delegates useCreationOverlay and current exact panel has no preset art field; review creation was Storybook-only, not live verified. Existing creation main contract owns native sex select, key capture, draft and confirmation.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Compose the existing creation wizard into a bounded three-region desktop workspace.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Use three desktop regions: a modest identity/race-description column, central form capped at 640px, and allocation/preview column. At 1280x720 retain the same desktop workflow using bounded internal scrolling and compact gaps; do not invent a mobile layout. The title, tab selector, confirmation/reset controls and error summary stay reachable; DOM focus order follows identity/form then allocation/action. Keep the existing full-viewport creation overlay, not the ordinary reference drawer.

Restyle native selects/checkboxes with token borders/background and platform semantics; reject a custom ARIA select implementation because it creates unnecessary keyboard/IME risk. Keep sex select directly below name, exact race/subrace choices, required ages, persona/background and concept flow. Do not remove fields for appearance.

Make presets fill a balanced three-column grid with complete authored name, race, emphasis and background. Current preset payload carries no portrait reference, so use a visibly decorative local silhouette/ornament instead of fetching or inventing per-preset artwork. Newly generated static defaults are not falsely attributed to a preset.

Move existing numeric allocations into labelled steppers with native number entry retained. Show simple bar previews of already-derived values using server bounds; no radar system or new stat formulas. Concept fill, in-flight pinning, save/activation confirmation and stale/error handling stay unchanged. This change is layout and existing control presentation only; localized data is a dependency.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
