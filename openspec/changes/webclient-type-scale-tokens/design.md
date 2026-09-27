## Context

Current shared tokens include sub-12px chrome and SkillDetailPane contains 10/10.5/11.5px declarations. Report type counts are not re-measured in this proposal.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Establish a readable shared chrome type/numeral scale and remove arbitrary size sprawl.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Use the existing draft scale mapping (12/13/14/16/18/20/24/28/32px plus 44px decorative initial), with shared --f-num based on the local sans stack and tabular lining numerals. Replace obsolete text-body/text-narrative/text-dialog token uses in one cutover; preserve viewport-relative narrative typography. Relative sizes must still meet the rendered floor.

Keep monospace for command input, ASCII/box-drawing maps and key names, not general UI or numerals. Map SVG label geometry is owned by webclient-map-legibility; its title/readout migrate there. This is a mechanical type-only sweep, not a layout redesign. Surface-specific redesigns and radius/scaling follow separately.

Reject the proposed literal-font-size/source guard and exact token-list tests: they pin implementation spelling rather than consumer behavior. Use a throwaway inventory to guide the sweep, delete stale CSS/source-wording tests, and retain focused browser checks for readable text, no clipping and numeric alignment. The report's 24-size/84-use counts and interrupted proposal's different counts are observations from separate inventories, not a new measurement claimed here.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
