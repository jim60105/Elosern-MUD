# Tasks: Fix Stale Skip-Safety Assertions and Art-Portrait Focus Race

## 1. Correct the stale skip-safety registry assertions

- [x] 1.1 In `world/maps/tests/test_wilderness_population.py`, change
      `test_restore_registers_live_session_skip_safety_state` to assert
      `str(self.player.pk)` and `str(self.monster.pk)` in `_BATTLEFIELDS`
      (replace the stale `str(self.player.key)` / `str(self.monster.key)`
      assertions) and update the docstring/comment to name the dbref-keyed
      contract.
- [x] 1.2 Grep the whole test tree for any remaining `_BATTLEFIELDS` assertion
      using `entity.key` instead of `entity.pk`; none may remain after this
      change.
- [x] 1.3 Annotate the corrected test with
      `covers_requirement("evennia-test-optimization::registry-content-assertions-use-the-registry-s-key-domain")`
      once the delta is synced; the test currently carries no decorator, so the
      annotation is added (verify the canonical ID with
      `tools.spec_traceability list` after sync) and the existing
      `player-combat-session::...` / `wilderness-monster-population::...`
      annotations on the sibling
      `test_restart_settles_committed_victory_before_reconciliation` are
      preserved untouched.
- [x] 1.4 Run the focused test
      (`world.maps.tests.test_wilderness_population.StartupSessionRestoreOrderTests`)
      and confirm it passes with the retained test database.

## 2. Harden the art-panel keyboard browser journeys

- [x] 2.1 In `web/tests/browser/test_browser_art.py`, extract a small helper on
      `ArtCombatBrowserTest` that, after `_engage`, focuses `#action-dock`
      (`page.evaluate("document.getElementById('action-dock').focus()")`),
      waits for `#combat-row-0` to be mounted (the combat dock's first row,
      which proves the router frame exists), and waits for
      `!window.Elosern.keyboard.isMutationInFlight()` (the router's submission
      gate open).
- [x] 2.2 Rework `test_keyboard_focus_switches_the_portrait_without_a_packet`
      to use the helper before pressing Enter, and after Enter wait for the
      target menu frame (`#combat-row-0` with a `data-item-key` starting with
      `target-`) before asserting the portrait name switched; keep the
      no-focus-packet assertion unchanged.
- [x] 2.3 Add the same dock-focus + mounted-frame + unlocked-router
      precondition to `test_defeated_participant_leaves_the_catalog_in_the_same_update`
      before its ArrowDown/Enter sequence, and wait for the
      forfeit-confirmation frame (`#combat-row-0` with `data-item-key`
      `confirm-forfeit`) between the two Enter presses.
- [x] 2.4 Annotate the hardened journeys with
      `covers_requirement("webclient-browser-verification::art-panel-portrait-keyboard-journeys-establish-dock-focus-before-key-presses")`
      (same sync discipline as 1.3).
- [x] 2.5 Run the art browser shard tests
      (`uv run --locked -m unittest web.tests.browser.test_browser_art`) against
      a managed server and confirm all journeys pass.

## 3. Verify the contracts

- [x] 3.1 Sync the two delta specs into the main specs only after both
      annotated tests exist with the literal requirement IDs; then resolve the
      canonical IDs from `tools.spec_traceability list` and confirm they match
      the annotations.
- [x] 3.2 Run `uv run --locked python -m tools.spec_traceability check` and
      confirm no uncovered or invalid requirement remains.
- [x] 3.3 Collect execution evidence with a shared `OPENSPEC_TEST_EVIDENCE`
      path across the non-browser Evennia suite, the managed browser art
      shard, and the top-level regression command, then run
      `tools.spec_traceability verify --evidence`; all three entry points must
      pass.
- [x] 3.4 Run the affected package suites
      (`world.maps.tests.test_wilderness_population`,
      `world.rules.tests.test_skip_safety`, `world.rules.tests.test_combat_party`),
      the Node suite (`node --test web/static/webclient/js/tests/*.test.js`),
      and the top-level regression command; then run the full non-browser
      Evennia suite once with `--parallel 4 --noinput` and once with the
      serial `--keepdb` profile; all must be green.
- [x] 3.5 Run `git diff --check` and confirm a clean tree, then
      `openspec validate --all --strict` before archiving.
