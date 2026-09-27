## Context

MessageWindow reader owns typing, advance and measurement; current main spec explicitly pins 28px and strip placement. Report Message Window bullets 3-7, Dialogue bullets 1-2, Motion bullet 2.

Architectural sources: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` (read-only browser, deterministic authority, offline operation) and `docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` (desktop AVG stage). Current main specifications, not historical archives, define preserved contracts. The report's screenshots are review observations; no new live/browser verification is claimed by this proposal-only work.

## Goals / Non-Goals

**Goals:** Improve CJK prose spacing and anchor reading furniture to the actual text measure.

**Non-goals:** no game-rule change, new gameplay capability, generic UI framework, mobile design, image-service work, compatibility adapter or persisted-data migration. Keep this slice to the named owners and focused checks; do not fold other batch surfaces into it.

## Decisions

Keep the contracted 28px reference prose size and <=42-character measure; reject the report's 26px reduction because it changes a deliberate reader contract. Set line height 1.5 and inter-paragraph gap .45em. The actual page and fit-measurement clone must receive the same prose class and font-ready remeasurement so paging follows rendered geometry, including preferences and resize.

Use progressive text-spacing-trim/text-autospace/line-break/hanging-punctuation on prose only. Unsupported CSS falls back to readable default spacing; do not globally apply halt or alter whitespace in ASCII/box-drawing maps or command input. Do not rewrite narrative strings.

Place the decorative page marker in the reserved control strip aligned with the prose measure's right edge, not the viewport edge. Name-plate underline follows the name inset. The left rule appears only when the reader owns focus. Slow the full-motion marker bob to a tokenized 1.6s with 2px travel; reduced/off remain static.

Dialogue choices receive restrained corner ornaments and a tint on the leave icon, not a destructive whole-row frame. On pointer-open, initialize local active descendant to the first enabled choice without activation, focus stealing before the list is eligible, or changing server order. If no enabled choice exists, retain the existing disabled focus/explanation behavior.

## Risks / Trade-offs

- Longer localized strings and raised type sizes can exceed fixed boxes. Use bounded internal scrolling and preserve keyboard focus/complete text; exercise 1280x720, 1440x900 and 1920x1080 instead of shrinking text until it disappears.
- Existing tests may encode retired CSS spelling or wording. Delete such incidental tests rather than re-pin them; keep behavioral invariants and update changed consumer contracts.
- Browser aesthetic acceptance is not proven by component tests or by this proposal. During application run the actual changed surface with deterministic fixtures and inspect it; do not claim screenshots or runtime coverage that were not exercised.
- New permanent tests are for uncertain transitions, error paths and consumer-visible boundaries only. Do not pre-invent traceability IDs. Discover canonical IDs with the project tool after main-spec sync during application and annotate only tests that establish the requirement.

## Delivery boundary

One engineer-day covers the named surface, focused regression work and visual smoke. The matrix explicitly assigns all report findings, including rejected suggested fixes. Keyboard and pointer behavior remain supported; no gamepad mapping is added because the current client has no gamepad contract. Reduced/off motion, truthful unavailable state and native browser zoom remain required.
