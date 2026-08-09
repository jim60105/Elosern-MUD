# affinity-friendly-fire — Tasks

## 1. Rulebook and source set

- [ ] 1.1 Add `friendly_fire_penalty_per_hit: 1` to `world/rules/rulebook/affinity.yaml` with a
      comment documenting the friendly-fire contract
- [ ] 1.2 Extend `world/rules/affinity_config.py` to load and validate
      `friendly_fire_penalty_per_hit` (positive integer, bounded), failing closed on deviation
- [ ] 1.3 Add `friendly_fire` to the closed `AffinitySource` set in `world/rules/affinity.py` and
      confirm `apply_affinity_change` handles it as a negative delta with no budget interaction

## 2. Combat-session damage scan

- [ ] 2.1 In `world/rules/combat_session.py`, after a resolved player action round, scan the
      round's damage events produced by that player action against ally-side participants,
      snapshotting qualifying companion membership when the scan starts
- [ ] 2.2 For each qualifying hit (target is an NPC in the snapshotted `player.db.party` set and
      present on the battlefield), call `apply_affinity_change(npc, player, FRIENDLY_FIRE, penalty)`
      with the rulebook value — one call per hit
- [ ] 2.3 Run the scan, all penalty writes, and any resulting auto-leave inside the round's
      transaction boundary; deliver the auto-leave notification after commit, never mid-transaction
- [ ] 2.4 Ensure non-player-action damage (companion-vs-companion, enemy behavior, buff ticks)
      never enters the scan, and non-companion targets (including recordless ones) trigger no write

## 3. Tests

- [ ] 3.1 Pure/unit tests: rulebook loading rejects missing/non-positive `friendly_fire_penalty_per_hit`;
      `friendly_fire` source accepted by the writer with no budget interaction
- [ ] 3.2 `EvenniaTest` combat tests: AREA skill hitting two companions applies two -1 penalties;
      self-selected single-target misfire penalizes; non-player-action damage never penalizes;
      non-companion target writes nothing; recordless non-companion gains no entry; a knockout hit
      (companion to 0 HP, nonlethal) still qualifies
- [ ] 3.3 Auto-leave integration tests: penalty dropping a companion below 70 ends the party with
      `affinity_below_threshold` and notification after commit; staying at/above 70 keeps the
      party; failed leave rolls back the penalty
- [ ] 3.4 Same-round snapshot tests: the first hit of an action triggers auto-leave and a later hit
      of the same action still penalizes; a companion that left in an earlier round no longer
      qualifies in a later round; a failure mid-round rolls back every penalty of that round
- [ ] 3.5 Regression: existing affinity, party, and combat-session suites stay green

## 4. Traceability and verification

- [ ] 4.1 Annotate the discoverable tests covering the new and modified requirements with
      `covers_requirement` using canonical IDs from
      `uv run --locked python -m tools.spec_traceability list`
- [ ] 4.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm the
      affinity-friendly-fire and affinity-system requirements are covered
- [ ] 4.3 Run the focused test packages (world rules tests) and confirm green
