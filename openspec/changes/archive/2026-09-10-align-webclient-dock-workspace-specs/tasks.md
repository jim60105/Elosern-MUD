# Tasks: align-webclient-dock-workspace-specs

## 1. Contract verification (behavior already shipped)

- [x] 1.1 Confirm the shipped band values in `web/webclient-app/styles/app-shell.css`
  still match the delta wording: base `--dock-h` clamp, the
  `:has(.interaction-workspace)` and `:has(.waiting-screen)` overrides, the
  combat clamp with its empty-pane collapse, the two-column
  `.dock-pane-host.interaction-workspace` grid with the
  `--selected` second-column rule, the `@media (max-width: 1000px)` target-grid
  collapse, and the dialogue-mode feed clamp. If any constant moved, update the
  delta's named constants, not the CSS.
  Verified 2026-09-10 against app-shell.css (base L226, overrides L260-264,
  combat L375-376, workspace grid L272-311, collapse L362-364, dialogue clamp
  L350-351). One discrepancy found and corrected in the delta instead of the
  CSS: the empty-host collapse is two-tier — generic empty host 144px (L256-258),
  which also fires at the ordinary non-degraded exploration root because
  AppClient suppresses DockMenu there (AppClient.vue L1077-1078), with combat's
  empty host overriding to 100px (L378-379). Proposal, design D1, and the shell
  delta now state the cascade, attribute the selectors precisely (:has() for
  interaction/waiting, mode-scoped rules for combat's normal clamp and its
  empty-host override), and scope the shared-measure coupling to non-combat —
  combat's feed/dock pair uses its own shorter band plus explicit offsets
  (L381-389), never --dock-h positioning.
- [x] 1.2 Confirm `web/webclient-app/components/DockMenu.vue` and
  `AppClient.vue` still wire the workspace pane and anchor widening exactly as
  the synced `webclient-exploration-menu` paragraph describes.
  Verified 2026-09-10: AppClient.vue L1026-1029 binds `.dock-pane-host` to
  `interaction-workspace` / `--selected`; the target grid holds column 1
  (L1047-1068), the active-target heading and DockMenu's affordance rows move
  to column 2 under `--selected` (CSS L310-311, single-column nav/affordance
  shape CSS L345-349), and the placeholder prompt fills column 2 pre-selection
  (L1073-1076). Anchor widening applies to both frames (CSS L266-271).

## 2. Sync obligations at archive time

- [x] 2.1 Sync both delta specs into `openspec/specs/` and re-run
  `uv run --locked python -m tools.spec_traceability list` — the modified
  requirements keep their existing slugs, so no annotation churn is expected;
  confirm with `uv run --locked python -m tools.spec_traceability check`.
  Synced 2026-09-10: both MODIFIED requirements spliced verbatim into
  `openspec/specs/`; `list` and `check` both exit 0 with no annotation churn.
- [x] 2.2 Confirm the managed browser geometry rows (feed/dock non-overlap,
  scroll-reachable last option) exist for the new shell scenarios; if a row is
  genuinely missing, note it in the archive proposal as the requirement's
  evidence gap rather than shipping a fake test.
  Assessed at archive 2026-09-10 — partial coverage, recorded as an evidence
  gap in proposal.md ("Managed-browser evidence status"). The standing row is
  `test_no_stage_anchor_overlaps_at_supported_viewports`
  (web/tests/browser/test_browser_layout.py), which asserts stage-anchor
  non-overlap at both viewports; no managed row yet grows the band with a
  tall frame, scrolls the pane to a last row, or bounds the dialogue caption.

## 3. Verification

- [x] 3.1 `openspec validate align-webclient-dock-workspace-specs --strict`.
  Passes after the 1.1 delta correction (2026-09-10).
- [x] 3.2 Node gate + Vitest layout files: `node --test
  web/static/webclient/js/tests/*.test.js` and `npx --no-install vitest run
  web/webclient-app/tests/action/action_dock.test.js
  web/webclient-app/tests/components/dock_panes.test.js`.
  Passes as the prescribed regression gate (449 Node tests; 27 Vitest tests
  across the two layout files). Per the archive-time row-mapping obligation in
  2.2, these are presentation/contract regressions, not the geometry proof for
  the new scenarios — the live-browser rows remain the evidence owner.
- [x] 3.3 At archive time: `openspec validate --all --strict`.
  Passes (exit 0) after the 2.1 sync, immediately before archiving 2026-09-10.
