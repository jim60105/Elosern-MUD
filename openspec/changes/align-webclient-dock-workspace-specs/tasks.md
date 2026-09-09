# Tasks: align-webclient-dock-workspace-specs

## 1. Contract verification (behavior already shipped)

- [ ] 1.1 Confirm the shipped band values in `web/webclient-app/styles/app-shell.css`
  still match the delta wording: base `--dock-h` clamp, the
  `:has(.interaction-workspace)` and `:has(.waiting-screen)` overrides, the
  combat clamp with its empty-pane collapse, the two-column
  `.dock-pane-host.interaction-workspace` grid with the
  `--selected` second-column rule, the `@media (max-width: 1000px)` target-grid
  collapse, and the dialogue-mode feed clamp. If any constant moved, update the
  delta's named constants, not the CSS.
- [ ] 1.2 Confirm `web/webclient-app/components/DockMenu.vue` and
  `AppClient.vue` still wire the workspace pane and anchor widening exactly as
  the synced `webclient-exploration-menu` paragraph describes.

## 2. Sync obligations at archive time

- [ ] 2.1 Sync both delta specs into `openspec/specs/` and re-run
  `uv run --locked python -m tools.spec_traceability list` — the modified
  requirements keep their existing slugs, so no annotation churn is expected;
  confirm with `uv run --locked python -m tools.spec_traceability check`.
- [ ] 2.2 Confirm the managed browser geometry rows (feed/dock non-overlap,
  scroll-reachable last option) exist for the new shell scenarios; if a row is
  genuinely missing, note it in the archive proposal as the requirement's
  evidence gap rather than shipping a fake test.

## 3. Verification

- [ ] 3.1 `openspec validate align-webclient-dock-workspace-specs --strict`.
- [ ] 3.2 Node gate + Vitest layout files: `node --test
  web/static/webclient/js/tests/*.test.js` and `npx --no-install vitest run
  web/webclient-app/tests/action/action_dock.test.js
  web/webclient-app/tests/components/dock_panes.test.js`.
- [ ] 3.3 At archive time: `openspec validate --all --strict`.
