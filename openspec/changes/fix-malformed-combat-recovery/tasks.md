## 1. Parse normalization

- [ ] 1.1 In `read_session` (`world/rules/combat_session.py:249`), wrap `from_storage(dict(raw))` so
      `CombatSessionError` re-raises untouched and `(TypeError, ValueError)` re-raise as
      `CombatSessionError(SessionReason.MALFORMED_SESSION, ...)` chained with `from error`
- [ ] 1.2 Unit tests: payloads `{"not": "a valid record"}`, an integer, and a string each make
      `read_session` raise `CombatSessionError` with the `malformed_session` reason (never a bare
      `TypeError`/`ValueError`), and `is_in_active_session` returns false for each
- [ ] 1.3 Test the still-persisted rejection contract: with a malformed payload persisted, `engage`
      and `forfeit` each raise `CombatSessionError` with the `malformed_session` reason and never a
      bare `TypeError`/`ValueError`

## 2. Recovery boundary restructure

- [ ] 2.1 Move strict parsing inside the recovery boundary: catch `CombatSessionError` from
      `read_session` in `restore_active_session`, log a `log_warn` diagnostic naming the actor and
      reason, call `clear_session(actor, None, None)`, and return — no time settlement, no participant
      effects derived from the payload
- [ ] 2.2 Keep the `settled_tick` fast path after a successful parse (log and clear leftover state,
      never settle again)
- [ ] 2.3 Split the reconstruction handler: `CombatSessionError` from `reconstruct_battlefield` keeps
      the diagnostic `log_warn` plus `_settle_with_restore` termination (defeat / exam FAIL);
      `_terminal_outcome`, `_settle_with_restore`, and `register_active_battlefield` failures
      propagate without clearing or re-settling the valid session
- [ ] 2.4 Update the `restore_active_session` docstring to distinguish unparseable records (cleared,
      never settled) from well-formed records with invalid participant references (diagnostic
      termination)

## 3. Regression tests

- [ ] 3.1 Test with exactly `{"not": "a valid record"}` persisted: `restore_active_session` clears
      `db.active_combat` and `ndb.action_context`, removes the actor's transient battlefield
      registration (the actor's key is no longer in `skip_safety._BATTLEFIELDS`), and does not advance
      the clock
- [ ] 3.2 Test the startup entry: `restore_persisted_sessions()` clears the same payload and a
      subsequent `engage` against a co-located living monster succeeds with a fresh hostile session
- [ ] 3.3 Guard the invalid-references contract: a well-formed record whose enemy dbref is deleted
      still settles diagnostically (defeat) and leaves the player unblocked (existing
      `test_deleted_enemy_does_not_strand_player` stays green)
- [ ] 3.4 Guard the unrelated-failure contract: a valid terminal session whose settlement raises
      (patched `settle_combat_result`) propagates from `restore_active_session` with the durable
      record intact and exactly zero re-settlement attempts (assert the patch was called once)
- [ ] 3.5 Annotate the new startup-recovery tests with
      `covers_requirement("player-combat-session::startup-restores-valid-sessions-and-terminates-invalid-references-safely")`
      (identifier already exists in main specs)
- [ ] 3.6 Before archive/sync, obtain canonical IDs with `uv run --locked python -m
      tools.spec_traceability list` and add `covers_requirement` to the engage/forfeit rejection test
      (task 1.3) for the new main requirement
      (`malformed-session-payloads-fail-closed-without-unhandled-conversion-errors`), then run the
      verifier's `verify --evidence` mode with the required test entry points

## 4. Verification

- [ ] 4.1 Run the focused Evennia package tests: `world.rules.tests.test_combat_session`,
      `world.rules.tests.test_guild_exams`, `world.rules.tests.test_guild_economy_guards`, and the
      web adapters that read through `read_session` (`web.webclient.actions.tests.test_combat_actions`,
      `web.webclient.actions.tests.test_combat_dispatcher`)
- [ ] 4.2 Run `uv run --locked python -m tools.spec_traceability check`,
      `openspec validate fix-malformed-combat-recovery --strict`,
      `uv run --locked python -m compileall -q world typeclasses commands server`, and
      `git diff --check`
