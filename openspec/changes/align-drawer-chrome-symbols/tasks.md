# Tasks — align-drawer-chrome-symbols

## 1. Symbols

- [ ] 1.1 In `web/webclient-app/components/dock-icons.js`, set the `inventory`
  glyph to the mock's backpack outline
  (`M4 8h16v11H4zM8 8V6a4 4 0 0 1 8 0v2`), the identical string already used by
  `items`; update the table comment to name the reference line
  (`index.html:958`).
- [ ] 1.1a Pin the change in `web/webclient-app/tests/action/dock_icons.test.js`:
  assert the `inventory` glyph equals the mock backpack path and equals the
  `items` glyph (the table currently only pins `items`), so neither key can
  regress independently.

## 2. Chrome geometry and type

- [ ] 2.1 In `HudDrawer.vue`, anchor the drawer at `top: var(--command-line-h)`
  (scrim keeps `inset:0`); set the head title to the reference display scale
  (`font-size:20px; letter-spacing:.04em`) and the subtitle to `11px`
  `--paper-500`.

## 3. Tests with the behavior

- [ ] 3.1 Update the pinned glyph paths at
  `web/webclient-app/tests/app_client_drawers.test.js:189,266` to the backpack
  outline and assert the drawer-head title carries the reference type scale
  classes in the same vitest file; extend
  `web/webclient/tests/test_vue_hud_drawer_evidence.py` (or the managed
  contextual-HUD test that carries the requirement's `covers_requirement`
  literal IDs — locate via `uv run --locked python -m tools.spec_traceability
  list`) with the command-line top-offset assertion for the modified
  requirement.
- [ ] 3.2 Audit `web/tests/browser/test_browser_services.py` for full-height
  drawer bounds or `inventory` icon-path assertions and update them; run that
  single browser class locally.

## 4. Showcase and gates

- [ ] 4.1 Add one `args`-bound variant export under the existing
  `Core/HudDrawer` title showing the inventory-drawer head state (backpack
  `icon: "inventory"` + wallet subtitle) — the showcase currently has no
  viewable state for it; verify the head against the mock (agent-browser
  screenshot pair). No new story titles; `npm run showcase-coverage` green.
- [ ] 4.2 `npm test`; `openspec validate align-drawer-chrome-symbols --strict`;
  `uv run --locked python -m tools.spec_traceability check`; `git diff --check`
  clean.
