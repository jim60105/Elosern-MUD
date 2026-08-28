# Design — align-drawer-chrome-symbols

## Context

`dock-icons.js` is the fixed glyph table already sourced from the mock; only the
`inventory` key still carries the box silhouette while the mock's backpack
outline is already shipped under the `items` key (`dock-icons.js:27`). The
drawer chrome (`HudDrawer.vue`) spans `top:0` and titles at `1em`; the mock's
`.draw` clears the 46px command line (token `--command-line-h`,
`tokens.css:118`) and titles at 20px / `.04em`.

## Goals / Non-goals

- Goals: one backpack glyph for `背包` semantics everywhere; command-line
  clearance; reference head type scale. Template, testids, focus, and modal
  contracts untouched.
- Non-goals: scrim opacity tweaks, drawer shadow depth, the `character` glyph.

## Decisions

### D1 — Glyph: copy the mock path, not invent one

`inventory: "M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2"` (identical to `items`, which
is already the mock string). No new stroke attrs beyond the table default
`stroke-width 1.8` (the mock draws it the same way).

### D2 — Top clearance via the existing token

`.hud-drawer { top: var(--command-line-h); }`; the scrim keeps `inset:0`
(whole-stage blur per the unchanged requirement wording). The command line
stays visible-but-inert behind the scrim exactly as in the mock (scrim
`pointer-events:auto`), so the focus-trap contract is untouched.

### D3 — Type scale literals in scoped CSS

Title `font-size:20px; letter-spacing:.04em`; subtitle `font-size:11px`
(`--paper-500`). Kept as literals matching the mock rather than new tokens
(the scale appears nowhere else; no token proliferation for two rules).

## Risks / trade-offs

- Any managed geometry assertion that measured a full-height drawer must be
  re-measured (audit `test_browser_services.py` locally as one class).
- The 20px head title widens head height slightly; the head is flex-row with a
  fixed 34px close control, so no wrap risk at 94vw.
