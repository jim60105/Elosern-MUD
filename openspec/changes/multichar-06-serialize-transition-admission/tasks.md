# Tasks: multichar-06-serialize-transition-admission

## 1. The pending-transition marker

- [ ] 1.1 `web/webclient/actions/account_actions.py`: add `TRANSITION_PENDING_CODE =
  "transition_pending"` and `TRANSITION_PENDING_MESSAGE = "角色切換正在進行中，請稍候。"` module
  constants, and three small helpers: `_transition_pending(session) -> bool`,
  `_set_transition_pending(session) -> None`, `_clear_transition_pending(session) -> None`,
  each reading/writing exactly one shared `session.ndb.elosern_char_transition_pending` boolean.
- [ ] 1.2 Add a short module-docstring paragraph (alongside the existing "Architectural Contract"
  section) naming the invariant this establishes: at most one scheduled-but-unexecuted transition
  per session, and why a plain boolean is sufficient (admission-time rejection makes two
  concurrently-scheduled transitions structurally impossible; see design.md D2/D3).

## 2. Admission and scheduling

- [ ] 2.1 `_account_character_switch_adapter`: check `_transition_pending(session)` first, before
  resolving `actor.account` or any other check (including the existing `in_combat`,
  `invalid_character`, and `already_current` checks); if set, return the `transition_pending`
  rejection (`no_presentation: True`) and schedule nothing, regardless of whether the request would
  otherwise also have been rejected for another reason. Otherwise, call
  `clock.callLater(0, _perform_switch, ...)` **first**, and only once that call returns, call
  `_set_transition_pending(session)` — schedule-then-set, not set-then-schedule (design.md D6): if
  scheduling itself somehow raises, the marker must never have been set, so there is nothing to
  leak.
- [ ] 2.2 `_account_character_create_adapter`: the same admission-check-first ordering and the same
  schedule-then-set sequencing immediately around its `clock.callLater(0, _perform_create, ...)`.
- [ ] 2.3 `_perform_switch`: wrap the existing full function body in `try: ... finally:
  _clear_transition_pending(session)` with no change to any existing branch's logic, ordering, or
  return value.
- [ ] 2.4 `_perform_create`: the same `try/finally` wrap around its existing full body.

## 3. Tests

- [ ] 3.1 `web/webclient/actions/tests/test_account_actions.py`: a second `account.character.switch`
  submitted while a first switch's transition is scheduled but not yet run (inject the test
  `Clock`, do not advance it) is rejected with `transition_pending`; `session.puppet` and the
  coordinator epoch are unchanged; no second `callLater` was scheduled (assert the clock holds
  exactly one pending call).
- [ ] 3.2 Cross-action coverage: `account.character.create` submitted while a switch is pending is
  rejected with `transition_pending` with no character object created; `account.character.switch`
  submitted while a create is pending is rejected with `transition_pending` with no puppet change
  scheduled.
- [ ] 3.2a Precedence: while a transition is pending, submit a second `account.character.switch`
  that would *also* independently fail for its own reason — a foreign/non-owned `character_id`,
  the session's puppet being in combat, or naming the already-current puppet — and assert each is
  rejected with `transition_pending`, never with `invalid_character`, `in_combat`, or
  `already_current`. Covers the ordering guarantee in design.md D5/spec.md's precedence scenario.
- [ ] 3.2b A third request submitted while the marker is still set from the first is rejected the
  same way as the second (the rejection itself does not reset, clear, or extend the marker).
- [ ] 3.3 After advancing the clock to let the first transition complete (success case), a
  subsequent `account.character.switch`/`account.character.create` is admitted normally (not
  rejected as pending).
- [ ] 3.4 The marker clears after each existing recovery path, proven by admitting a fresh request
  immediately after each: recovery rung 1 (silent refusal retains current puppet), rung 2
  (repaired after unpuppet), rung 3 (unrecoverable, session left with no character), the late
  capacity/combat re-check cancellations for create, and the externally-reassigned stale-puppet
  cancellation for switch. Reuse the existing per-scenario setup from the current test classes
  rather than re-deriving it; only add the "marker cleared, next request admitted" assertion at
  the end of each.
- [ ] 3.5 Full regression pass of the existing single-request test suite in this file
  (`test_account_actions.py`) with no behavior change: same assertions, same outcomes, same call
  counts as before this change.
- [ ] 3.6 `covers_requirement` annotations for the six new `webclient-character-roster`
  scenarios (IDs from `uv run --locked python -m tools.spec_traceability list`).

## 4. Cleanup

- [ ] 4.1 `commands/localized/account.py`: delete the unused `from django.conf import settings`
  line. Confirm with a repo-wide grep that no other symbol in the file reads `settings`.
- [ ] 4.2 Confirm `commands/tests/test_localized.py` (or wherever this module's existing tests
  live) still imports and runs cleanly with no reference to the removed import.

## 5. Verification

- [ ] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  web.webclient commands`.
- [ ] 5.2 `uv run --locked python -m tools.spec_traceability check` and
  `uv run --locked python -m tools.observability_lint check`.
- [ ] 5.3 `uv run --locked python -m compileall -q web/webclient commands`.
- [ ] 5.4 Live container check: from a browser session with two or more characters, rapidly click
  two different roster rows before the first switch's snapshot lands, and confirm the second click
  is refused with a visible rejection rather than silently doing nothing while looking like it
  succeeded; repeat with switch-then-create-confirm in rapid succession.
