# Tasks — align-drawer-chrome-symbols

## 1. Symbols

- [x] 1.1 In `web/webclient-app/components/dock-icons.js`, set the `inventory`
  glyph to the mock's backpack outline
  (`M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2`), the identical string already used by
  `items`; update the table comment to name the reference line
  (`index.html:958`).
- [x] 1.1a Pin the change in `web/webclient-app/tests/action/dock_icons.test.js`:
  assert the `inventory` glyph equals the mock backpack path and equals the
  `items` glyph (the table currently only pins `items`), so neither key can
  regress independently.

## 2. Chrome geometry and type

- [x] 2.1 In `HudDrawer.vue`, anchor the drawer at `top: var(--command-line-h)`
  (scrim keeps `inset:0`); set the head title to the reference display scale
  (`font-size:20px; letter-spacing:.04em`) and the subtitle to `11px`
  `--paper-500`.

## 3. Tests with the behavior

- [x] 3.1 Update the pinned glyph paths at
  `web/webclient-app/tests/app_client_drawers.test.js:206,284` to the backpack
  outline and keep asserting the drawer-head title element/class in the same
  vitest file; add selector-pinned source assertions to
  `web/webclient-app/tests/hud_drawer.test.js` (the component's own CSS-rule
  blocks, following that file's existing readFileSync pattern): the
  `.hud-drawer` rule carries `top: var(--command-line-h)` and `bottom: 0`, the
  scrim rule keeps `inset: 0`, the `.hud-drawer__title` rule carries
  `font-size: 20px` and `letter-spacing: .04em`, and the
  `.hud-drawer__subtitle` rule carries `font-size: 11px`. That file is executed
  by the modified requirement's `covers_requirement`-annotated evidence test
  `test_reference_drawer_modal_contract` in
  `web/webclient/tests/test_vue_hud_drawer_evidence.py` (canonical ID via
  `tools.spec_traceability list`), so update that test's comment to name the
  new clauses; no Python behavior change is needed.
- [x] 3.2 Audit `web/tests/browser/` for full-height drawer bounds or
  `inventory` icon-path assertions. Audit result: none exist
  (`test_vue_foundation.py`'s boundedness check is geometry-agnostic), so no
  managed browser file changes; the browser suite stays CI-owned and no local
  browser class run is required by this change.

## 4. Showcase and gates

- [x] 4.1 Add one `args`-bound variant export under the existing
  `Core/HudDrawer` title showing the inventory-drawer head state (backpack
  `icon: "inventory"` + wallet subtitle) — the showcase currently has no
  viewable state for it. Verification is head-chrome only: the drawer is
  `position: fixed` against the iframe viewport, so Storybook cannot evidence
  stage-relative 46px geometry (that clause is covered by the 3.1 source
  assertions plus the CI browser suite); capture the rendered head as a
  screenshot artifact for human review — screenshot read-back is not
  available to the implementing agent — and pin the head state itself via the
  1.1a/3.1 vitest assertions. No new story titles;
  `npm run showcase-coverage` green.
- [x] 4.2 `npm test`; `openspec validate align-drawer-chrome-symbols --strict`;
  `uv run --locked python -m tools.spec_traceability check`; `git diff --check`
  clean.
