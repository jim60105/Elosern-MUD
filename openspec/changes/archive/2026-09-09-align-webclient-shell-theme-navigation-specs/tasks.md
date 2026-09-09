# Tasks: align-webclient-shell-theme-navigation-specs

## 1. Theme token repair

- [x] 1.1 Define `--gold-600: #8f713c` in `web/webclient-app/styles/tokens.css` inside the
  gold ramp block, and update the file-header comment and the gold block comment from the
  stale "single seal-red accent" wording to the two-family model (seal-red semantic accent +
  muted-gold navigation/focus/emphasis accent). Verify `.ui-btn--primary` and the tab/dock
  gold fills match the comment before rewriting it.
- [x] 1.2 Add the Node-gate regression test to
  `web/static/webclient/js/tests/ui_contract.test.js`: every `var(--x)` consumed by the
  shipped CSS/Vue style sources must be defined somewhere in the same source union. Confirm
  the test fails before 1.1 and passes after.

## 2. Spec sync housekeeping

- [x] 2.1 Rebase prerequisite: archive `align-webclient-waiting-practice-specs` (sync its
  delta into `openspec/specs/`), then re-check this change's stacked
  `webclient-exploration-menu` MODIFIED block against the synced text.
- [x] 2.2 Update the `covers_requirement` slug in
  `web/webclient/tests/test_vue_hud_drawer_evidence.py` to the renamed hud requirement
  (`...reached-from-the-top-navigation-or-the-dock`); confirm the new slug via
  `uv run --locked python -m tools.spec_traceability list`.

## 3. Verification

- [x] 3.1 Focused Python: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
  test_settings.py --keepdb web.webclient.tests.test_vue_hud_drawer_evidence
  web.webclient.tests.test_vue_shell_evidence` (adjust shell label to the existing module
  covering the surfaces scenario).
- [x] 3.2 Node gate: `node --test web/static/webclient/js/tests/ui_contract.test.js`.
- [x] 3.3 Traceability: `uv run --locked python -m tools.spec_traceability check`.
- [x] 3.4 `openspec validate align-webclient-shell-theme-navigation-specs --strict`, and at
  archive time `openspec validate --all --strict`.
- [x] 3.5 Frontend suite + build + collectstatic per the session contract
  (`pnpm test`, `pnpm run build`, `uv run --locked evennia collectstatic --noinput`).
