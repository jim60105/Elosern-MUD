# party-quest Tasks

> **Precondition**: `party-core`, `party-follow`, and `party-combat` MUST be implemented,
> verified, and archived before this change starts; it reads their APIs (binding, safe party
> reads, knockout predicate).

## 1. Companion DEFEAT credit

- [x] 1.1 Extend the quest event-effect planner (in `world/quests/planner.py` or the module
      owning `quest_event_effect_planner`) with the companion rule, evaluated pre-commit with the
      request context in hand: the request actor is a bound companion of a quest owner — validated
      bidirectionally through `world/rules/party.py`'s safe resolver (actor in the owner's valid
      party list AND back-reference pointing to the owner) — and is not knocked out per
      `Battlefield.is_knocked_out(str(actor.key))` on the request context's battlefield; a credit
      decision without an active battlefield or without a valid bidirectional binding fails closed.
- [x] 1.2 Plan the owner's matching active DEFEAT stage with the existing aggregation, cap, and
      one-transition semantics; the same commit that stages the lethal damage carries the quest
      mutation.
- [x] 1.3 Add integration tests: a bound companion's kill advances the owner's objective; a
      knocked-out companion's kill grants no credit; an unbound NPC's kill grants no credit; a
      backref mismatch (NPC claims the owner but is absent from the owner's party) grants no
      credit; no-battlefield credit requests fail closed; AREA aggregation and one-transition
      rules hold for companion-sourced entries.

## 2. Companion co-presence for arrival objectives

- [x] 2.1 Extend `observe_room_entry` in `world/quests/room_observation.py` with a co-presence
      read: the destination room contains at least one bound companion of the arriving player
      (safe party read). Arrival advances only when the player is the arriving object AND a bound
      companion is present; no companion-alone entry point is added.
- [x] 2.2 In `world/rules/party.py`'s follow flow, after the companions' moves complete, re-run
      the quest arrival observation for the player (via `world/quests/room_observation.py`), so
      first-arrival co-presence is visible; the one-transition rule keeps the repeated observation
      idempotent.
- [x] 2.3 Keep ESCORT's protected-entity alive-and-present gate and the wilderness
      no-observation behavior unchanged.
- [x] 2.4 Add tests through real exit traversal: a player arriving with companions advances a
      matching REACH/ESCORT stage exactly once (with and without the post-follow re-run); the
      repeated observation never advances a stage twice; an ESCORT with a missing/dead protected
      entity stays unchanged; wilderness traversal still produces no arrival observation.

## 3. Turn-in affinity bonus

- [x] 3.1 In `world/rules/guild.py::turn_in_quest()`, precompute the then-in-party companion list
      through the safe party read from `world/rules/party.py` and call
      `apply_affinity_change(npc, player, "quest_completion", 2)` per companion inside the reward
      transaction.
- [x] 3.2 Extend the reward snapshot/restore with a per-NPC map: snapshot every affected
      companion's `relations_data` attribute (and the relation-handler cache the affinity API
      relies on) before any write; on failure restore each NPC's attribute and rebuild/invalidate
      its relation cache so in-process affinity never diverges from the rolled-back database.
- [x] 3.3 Add tests in `world.rules.tests.test_guild_rewards`: turn-in with two in-party
      companions grants +2 each alongside the ordinary surfaces; a companion outside the party
      gains nothing; the bonus bypasses the daily cap; a fault at every affinity and reward write
      position restores wallet/inventory/merit/quest log/claims and every companion's affinity
      record and cache.

## 4. Verification

- [x] 4.1 Run the touched test labels: `world.quests.tests.test_planner` and the room/exit
      traversal tests, `world.rules.tests.test_guild_rewards`, `world.rules` party/affinity, and
      the quest reward and progress integration suites.
- [x] 4.2 Run `uv run --locked python -m compileall -q world typeclasses commands server` and keep
      `git diff --check` clean.
- [x] 4.3 Annotate substantive new tests with `covers_requirement` canonical IDs; run
      `openspec validate party-quest --strict` and
      `uv run --locked python -m tools.spec_traceability check`; before handoff run the required
      test entry points with the same `OPENSPEC_TEST_EVIDENCE` path and the verifier's
      `verify --evidence` mode.
