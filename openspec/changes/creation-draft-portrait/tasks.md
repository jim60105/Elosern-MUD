# Tasks

## 1. Slot and contextual drawer

- [ ] 1.1 Extend the real `CreationPortraitSlot.vue` for the closed union, existing motion preferences, accessible status/alt text and generation intent. Add `tests/overlays/creation_portrait.test.js` cases for each state, disabled controls, ready art and silhouette fallback; the focused Vitest command in design must pass without copy/markup pins.
- [ ] 1.2 Add optional `context` to `GalleryGenerateDrawer.vue`, preserving its gallery default and capability behavior. Mount it above creation with the exact free-text-only view-model projection in design. Extend drawer/component tests for creation exclusions, retained prompt and unchanged ordinary gallery behavior; verify no `gallery.generate` or action is sent on opening.
- [ ] 1.3 Compose `use-creation-portrait.js` into the existing overlay facade and dispatch only the exact five-key payload from current form refs on submit. Test null admission, synchronous failure, matching/foreign results, result-before-panel ordering, drawer focus/Escape priority, reconnect teardown and zero automatic retry. Expected state is no concept text leakage and no custom save/activation.

## 2. Live journey evidence

- [ ] 2.1 Add `CreationPortraitJourneys.test_generate_while_editing` and `test_reconnect_and_reset` in `web/tests/browser/test_browser_creation_portrait.py`, with managed synthetic seed/fake-client support. Drive the real request/queue/worker/push path, retain unsent fields/step during pending-to-ready, and prove reconnect submits no duplicate and reset rejects late output. Run each named browser command in design independently after `pnpm run build`.
- [ ] 2.2 Add focused failure/retry and custom/preset activation disposition methods in the same browser module and register every new method via `uv run --locked python -m tools.shard_register fix`. Verify failed input retention, no duplicate activation generation, preset cleanup and offline preset/custom play using deterministic state waits; run each new method independently.
- [ ] 2.3 Update real overlay/slot/drawer stories and schema-8 fixtures, component-manifest coverage and frontend/synchronization documentation. Produce this change’s human-reviewed `visual-review.md` for the two reference viewports, motion levels, all portrait states and nested focus. Expected evidence uses real components and pins no shipped data/copy.

## 3. Integrated acceptance

- [ ] 3.1 Run focused Vitest and browser commands in design, `pnpm run build-storybook`, `pnpm run showcase-coverage` and `uv run --locked python -m tools.contract_gate` once after integration. Expect passing stories/coverage/registered tests, no page-level horizontal overflow, no wall-clock assertion and no weakened gate.
- [ ] 3.2 Run `openspec validate creation-draft-portrait --strict` and record concrete test-to-delta-scenario evidence; all warnings fail. Preserve the prerequisite schema/version and ownership contracts rather than adding another panel cutover or compatibility shim.
