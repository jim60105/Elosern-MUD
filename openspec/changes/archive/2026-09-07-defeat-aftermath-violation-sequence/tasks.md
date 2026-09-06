# Tasks: defeat-aftermath-violation-sequence

## 1. Rulebook extension

- [x] 1.1 Extend `world/rules/rulebook/defeat_aftermath.yaml` with the archetype section: per archetype `victory_pleasure_delta`, `threshold_ordinal`, `attempt_cap`, `attempt_duration_seconds`, `landed_deltas`, `resisted_deltas`, `credited_counters`; register this section's validator with the core's per-section loader; validate archetype keys against `world/lore/monsters.py` registries (fail closed); reject any `shame` key
- [x] 1.2 Author the v1 monster rows (goblin / slime / beast / wolf / ogre at minimum), values from the parent design's flavor notes — the archetype keys ARE the lore species names (MONSTER_TIER_REGISTRY `example_monsters_zh`: the durable identity a population monster carries as its key), so all twelve species rows ship and the five named monsters resolve through their species keys

## 2. State-derived dice helper

- [x] 2.1 Create `world/rules/state_derived_roll.py`: pure `derived_roll(session_id, violator_key, victim_key, attempt_index, purpose) -> int` (d100 range, no state); unit-test determinism, key sensitivity, and range/distribution bounds. No edit to `world/rules/action.py` — `resist_verdict` (`world/rules/sexual_resist.py`) is called as-is with the derived roll injected through its `rng` parameter

## 3. Violation sequence engine

- [x] 3.1 `world/rules/defeat_aftermath.py`: `run_violation_sequence(...)` REGISTERED as the core change's guarded-hook body (no settings read in this change); runs between `defeat_settle` and `violator_depart` — the hook seam carries a `ViolationHookContext` (actor/session/battlefield/entry sink/undo registry) and the engine registers at import (D-V6)
- [x] 3.2 Victory arousal: pleasure-point deltas through the existing pleasure path (clamped), carrying mid-fight accumulation
- [x] 3.3 Threshold gate + attempt loop over the player-only pool (v1): derived target/resist rolls; `resist_verdict(monster, player, rng=derived)`; landed/resisted delta application through the existing sexual-state write path; symmetric counter credits per the shared convention; per-attempt `advance_world_clock(source="defeat_aftermath")` for the declared duration — attempt advances run an empty entity scope (pure world-time passage), so the victim cannot regenerate past the recovery wake target mid-sequence
- [x] 3.4 First-resistance stop per violator; zero-landed ⇒ PG wake template
- [x] 3.5 Return the in-memory `ViolationOutcome` (selected/landed/resisted/climax_delta/zero_landed) to the settlement call graph; no persistence — `climax_delta` counts climax onsets (one per `violation_act` entry that pushed the victim into 進行中)
- [x] 3.6 EventLog `violation_attempt` / `violation_resisted` / `violation_act` entries in sequence order with their zh-tw template lines in `player_messages.py`; `log_warn` facade event for a missing archetype row

## 4. Tests (new module registered in `.github/evennia-shards.json` same change)

- [x] 4.1 `world/rules/tests/test_defeat_aftermath_violation.py`: threshold gate on/off, cap respected on all-landed runs, carry-over from mid-fight sexual casts, pleasure clamp, landed vs resisted deltas, symmetric counters, per-attempt clock sum == N×D, first-resistance stop, zero-landed PG equivalence, companion untouched under the player-only pool, digest-outcome counts equal EventLog counts
- [x] 4.2 Rollback-replay test: inject a failure after attempt 1, roll back, retry via the recovery fallback, assert the second run's rolls/targets/deltas are identical (state-derived property)
- [x] 4.3 Flag-off equivalence: same defeat with `DEFEAT_ADULT_SCENES` false equals the core-only settlement exactly
- [x] 4.4 Assert existing `test_sexual_state.py` monster-baseline tests stay green unmodified
- [x] 4.5 `covers_requirement` annotations for every added requirement; `uv run --locked python -m tools.spec_traceability check` green — annotations ship with the canonical slugs; the check reports the new capability's nine IDs as unknown until the archive workflow syncs the delta spec into `openspec/specs/` (the DA2 precedent; archive is owner-gated)
- [x] 4.6 Focused run green: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_defeat_aftermath_violation world.rules.tests.test_defeat_aftermath_core world.rules.tests.test_sexual_state`; `tools.observability_lint check`; `git diff --check` clean
