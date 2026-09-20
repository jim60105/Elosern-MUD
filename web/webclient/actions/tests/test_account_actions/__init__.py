"""
Account action adapter, transition, and dispatcher integration tests (MC3).

Tests the ``account.character.switch`` action:
- Exact payload validation ({character_id} positive int, no booleans, no extras).
- Synchronous authorization decisions (foreign ID, combat lock, self-switch).
- Result-only presentation contract (no_presentation=True, no retiring-epoch snapshot).
- Deferred transition execution on the Twisted reactor turn via an injectable clock seam.
- Verify-and-recover ladder (rungs 1, 2, 3, unexpected puppet, stale puppet cancellation).
- Dispatcher ordering: result delivered before detach signal and new-epoch snapshot.
- Cross-puppet session presentation isolation (options state, barriers, proposals cleared).
- MC6: transition-pending admission serialization — a second switch/create submitted while a
  scheduled transition is still unexecuted is refused synchronously with ``transition_pending``.

Package split of the original flat module; each slice module groups
the shipped classes by concern. Shared module-level helpers live
in ``_support`` (not a collected test module).
"""
