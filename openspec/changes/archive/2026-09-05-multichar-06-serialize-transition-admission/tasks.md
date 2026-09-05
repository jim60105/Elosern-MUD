# Tasks: multichar-06-serialize-transition-admission

## 1. The pending-transition marker

- [x] 1.1 `web/webclient/actions/account_actions.py`: add `TRANSITION_PENDING_CODE =
  "transition_pending"` and `TRANSITION_PENDING_MESSAGE = "角色切換正在進行中，請稍候。"` module
  constants, and three small helpers: `_transition_pending(session) -> bool`,
  `_set_transition_pending(session) -> None`, `_clear_transition_pending(session) -> None`,
  each reading/writing exactly one shared `session.ndb.elosern_char_transition_pending` boolean.
- [x] 1.2 Add a short module-docstring paragraph (alongside the existing "Architectural Contract"
  section) naming the invariant this establishes: at most one scheduled-but-unexecuted transition
  per session, and why a plain boolean is sufficient (admission-time rejection makes two
  concurrently-scheduled transitions structurally impossible; see design.md D2/D3).

## 2. Admission and scheduling

- [x] 2.1 `_account_character_switch_adapter`: check `_transition_pending(session)` first, before
  resolving `actor.account` or any other check (including the existing `in_combat`,
  `invalid_character`, and `already_current` checks); if set, return the `transition_pending`
  rejection (`no_presentation: True`) and schedule nothing, regardless of whether the request would
  otherwise also have been rejected for another reason. Otherwise, call
  `clock.callLater(0, _perform_switch, ...)` **first**, and only once that call returns, call
  `_set_transition_pending(session)` — schedule-then-set, not set-then-schedule (design.md D6): if
  scheduling itself somehow raises, the marker must never have been set, so there is nothing to
  leak.
- [x] 2.2 `_account_character_create_adapter`: the same admission-check-first ordering and the same
  schedule-then-set sequencing immediately around its `clock.callLater(0, _perform_create, ...)`.
- [x] 2.3 `_perform_switch`: wrap the existing full function body in `try: ... finally:
  _clear_transition_pending(session)` with no change to any existing branch's logic, ordering, or
  return value.
- [x] 2.4 `_perform_create`: the same `try/finally` wrap around its existing full body.

## 3. Tests

- [x] 3.1 `web/webclient/actions/tests/test_account_actions.py`: a second `account.character.switch`
  submitted while a first switch's transition is scheduled but not yet run (inject the test
  `Clock`, do not advance it) is rejected with `transition_pending`; `session.puppet` and the
  coordinator epoch are unchanged; no second `callLater` was scheduled (assert the clock holds
  exactly one pending call).
- [x] 3.2 Cross-action coverage: `account.character.create` submitted while a switch is pending is
  rejected with `transition_pending` with no character object created; `account.character.switch`
  submitted while a create is pending is rejected with `transition_pending` with no puppet change
  scheduled.
- [x] 3.2a Precedence: while a transition is pending, submit a second `account.character.switch`
  that would *also* independently fail for its own reason — a foreign/non-owned `character_id`,
  the session's puppet being in combat, or naming the already-current puppet — and assert each is
  rejected with `transition_pending`, never with `invalid_character`, `in_combat`, or
  `already_current`. Covers the ordering guarantee in design.md D5/spec.md's precedence scenario.
- [x] 3.2b A third request submitted while the marker is still set from the first is rejected the
  same way as the second (the rejection itself does not reset, clear, or extend the marker).
- [x] 3.3 After advancing the clock to let the first transition complete (success case), a
  subsequent `account.character.switch`/`account.character.create` is admitted normally (not
  rejected as pending).
- [x] 3.4 The marker clears after each existing recovery path. For the paths that leave the
  session holding a puppet — recovery rung 1 (silent refusal retains current puppet), rung 2
  (repaired after unpuppet), the late capacity/combat re-check cancellations for create, and the
  externally-reassigned stale-puppet cancellations for both switch and create — reuse the existing
  per-scenario setup from the current test classes rather than re-deriving it, and add only the
  "marker cleared, next request admitted normally" assertion at the end of each. For rung 3
  (unrecoverable, session left with no character), assert instead that the marker no longer refuses
  as `transition_pending`: a direct second request from the puppet-less session must not carry the
  pending code (the real entry gate answers puppet-less sessions with the ordinary no-puppet
  rejection; the pending refusal must never shadow it).
- [x] 3.4a Exception escape: with an admitted switch and an admitted create, make a dependency of
  the scheduled callback raise an uncaught exception, advance the clock, and assert the exception
  propagates while the marker is cleared — a subsequent valid request is admitted normally, not
  refused as `transition_pending` (proves the `try/finally` wrap, design.md D4).
- [x] 3.5 Full regression pass of the existing single-request test suite in this file
  (`test_account_actions.py`) with no behavior change: same assertions, same outcomes, same call
  counts as before this change.
- [x] 3.6 `covers_requirement` annotations for the new `webclient-character-roster`
  requirement (ID from `uv run --locked python -m tools.spec_traceability list`), one per scenario.

## 4. Cleanup

- [x] 4.1 `commands/localized/account.py`: delete the unused `from django.conf import settings`
  line. Confirm with a repo-wide grep that no other symbol in the file reads `settings`.
- [x] 4.2 Confirm `commands/tests/test_localized.py` (or wherever this module's existing tests
  live) still imports and runs cleanly with no reference to the removed import.

## 5. Verification

- [x] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  web.webclient commands`.
- [x] 5.2 `uv run --locked python -m tools.spec_traceability check` and
  `uv run --locked python -m tools.observability_lint check`.
- [x] 5.3 `uv run --locked python -m compileall -q web/webclient commands`.
- [x] 5.4 Live container check: from a browser session with two or more characters, rapidly click
  two different roster rows before the first switch's snapshot lands, and confirm the second click
  is refused with a visible rejection rather than silently doing nothing while looking like it
  succeeded; repeat with switch-then-create-confirm in rapid succession.
