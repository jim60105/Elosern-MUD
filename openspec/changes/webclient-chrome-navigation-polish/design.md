## Context

DesktopNavigation currently v-if hides map in combat and already exposes title/aria-label on tool buttons. Report Top Bar bullets 1-3 and Place Card.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Stabilize top-navigation placement and polish the place card without changing visibility rules.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Reserve stable CSS grid tracks for the normal primary navigation concepts; missing entries leave empty layout space, not hidden actionable controls. Keep mode-forbidden surfaces display:none or absent as the mode contract requires. This resolves the tool cluster shift without adopting the report's aria-disabled/visibility:hidden substitutes for forbidden surfaces. At 1280px the primary tracks may use compact padding but never overlap switcher/tools.

Tool buttons already have title and aria-label; add a shared visible hover AND focus tooltip treatment, escape-dismissable without moving focus, with labels from the same tool model. Use glyph keys shared with DrawerHeader. Align bilingual brand baselines and reduce tracking; no new brand assets.

Place card separates the location title from the world-time line with a quiet gold rule. Remove only a leading placeholder separator when no prefix exists, not canonical time information. Tabular world-time numerals and tokenized readable type replace ad-hoc sizes; the card remains display-only.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
