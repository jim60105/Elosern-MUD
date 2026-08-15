## Why

A non-Monster NPC companion can legally own and afford an elemental damage spell whose tier gate it does not meet; the generic `default_attack_policy` picks that spell every round, `ActionResolver` rejects it with `UNKNOWN_SKILL`, and `run_round` silently discards the rejected result — the companion repeats the same invalid choice every turn instead of falling back to its innate `basic_attack`, wasting every turn (security-audit finding, run-3 index 0, severity medium).

## What Changes

- Introduce one public, side-effect-free cast-eligibility predicate in `world/rules/progression.py` (the deterministic core) that composes the existing `spell_tier_for` (`world/skills/cost_tiers.py`) and `can_cast_spell_tier` checks with fail-closed `ValueError` handling — the single authoritative spell-tier gate shared by `ActionResolver`, the Monster behaviour policy, and the generic NPC attack policy.
- `ActionResolver._step1_ownership` consumes the shared predicate instead of its inline duplicate of the tier-gate block.
- `world/rules/monster_behaviour.py` drops its private `_gate_allows` and filters candidates through the shared predicate (behavior-preserving; this is the same gate it already applies).
- `world/rules/combat.py::default_attack_policy` applies the shared predicate to its candidate scan, so a tier-blocked spell is skipped and the scan falls back to the next legal damage skill — the innate `basic_attack` in practice — producing resolver-ready requests for NPC companions (the actual fix).
- Behavior tests for the predicate, the generic-policy fallback, and a `run_round` integration case proving the companion acts every round instead of silently losing turns.
- No change to `run_round`'s rejection handling, import schemas, or preview/revalidation code (the parallel change `fix-combat-preview-tier-gate` owns that wiring and depends on the shared predicate introduced here).

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `element-mastery`: adds the shared `can_cast_skill` predicate requirement — the single consumer-facing spell-tier eligibility query.
- `monster-action-policy`: adds the requirement that a non-Monster entity delegated to `default_attack_policy` is never proposed a tier-blocked elemental spell (falls back to the next legal owned damage skill).

## Impact

- `world/rules/progression.py` (new public predicate), `world/rules/action.py` (resolver gate adoption), `world/rules/monster_behaviour.py` (gate adoption), `world/rules/combat.py` (generic policy candidate gating).
- Tests: `world/rules/tests/test_progression.py` (predicate unit tests), `world/rules/tests/test_action_pipeline_rejections.py` (resolver parity stays green), `world/rules/tests/test_monster_behaviour_policy.py` (patch-target update for the shared helper), new generic-policy and `run_round` fallback tests.
- Coordination: this change owns the shared predicate; `fix-combat-preview-tier-gate` (parallel proposal) depends on it and will wire `world/rules/action_preview.py` preview and submission revalidation to the same predicate. No preview wiring is designed or implemented here.
- No data migration or backward-compatibility work (project has no released users). No schema, command-surface, or player-facing documentation change.
