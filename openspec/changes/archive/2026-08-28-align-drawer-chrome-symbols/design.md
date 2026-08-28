# Design — align-drawer-chrome-symbols

## Context

`dock-icons.js` is the fixed glyph table already sourced from the mock; only the
`inventory` key still carries the box silhouette while the mock's backpack
outline is already shipped under the `items` key (`dock-icons.js:27`). The
drawer chrome (`HudDrawer.vue`) spans `top:0` and titles at `1em`; the mock's
`.draw` is inset 46px from the stage top (`top:46px`, index.html:404) and titles
at 20px / `.04em`. Note (audit correction): the mock's 46px top strip is its
demo-only design switcher, not the command line — the mock's command line and
the shipped `[data-anchor="command-line"]` strip are both bottom-anchored
(`HudFrame.vue:182`), and the mock drawer (`bottom:0`, z-index 90) covers it.
The shipped token `--command-line-h` (`tokens.css:118`) carries that same 46px
value.

## Goals / Non-goals

- Goals: one backpack glyph for `背包` semantics everywhere; the reference's
  46px stage-top clearance; reference head type scale. Template, testids,
  focus, and modal contracts untouched.
- Non-goals: scrim opacity tweaks, drawer shadow depth, the `character` glyph.

## Decisions

### D1 — Glyph: copy the mock path, not invent one

`inventory: "M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2"` (identical to `items`, which
is already the mock string). No new stroke attrs beyond the table default
`stroke-width 1.8` (the mock draws it the same way).

### D2 — Top clearance via the existing token

`.hud-drawer { top: var(--command-line-h); }` reproduces the mock's 46px
stage-top inset with the existing token whose value is that same 46px (no new
token; the bottom edge and the modal z-index stay as today). The scrim keeps
`inset:0` (whole-stage blur per the unchanged requirement wording): everything
behind the open drawer — including the bottom command line and, at narrow
widths, the top brand/meta pill band — is already scrim-covered and inert
exactly as in the mock (the mock drawer likewise covers its bottom command
line), and no top-band visibility guarantee is claimed. The focus-trap
contract is untouched.

### D3 — Type scale literals in the drawer CSS

Title `font-size:20px; letter-spacing:.04em`; subtitle `font-size:11px`
(`--paper-500`). Kept as literals matching the mock rather than new tokens
(the scale appears nowhere else; no token proliferation for two rules).

## Risks / trade-offs

- Any managed geometry assertion that measured a full-height drawer must be
  re-measured. Audit found none: `web/tests/browser/` carries no drawer-bounds
  or `inventory` icon-path assertions (`test_vue_foundation.py`'s viewport
  boundedness check is geometry-agnostic), so the managed browser files stay
  untouched and CI-owned.
- At 94vw the scrim-covered top band (brand/meta pills) can sit behind the
  drawer's top inset; accepted — it mirrors the mock, the band is dimmed and
  inert behind the scrim while any drawer is open.
- The 20px head title widens head height slightly; the head is flex-row with a
  fixed 34px close control, so no wrap risk at 94vw.
