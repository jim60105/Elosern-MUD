# Fix Stale Skip-Safety Assertions and Art-Portrait Focus Race

## Why

The quality-gate CI has been red on three consecutive merges with one
deterministic failure: `StartupSessionRestoreOrderTests.
test_restore_registers_live_session_skip_safety_state` asserts that
`world.rules.skip_safety._BATTLEFIELDS` is keyed by participant display keys,
but the `fix-battlefield-identity-collisions` change (merged as `95d0335`)
re-keyed that process-global registry to participant **dbrefs** and updated
every other assertion site except this one. The same run also surfaced one
browser flake (`web.tests.browser.test_browser_art`.
`ArtCombatBrowserTest.test_keyboard_focus_switches_the_portrait_without_a_packet`)
that times out waiting for the portrait to switch after an Enter press that the
keyboard router never receives, because the test — unlike every other combat
keyboard journey — never focuses the action dock before pressing keys.

## What Changes

- Fix the stale test assertions in
  `world/maps/tests/test_wilderness_population.py`:
  `test_restore_registers_live_session_skip_safety_state` asserts
  `str(self.player.pk)` / `str(self.monster.pk)` membership in
  `_BATTLEFIELDS`, matching the dbref-keyed contract the registry has
  implemented since `fix-battlefield-identity-collisions`. No production
  behavior changes.
- Harden the flaky art-panel keyboard journey in
  `web/tests/browser/test_browser_art.py`: after engaging combat, the journey
  focuses `#action-dock` (the documented pattern in `test_browser_shell.py`,
  `test_browser_combat.py`, `test_browser_services.py`, and
  `test_browser_actions.py`), waits for the combat dock's mounted router frame
  (`#combat-row-0`) and for the router to be unlocked before pressing Enter, so
  the key event can never be swallowed by the command drawer or an editable
  field; after Enter it waits for the target menu frame to mount, moves focus
  past the actor to the enemy target (the single-target menu lists the actor
  first in presenter order), and only then asserts the portrait name — turning
  a bare 15-second timeout into a precise diagnostic. The sibling
  `test_defeated_participant_leaves_the_catalog_in_the_same_update` gets the
  same dock-focus and mounted-frame steps (it has the same latent race) and
  waits for the forfeit-confirmation frame between its two Enter presses.
- No player-facing command surface, production code, dependency, or schema
  changes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `evennia-test-optimization`: the process-global registry isolation contract
  gains the rule that tests asserting a covered registry's contents use that
  registry's documented key domain (for the skip-safety battlefield registry:
  participant dbrefs, never display keys), so a keying-contract change can no
  longer silently redden the suite.
- `webclient-browser-verification`: the deterministic-browser-test contract
  gains the rule that art-panel keyboard journeys asserting the client-local
  portrait focus focus the action dock (and wait for the router frame to be
  mounted and unlocked) before pressing keys, and await the target-menu frame
  before asserting the switched portrait.

## Impact

- `world/maps/tests/test_wilderness_population.py` — corrected assertions in
  `StartupSessionRestoreOrderTests`.
- `web/tests/browser/test_browser_art.py` — deterministic keyboard setup in
  `ArtCombatBrowserTest`.
- Delta specs: `evennia-test-optimization` and `webclient-browser-verification`
  gain the ADDED contract rules above, each paired with its behavior test.
- CI: the quality gate stops failing on the stale assertion and the art shard
  stops flaking on the focus race.
- No backward-compatibility or migration concerns (project is unreleased).
