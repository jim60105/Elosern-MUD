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

## Implementation notes

- Tokens (`styles/tokens.css`): `--message-line-height: 1.5`, `--message-paragraph-gap: .45em`, `--band-strip-actions-w: 104px` (the strip's 日誌 / ⌨ footprint plus a gap), and the level token `--motion-marker-bob` (1.6s; 0ms at reduced, off and the OS fallback) with the level-independent `--motion-marker-travel: 2px` scaled by `--motion-travel`.
- `MessageWindow.vue` defines `--message-page-font` and `--message-measure` once on the window (redefined for the left-aligned dialogue column); the page's `max-width`, the plate's `max-width`, and the marker's `right` all read them. The marker's `right` is `max(--band-strip-actions-w, <gap from the column edge to the window edge> + 24px)`, computed from percentages of the control strip (no container query, so the strip's containment and the shell-owned 日誌 / ⌨ are untouched). At 1920x1080 exploration keeps the clamped 104px; dialogue moves the marker under the prose column's edge (x≈1291 instead of ≈1804).
- CJK spacing is on `.message-window__page` (shared with the hidden measurer) and on the full log's prose lines: `text-autospace: normal`, `text-spacing-trim: trim-start`, `line-break: strict`. Chrome 153 applies autospace with identical widths whether the text is one node or split by the typewriter's hidden tail; `text-spacing-trim` has no visible effect with the self-hosted Noto Serif TC (centred punctuation) and stays as progressive enhancement. `hanging-punctuation` was dropped (Safari-only, would hang glyphs outside the clipped page). Map lines (and the full log's echoed commands) opt out; no `halt`/`palt` is set anywhere.
- Capacity at 1080 moves from 6 to 5 lines in exploration and from 5 to 4 in dialogue; paging is measured, so nothing clips (verified at all three acceptance viewports and prose scales 1 / 1.12).
- The plate's underline moved from the full row onto a `message-window__plate-line` wrapper around name and bond, starting at the name's left edge on a 5px lozenge. The reading rule is one gold rule at opacity 0, shown only on `:focus-visible` of the page in every mode.
- `DialogueChoices.vue`: `firstEnabled()` (ignoring the exits' back row) seeds `activeIndex` and every view swap without an explicit index; an unfocused list shows a quiet active-row treatment; decorative `dialogue-choices__corners` brackets; the leave badge is an inline SVG cross in the seal tint and the red whole-row active frame is gone.
