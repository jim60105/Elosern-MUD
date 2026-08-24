## Context

CI run 32705789787 leaves two browser shards red, for two distinct root causes:

1. **Shard 14 (vue-foundation)** — `test_window_elosern_bridge_facades_resolve_and_route`
   fails **deterministically** (reproduced locally). The test dispatches a document `keydown
   ArrowDown` on the exploration root frame and asserts `store.view.focus.key == "action-guild"`.
   The implemented app builds the **G2 hierarchical exploration root** (Move / Look / Interact /
   Character / Quests / Inventory / Wait) with bare item keys (`move`, `look`, `interact`,
   `character`, `quests`, `inventory`, `wait`), rendered as a single-row grid (`gridCols: 7`).
   `ArrowDown` on a single-row grid is a no-op (row stays 0), so the focus key remains `"move"`.
   The test's `action-guild` expectation is a **stale expectation** from the legacy B2 flat
   `context_actions` affordance-list contract, where items were keyed `action-<action_id>` /
   `action-<surface>` (e.g. `action-explore.wait`, `action-guild`). That contract is what
   `web/webclient-app/tests/action/dock_items.test.js` still exercises in isolation, but it is no
   longer the source of the keyboard router's exploration focus frame.

2. **Shard 11 (art-harness-shell)** — `test_missing_scene_uses_the_placeholder_and_play_continues`
   is **flaky in CI only** (passes locally). The assertion `assertCountEquals(page.locator(
   ".art-panel__scene-placeholder").count(), 1)` intermittently observes **two**
   `.art-panel__scene-placeholder` nodes (`AssertionError: 2 == 2`), because under a loaded CI
   runner a snapshot refresh / Vue re-render opens a transient double-node window that a single raw
   count sample lands inside. This is a **timing/load-related flake**, not a permanent art-panel
   behavioral bug — the panel is available and correctly shows the missing placeholder.

## Goals / Non-Goals

**Goals:**
- Turn both failing shards green by aligning the tests and the capability contracts with the
  already-correct app behavior (G2 root keys; stable single placeholder node; bounded DOM-gated
  waits).
- Keep every existing Node gate, the keyboard router, and the deterministic core untouched.
- Produce a single OpenSpec change with proposal + design + tasks + spec deltas, validated with
  `openspec validate --strict`.

**Non-Goals:**
- No app-behavior change: the Vue app and the `KeyboardRouter` are already correct.
- No new dependencies, no data migrations (the project is unreleased, zero users).
- No changes to other shards; the fix is scoped to the two red shards.

## Decisions

1. **Fix the vue-foundation mismatch in the test, not the app.**
   The G2 hierarchical root is the implemented, intended contract. Alternatives considered:
   - *(a) Revert the app to the B2 flat affordance list.* Rejected — that would roll back the
     shipped G2 behavior and re-introduce the flat list the G2 change deliberately replaced.
   - *(b) Update the test to the G2 root.* **Adopted** — minimal, and keeps the Node gate
     (`dock_items.test.js` still covers the B2 `action-`/`target-` key derivation in isolation).

   Concrete test edit (planning; implemented on this branch):
   - After `ArrowDown` on the single-row G2 root, `store.view.focus.key` is `"move"` (the no-op).
     Update `assertEqual(keys["focusKey"], "move")` and keep `focusEnabled`/`downClaimed`/
     `letterSwallowed` assertions.
   - For the Enter block, the G2 root item `move` carries `openSubmenu: "move"`, so Enter pushes the
     move submenu frame. Because the test's committed state has no `exploration` panel, the move submenu
     is `[move-empty (disabled), back]`; after the push, the router's focus lands on the first item
     (`move-empty`, `enabled: false`). Update the Enter assertions to expect `dockDepth == 2` and
     `store.view.focus.key == "move-empty"` with `store.view.focus.enabled == false`, and assert
     `isInFlight() == false` (no `ui_action` dispatched — the submenu push is client-local). Replace
     the `surface == "guild"` / `focusKey == "action-guild"` legacy assertions.

2. **Stabilize the art-panel placeholder assertion with the bounded wait helper.**
   The raw `.count()` sample races a refresh re-render. Decision: gate the DOM-bound assertion on the
   shared bounded wait helper (`wait_for_store_state` with a `{selector, predicate, description}`
   DOM-readiness descriptor) so the test polls until the single placeholder node is present and
   visible, under one monotonic deadline. Alternatives:
   - *(a) Tighten the selector to the scene frame.* **Also adopted** — scope the placeholder lookup
     to the `.art-panel__scene-frame` container (e.g.
     `.art-panel__scene-frame .art-panel__scene-placeholder`) so the unavailable form's node (class
     `art-panel__unavailable`) is excluded and the count is robust.
   - *(b) Retry the raw count in a polling loop.* Effectively what (a) + the bounded helper
     provides; a plain sleep/retry would still be a load-timing hack.

   The bounded helper already exists in `web/tests/browser/browser_helpers.py`
   (`wait_for_store_state`), so no new API is needed — only the test's assertion is re-gated.

3. **Spec deltas amend three capability specs.**
   - `webclient-desktop-shell` → `keyboard-routing-is-menu-first-and-submission-safe`: state the
     exploration keyboard root is the G2 hierarchical menu with bare keys, not the B2 `action-`/
     `target-` prefixed contract.
   - `webclient-art-panel` → `art-degradation-never-blocks-gameplay-or-leaks-rejected-content`: the
     scene placeholder frame SHALL render as exactly one stable DOM node; a missing/failed/pending
     scene degrades to that single placeholder and never leaves a transient second node during a
     snapshot refresh.
   - `webclient-browser-verification` → `browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline`:
     DOM-bound acceptance assertions (counts/visibility) SHALL be gated by the shared bounded wait
     helper using a `{selector, predicate, description}` descriptor, so a delayed render under a
     loaded CI runner does not produce a flaky raw count.

## Risks / Trade-offs

- [Updating the test's expectations could mask a real app regression if G2 is actually wrong] →
  Mitigation: the Node gate (`web/webclient-app/tests/action/dock_items.test.js`, `dock_menu.test.js`)
  still covers the B2 key derivation in isolation, and the focused shard tests are re-run after the
  edit to confirm the router's root is the G2 set.
- [Gating the art count on the bounded helper adds a small polling overhead] → Mitigation: the helper
  polls at 250 ms intervals under a bounded deadline; the overhead is negligible relative to the
  shard's per-test managed-server lifecycle.
- [Scoping the selector to `.art-panel__scene-frame` changes which node is counted] → Mitigation: the
  scoped selector still matches the single scene placeholder node; the unavailable form (a different
  class) is intentionally excluded, matching the missing-scene fixture.

## Migration Plan

No data migration (the project is unreleased). Implementation is test-only:
1. Edit `test_vue_foundation.py` keyboard-routing block + Enter assertions to the G2 root keys.
2. Edit `test_browser_art.py` placeholder assertion to the bounded, scene-frame-scoped count.
3. Re-run the two focused shard tests locally (`vue-foundation`, `art-harness-shell`) to confirm
   green, then let CI validate both shards.
Rollback: revert the two test files and the three spec deltas; no app or schema changes to roll back.

## Open Questions

- Should the vue-foundation Enter block assert the **move submenu** (`dockDepth == 2`) or focus a
  navigation-like root item (e.g. `character`/`quests`/`inventory` sub-dock)? Decision: assert the
  submenu push (`dockDepth == 2`, no `ui_action`), keeping the "Enter on a root item opens a client-
  local submenu without dispatching" contract.
- The art flake is load-related; if CI still flakes after the bounded gate, consider whether the
  double-node window is a genuine (rare) render bug in `ArtPanel.vue`. For this planning change the
  bounded gate + scoped selector is the stabilization; a deeper `ArtPanel` fix is a follow-up only
  if the gate is insufficient.
