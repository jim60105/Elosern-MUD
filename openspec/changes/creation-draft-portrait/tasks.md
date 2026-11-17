# Tasks

## 1. Slot and contextual drawer

- [ ] 1.1 Extend the real `CreationPortraitSlot.vue` for the closed union, existing motion preferences, accessible status/alt text and generation/refresh intents. Wire `request-sync` through overlay/AppClient to existing `store.requestPresentationSync("manual")`. Add state/disabled/refresh tests proving server reason display, no probe or generation during refresh and preserved form state; focused Vitest must pass without copy/markup pins.
- [ ] 1.2 Add optional `context` and `unavailableReason` to `GalleryGenerateDrawer.vue`, preserving gallery defaults. Mount it above creation with the exact free-text-only view model. Creation unavailability disables submit but retains editable prompt and offers refresh inside the focus trap. Extend tests for server-reason/refresh wiring, retained prompt and unchanged gallery behavior; opening/refresh sends no generation action and performs no client probe.
- [ ] 1.3 Compose `use-creation-portrait.js` into the existing overlay facade and dispatch only the exact five-key payload from current form refs on submit. Test null admission, synchronous failure, matching/foreign results, result-before-panel ordering, drawer focus/Escape priority, reconnect teardown and zero automatic retry. Expected state is no concept text leakage and no custom save/activation.

## 2. Live journey evidence

- [ ] 2.1 Add `CreationPortraitJourneys.test_generate_while_editing` and `test_reconnect_and_reset` in `web/tests/browser/test_browser_creation_portrait.py`, with managed synthetic seed/fake-client support. Drive the real request/queue/worker/push path, retain unsent fields/step during pending-to-ready, and prove reconnect submits no duplicate and reset rejects late output. Run each named browser command in design independently after `pnpm run build`.
- [ ] 2.2 Add `test_offline_refusal_and_explicit_retry` using the design's managed fake-probe/cache control and the named command: no durable write on refusal, disabled server-signal display, manual refresh without enqueue, then one explicit retry to ready with input preserved. Add worker-failure/retry and custom/preset activation disposition methods; register every method via `uv run --locked python -m tools.shard_register fix`. Verify no duplicate activation generation, preset cleanup and offline preset/custom play without wall-clock assertions; run each method independently.
- [ ] 2.3 Update real overlay/slot/drawer stories and schema-8 fixtures, component-manifest coverage and frontend/synchronization documentation. Produce this change’s human-reviewed `visual-review.md` for the two reference viewports, motion levels, all portrait states and nested focus. Expected evidence uses real components and pins no shipped data/copy.

## 3. Integrated acceptance

- [ ] 3.1 Run focused Vitest and browser commands in design, `pnpm run build-storybook`, `pnpm run showcase-coverage` and `uv run --locked python -m tools.contract_gate` once after integration. Expect passing stories/coverage/registered tests, no page-level horizontal overflow, no wall-clock assertion and no weakened gate.
- [ ] 3.2 Run `openspec validate creation-draft-portrait --strict` and record concrete test-to-delta-scenario evidence; all warnings fail. Preserve the prerequisite schema/version and ownership contracts rather than adding another panel cutover or compatibility shim.
