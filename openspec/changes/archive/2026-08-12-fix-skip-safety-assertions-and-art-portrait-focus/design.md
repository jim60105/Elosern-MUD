# Design: Stale Skip-Safety Assertions and Art-Portrait Focus Race

## Context

The quality-gate CI has failed on three consecutive merges (`f30a5c8`,
`12cd262`, `95d59e7`) with the same deterministic Evennia failure:

```text
FAIL: test_restore_registers_live_session_skip_safety_state
AssertionError: 'Char' not found in {'6': Battlefield(...), '17': Battlefield(...)}
```

`fix-battlefield-identity-collisions` (merged `95d0335`) re-keyed the
process-global `world.rules.skip_safety._BATTLEFIELDS` registry from each
participant's mutable display key to its immutable dbref
(`{str(entity.pk): battlefield}`) and updated the assertion sites in
`test_skip_safety.py`, `test_combat_party.py`, `test_guild_exams.py`, and the
`BattlefieldIsolation` mixin — but missed `StartupSessionRestoreOrderTests.
test_restore_registers_live_session_skip_safety_state` in
`world/maps/tests/test_wilderness_population.py`, which still asserts
`str(self.player.key)` / `str(self.monster.key)`. The failure reproduces
locally in 0.16 s (verified) and is pure test debt: the production contract
(dbref keying) is already correct and specified in the `skip-safety-gate` spec.

The same run surfaced one browser flake in the art shard:
`ArtCombatBrowserTest.test_keyboard_focus_switches_the_portrait_without_a_packet`
timed out after 15 s waiting for the portrait name to switch to the focused
enemy target's name after pressing Enter. The journey presses Enter without
establishing DOM focus; `routeKeyboard` in `elosern_ui.js` routes Enter to the
command drawer's send path whenever the drawer field (`#inputfield` inside
`.inputfieldwrapper`) holds focus, silently dropping the keystroke. Every other
combat keyboard journey (`test_browser_combat.py`, `test_browser_services.py`,
`test_browser_actions.py`, `test_browser_shell.py`) explicitly runs
`document.getElementById('action-dock').focus()` before pressing keys; the art
journey is the only one missing it. Where focus lands after login is
timing-dependent, which explains the single CI observation in three runs.

## Goals / Non-Goals

**Goals:**
- Make the Evennia suite green again with assertions that match the registry's
  actual key domain (dbref), with zero production behavior change.
- Make the art-panel keyboard journey deterministic by following the
  repository's established dock-focus pattern, and give its sibling journey
  the same protection.
- Codify both test contracts in main specs so the regression class cannot
  silently recur.

**Non-Goals:**
- No change to `world/rules/skip_safety.py` or any other production code.
- No change to the skip-safety registry keying decision; the dbref contract
  stands as specified in `skip-safety-gate`.
- No rework of the keyboard router or the drawer routing gate (the browser
  behavior is correct; the test just needs the documented focus precondition).
- No new test-infrastructure, dependency, or CI-workflow changes.

## Decisions

### 1. Correct the assertions to the dbref key domain

`test_restore_registers_live_session_skip_safety_state` asserts
`str(self.player.pk)` and `str(self.monster.pk)` in `_BATTLEFIELDS`. The
registry keys are exactly `{str(entity.pk): battlefield}` per participant
(`register_active_battlefield`), so the pk form is both correct and aligned
with every other assertion site in the suite.

Alternatives considered: asserting roster membership
(`any(entity.key == ... for battlefield in _BATTLEFIELDS.values())`) would be
weaker (it cannot detect that the actor's own registration is missing) and
would diverge from the sibling assertion style. Keeping the display-key
assertion is rejected outright: it is the bug.

### 2. Focus the action dock before any key press in the art combat journeys

After `_engage(page)` (combat mode confirmed via state), each keyboard journey
in `ArtCombatBrowserTest` runs
`page.evaluate("document.getElementById('action-dock').focus()")` and then
waits for the combat dock's first row (`#combat-row-0`) to be mounted before
the first key press. `renderCombatRows` runs synchronously inside the
`keyboard.reset(...)` focus emission in the combat dock's state subscription,
so a mounted `#combat-row-0` proves the router frame exists and the dock owns
the key path. The journey additionally waits for
`!window.Elosern.keyboard.isMutationInFlight()` so the KeyboardRouter's
submission gate (`keyboard_router.js` `confirm()`, `mutationInFlight ||
isAwaitingRevision()`) is provably open; `isAwaitingRevision` is never set in
production, so the in-flight check is the only real gate.

Alternatives considered: pressing Escape first to dismiss a hypothetical open
drawer would be heuristic and could pop a real menu; blurring the active
element (`document.activeElement.blur()`) changes what the test documents
rather than what the shell documents; a retry loop around Enter would risk a
double submission once the target menu is open (a second Enter would cast).
Explicit dock focus is the documented shell contract and the existing pattern.

### 3. Wait for the target menu frame, navigate to the enemy target, then assert the portrait

After Enter, the journey waits for `#combat-row-0`'s `data-item-key` to begin
with `target-` (the basic-attack target frame). The single-target menu lists
participants in presenter order (the actor first — verified by runtime
debugging: `basic_attack.targets` is `[actor, monster]`), so the journey then
presses ArrowRight and waits for the focused row to carry the enemy target's
key (`target-<monster_id>`) before asserting the portrait name switched — the
same "move past the actor to the monster" navigation the combat-menu journeys
document. If any frame never mounts, the failure names the missing frame
instead of a bare 15-second portrait-name timeout, and it cannot pass for the
wrong reason (the name comparison stays as the final assertion, so the
no-focus-packet and name-switch semantics are unchanged).

### 4. Spec deltas capture the two test contracts

- `evennia-test-optimization` (existing "Tests restore process-global registry
  state" requirement family): new ADDED requirement that a test asserting a
  covered registry's contents uses that registry's documented key domain — the
  skip-safety battlefield registry keys by participant dbref, so display-key
  assertions are a contract violation. This is the direct, annotated behavior
  test for the CI failure.
- `webclient-browser-verification` (existing "Browser tests are localhost-only
  and deterministic" requirement family): new ADDED requirement scoped to the
  art-panel portrait keyboard journeys — they focus the action dock, wait for
  the mounted and unlocked router frame before pressing keys, and await the
  target-menu frame before asserting the switched portrait. The scope is
  deliberately narrow: other keyboard journeys (e.g.
  `test_browser_combat.py::test_attack_flow_submits_basic_attack_once`) do not
  explicitly focus the dock and are NOT covered by this contract, so no
  existing test violates it.

Both deltas are ADDED requirements with behavior tests in this change, keeping
the traceability gate green (`covers_requirement` annotations only after the
main spec identifiers exist at sync time). The existing annotations on the
sibling `test_restart_settles_committed_victory_before_reconciliation`
(`player-combat-session::...` and `wilderness-monster-population::...`) are
preserved; the corrected `test_restore_registers_live_session_skip_safety_state`
currently carries no annotation and gains the new one plus its existing
subject-matter annotations as appropriate.

## Risks / Trade-offs

- [The browser fix may not reproduce the exact CI race] → The precondition
  (dock focus + mounted router frame) removes every plausible swallow path
  (drawer field focus, editable target, unmounted frame); the remaining
  assertion semantics are unchanged. The managed browser shard is the final
  evidence.
- [Adding spec requirements widens the traceability contract] → Each added
  requirement ships with its annotated behavior test in this change, and the
  existing `covers_requirement` discipline is followed.
- [The evennia fix is one-line; a future keying change could regress it again]
  → The new `evennia-test-optimization` scenario makes display-key assertions
  on the registry an explicit contract violation; the corrected test is itself
  the behavior test for that scenario.
- [Parallel/shuffled order could still expose other stale sites] → A full
  parallel + shuffled verification run is part of the tasks, mirroring the
  documented isolation-check discipline.

## Migration Plan

No production or data migration: the change touches only tests and spec
artifacts. Verification order: focused test → affected packages → full
non-browser suite (parallel and serial) → managed browser shard 6
(`test_browser_art` + `test_harness`) → traceability check. The retained test
database needs no rebuild (no migration change).

## Open Questions

None.
