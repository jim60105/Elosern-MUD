# Align drawer chrome symbols with the v2 redesign

## Why

Two drawer-chrome details still read differently from the binding mock
(`docs/design/elosern-redesign/index.html`):

1. Symbol: the mock's `背包 · 裝備` head icon is the backpack outline
   (`M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2`, index.html:958); the shipped
   `inventory` glyph in `dock-icons.js:18` is a box/crate silhouette
   (`M4 7h16v12H4V7zm2-2h12l-1 2H7L5 5z`), so the drawer head does not match
   the redesign's symbol language (the dock tab uses the same key and the mock's
   `道具` tab shares that backpack glyph, index.html:833).
2. Geometry and head type: the mock's drawer starts below the always-visible
   46px command line (`.draw{top:46px}`, index.html:404) and its head title is
   20px display type with `.04em` tracking (index.html:410); the shipped
   `.hud-drawer` spans `top:0` over the command line and titles at `1em`.

Both are cheap, self-contained chrome fixes; the mock's close button, head
layout, and scrim already match.

## What Changes

- Replace the `inventory` glyph path in `web/webclient-app/components/dock-icons.js`
   with the mock's backpack outline (same stroke attrs); the `items` combat key
   already points at a bag glyph — align it to the identical backpack path so
   the symbol is stable across the dock tab and the drawer head.
- Anchor `.hud-drawer` below the persistent command-line strip:
  `top: var(--command-line-h)` (token already exists, `tokens.css:118`); the
  scrim keeps covering the whole stage as today.
- Head title typography: 20px, `letter-spacing:.04em` (mock `.dhead h3`),
  subtitle 11px `--paper-500` (mock `.dhead .sub`); existing order
  (icon → title → subtitle → close) already matches.
- No copy, protocol, or behavior changes; all testids preserved.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-contextual-hud`: requirement
  `Reference surfaces render in a right-anchored drawer with one modal
  contract` — the drawer spans the stage from the top edge of the persistent
  command-line strip to the stage bottom (the scrim still covers the whole
  stage), and the head title adopts the reference's display type scale.

## Impact

- Code: `dock-icons.js` (two path values), `HudDrawer.vue` scoped CSS
  (`top`, title/subtype sizes) — no template changes.
- Tests: pin the old icon path at
  `web/webclient-app/tests/app_client_drawers.test.js:189,266` → update to the
  backpack path; extend the drawer geometry assertion (top offset equals the
  command-line token) in the same file's existing `covers_requirement`-annotated
  tests; managed `web/tests/browser/test_browser_services.py` drawer-bounds and
  icon assertions if any, run locally as the single class.
- Showcase: add one `args`-bound inventory-head variant under the existing
  `Core/HudDrawer` title (the showcase has no viewable backpack-icon state
  today); no new story titles (frozen manifest untouched).
- Glyph tests: `web/webclient-app/tests/action/dock_icons.test.js` pins only
  `items` today; it gains the `inventory` backpack path plus an
  `inventory === items` equality assertion.
- No command-surface change; no backward compatibility work.
