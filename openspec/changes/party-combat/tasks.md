# party-combat Tasks

> **Precondition**: `party-core` and `party-follow` MUST be implemented, verified, and archived
> before this change starts; task 1.1 calls their `world/rules/party.py` APIs and must not
> reimplement membership.

## 1. Allied engagement

- [ ] 1.1 Use `world/rules/party.py`'s safe companion-resolution API to collect the player's
      bound, co-located, living, non-knocked-out companions.
- [ ] 1.2 Extend `engage` in `world/rules/combat_session.py`: include those companions in
      `player_ids` (player first, then companions in deterministic party order); keep all existing
      validation (PlayerCharacter, no active session, living hostile Monster in the same room).
- [ ] 1.3 Build the per-entity nonlethal context: `_context_for` sets `nonlethal_keys` to the
      companion keys in hostile sessions; the exam mode keeps the session-wide flag unchanged.
- [ ] 1.4 Add integration tests: co-located living companions join the allied team; distant, dead,
      or knocked-out companions do not; an empty-party engage behaves exactly as before.

## 2. Knockout as battlefield state

- [ ] 2.1 Add `knocked_out: set[str]` to `Battlefield` in `world/rules/combat.py` (beside `fled`),
      initialize it in `reconstruct_battlefield` from `record.knocked_out_ids`, and expose a
      shared `is_knocked_out(key)` predicate.
- [ ] 2.2 Extend `world/rules/action.py`'s battlefield-shaped snapshot/restore to cover `fled`
      AND `knocked_out` (duck-typed, no `Battlefield` import); extend the commit-rollback path
      accordingly.
- [ ] 2.3 Mark the knockout at damage-commit time: the per-entity nonlethal floor in
      `world/rules/combat.py` adds the target key to `battlefield.knocked_out` inside the same
      commit when the target is protected by `nonlethal_keys`.
- [ ] 2.4 Convert every alive-check consumer to the predicate: initiative order, the round and
      overwhelm providers, `_living_enemies` in `world/rules/monster_behaviour.py`, the
      `all-allies`/AREA target expansion, overwhelm classification, and `_team_living`.
- [ ] 2.5 Persist `knocked_out_ids` at round end as today (existing `_knocked_out_ids` backfill
      plus in-round markings).
- [ ] 2.6 Clear the marker only when HP rises above 1 via regen; make `engage` exclude
      knocked-out companions until then.
- [ ] 2.7 Add tests: a knocked-out companion receives no policy request, is excluded from
      `all-allies` and opposing-team targeting, is absent after a battlefield rebuild, cannot
      re-engage before recovery, and rejoins after regen above 1 HP; knockout is rolled back with
      the commit on failure.

## 3. Per-entity nonlethal projection

- [ ] 3.1 Update the knockout decision in `world/rules/action.py` (`_defeated_entry` / step-7
      builder): per-damaged-target `nonlethal = session_flag or target.key in nonlethal_keys`.
- [ ] 3.2 Update the HP-crossing floor in `world/rules/combat.py` to apply the nonlethal floor per
      damaged target under the same rule and to mark the battlefield knockout (2.3).
- [ ] 3.3 Add tests: a companion crossing to non-positive HP floors at 1, emits
      `target_knocked_out`, no `target_defeated`, and is marked knocked out in the same commit; a
      monster crossing in the same session stays lethal; exam sessions behave exactly as before
      (existing nonlethal tests stay green).

## 4. Player-centric terminal rules and cleanup

- [ ] 4.1 Rewrite `_terminal_outcome` in `world/rules/combat_session.py`: the player fled → fled;
      the player knocked out or at zero HP → defeat (hostile) / exam failure; foes team gone →
      victory / exam pass; otherwise continue or round cap.
- [ ] 4.2 Fix `clear_session` / forfeit / recovery cleanup to resolve every participant dbref from
      the persisted record so a failed reconstruction still unregisters surviving companions and
      monsters from skip safety.
- [ ] 4.3 Add tests: player defeated with companions standing settles as defeat end to end (no
      deadlock); victory requires only the foes team gone; a knocked-out companion does not end
      the session; a missing participant during cleanup does not leave other participants
      registered IN_COMBAT.

## 5. Verification

- [ ] 5.1 Run the touched test labels (`world.rules` combat/combat_session/monster_behaviour/
      action/party, `commands` combat, `web.webclient.actions` combat facade if affected) plus
      the existing combat golden tests and the action-resolver atomicity suite.
- [ ] 5.2 Run `uv run --locked python -m compileall -q world typeclasses commands server` and keep
      `git diff --check` clean.
- [ ] 5.3 Annotate substantive new tests with `covers_requirement` canonical IDs; run
      `openspec validate party-combat --strict` and
      `uv run --locked python -m tools.spec_traceability check`; before handoff run the required
      test entry points with the same `OPENSPEC_TEST_EVIDENCE` path and the verifier's
      `verify --evidence` mode.
