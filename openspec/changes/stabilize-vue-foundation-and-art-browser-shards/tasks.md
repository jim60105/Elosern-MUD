## 1. Fix the vue-foundation keyboard-routing expectation (Shard 14)

- [ ] 1.1 Update `test_window_elosern_bridge_facades_resolve_and_route` in `web/tests/browser/test_vue_foundation.py`: change `assertEqual(keys["focusKey"], "action-guild")` to `assertEqual(keys["focusKey"], "move")` (the G2 single-row root makes `ArrowDown` a no-op, so the focus key stays `move`), and update the Enter block to assert `store.view.dockDepth == 2` (Enter on the focused root item pushes its client-local submenu, no `ui_action` dispatched) and `store.view.focus.key == "move-empty"` with `store.view.focus.enabled == false` (the pushed move submenu's first row is the disabled `move-empty` item when the exploration panel is empty); drop the legacy `lastSurface == "guild"` / `focusKey == "action-guild"` assertions.
- [ ] 1.2 Update the test's comment block to describe the G2 hierarchical root (Move/Look/Interact/Character/Quests/Inventory/Wait) instead of the B2 flat `action-`/`target-` affordance list.

## 2. Stabilize the art missing-scene placeholder assertion (Shard 11)

- [ ] 2.1 Update `test_missing_scene_uses_the_placeholder_and_play_continues` in `web/tests/browser/test_browser_art.py`: replace the raw `assertCountEquals(page.locator(".art-panel__scene-placeholder").count(), 1)` with a bounded, scoped assertion — gate on the committed art panel state via `wait_for_store_state`, using the scoped selector `.art-panel__scene-frame .art-panel__scene-placeholder` and a DOM-readiness descriptor asserting a single visible placeholder node, so a transient double-node window under a loaded CI runner no longer fails the shard.
- [ ] 2.2 Confirm the scoped selector excludes the unavailable form (class `art-panel__unavailable`) and only counts the scene placeholder node.
- [ ] 2.3 Update the `covers_requirement` annotation on `test_missing_scene_uses_the_placeholder_and_play_continues` to also claim the amended `webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline` requirement, so the gated, scoped count assertion substantively covers the amended bounded-wait requirement (per the spec-test traceability rule).

## 3. Run the focused shard tests

- [ ] 3.1 Run the vue-foundation focused test locally and confirm green.
- [ ] 3.2 Run the art-harness-shell focused test locally and confirm green (repeat a few times to confirm the flake is gone).
- [ ] 3.3 Run the Node gate `node --test web/static/webclient/js/tests/*.test.js` to confirm the B2 key-derivation gate and the keyboard router Node tests still pass.

## 4. Sync spec deltas and traceability

- [ ] 4.1 Keep the three spec deltas (webclient-desktop-shell, webclient-art-panel, webclient-browser-verification) mutually consistent with proposal.md and design.md.
- [ ] 4.2 Verify the `covers_requirement` annotations on the two edited tests still resolve to canonical requirement IDs (run `uv run --locked python -m tools.spec_traceability check` to confirm the edited tests still substantively cover their requirements).

## 5. Validate the change

- [ ] 5.1 Run `openspec validate stabilize-vue-foundation-and-art-browser-shards --strict` and fix any errors until it passes.
- [ ] 5.2 Invoke the rubber-duck reviewer (sync mode) to independently critique the finished proposal artifacts, address blocking suggestions, then re-run `openspec validate --strict`.
