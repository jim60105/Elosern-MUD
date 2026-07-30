## Why

Design doc §11 roadmap item #9 depends on change 8 (`action-resolver`), which built the eight-step
resolution pipeline, `EventLog`, the effect-handler registry, and the `ActionContext` protocol — but
deliberately left every `damage:*`-prefixed effect ID rejecting with `UNKNOWN_EFFECT_ID`, declared
`BattlefieldActionContext` as an unimplemented protocol-conformance target, and named this change as
the owner of a real `is_in_range()`. Without this change, no skill whose `effects` list contains a
`damage:*` ID can ever resolve, no combatant roster or turn order exists, and §6.3's to-hit/damage
formulas are un-implemented prose.

This change is also a correction. Design doc §6.3 fixes the to-hit formula's defender threshold at a
literal `60`, chosen when the author (incorrectly) believed human physical stats sat in the 60-90
range. Changes 2 and 3 have since established the real bands — human 1-22 (elite 7-14, e.g. 8/9/7),
elf 70-95 — so `60 + defender agility` is no longer the number it was designed against. Because
`rulebook/combat.yaml` is this change's own file to own, this change is also where that constant gets
re-derived against the real numbers rather than carried forward unexamined.

## What Changes

- Add `world/rules/dice.py`: a thin wrapper over `evennia.contrib.rpg.dice.roll()` for the d100 roller
  design doc §4 confirms is usable directly.
- Add `world/rules/combat.py`: `Battlefield`, `BattlefieldActionContext` (satisfying change 8's
  `ActionContext` protocol), initiative ordering, the turn loop, `effective_power()`, and the to-hit /
  damage resolution that calls `ActionResolver.resolve()` (change 8) for every combatant action.
- Add `world/rules/rulebook/combat.yaml`: the recalibrated to-hit constant, the damage roll-multiplier
  bands, and initiative tuning — all as tunable data, not hardcoded Python, per D9's "balance numbers
  are data" split.
- Register `damage:*` effect handlers into change 8's `_EFFECT_HANDLERS` registry via
  `register_effect_handler()`, declaring `surfaces=frozenset({"traits"})` — the first real occupant of
  the extension point change 8 declared and refused to guess at.
- Implement `is_in_range()` for `BattlefieldActionContext` to the extent a coordinate-free battlefield
  model allows (engaged/not-engaged, melee-vs-ranged), explicitly deferring true positional range to
  change 12 (`map-anchor-grid`).
- Extend change 8's pending-effect event conversion with the `"roll"` and `"damage"` records required
  for combat, and correct its battlefield shorthand expansion to read entity values from the roster
  mapping.
- Report `rounds × 6 seconds` as a plain integer to whatever calls the turn loop; this change never
  calls `WorldClock.advance()` (change 11 remains a later roadmap item).
- Recalibrate and document the to-hit formula's defender-side constant in `rulebook/combat.yaml`,
  replacing the stale `60` with a value re-derived against changes 2/3's real stat bands, with the
  reasoning recorded where a future balance pass can find it.

## Capabilities

### New Capabilities
- `dice-roller`: the d100 roller wrapper (`world/rules/dice.py`), fixed-seed determinism for
  reproducible rolls.
- `combat-resolution`: initiative ordering, the turn loop, `effective_power()`, the recalibrated
  to-hit and damage formulas (`world/rules/combat.py` + `rulebook/combat.yaml`), and the round-based
  time-cost report.
- `battlefield-action-context`: `Battlefield`/`BattlefieldActionContext` conforming to change 8's
  `ActionContext` protocol, combat-shortcut roster support, and `is_in_range()`'s battlefield-level
  implementation.
- `damage-effect-handlers`: the `damage:*` prefix registered into change 8's effect-handler registry,
  reading skill multipliers exclusively through change 5's `SkillHandler.effective_value()` and combat
  modifiers exclusively through change 6's `evaluate_combat_modifiers()`.

### Modified Capabilities
- `action-resolution-pipeline`: damage pending effects are converted into structured roll/damage
  entries by the existing step-7 event-log builder.
- `targeting-validation`: battlefield shorthand expansion reads live entity values from the
  battlefield roster mapping before applying the unchanged validation pipeline.

## Impact

- **New files**: `world/rules/dice.py`, `world/rules/combat.py`, `world/rules/rulebook/combat.yaml`,
  `world/rules/tests/` (new test modules for this change's scope).
- **Modified files**: `world/rules/action.py` (combat event conversion only) and
  `world/rules/targeting.py` (roster mapping values for shorthand expansion). The resolver pipeline,
  validator ordering, and public effect registration seam remain unchanged.
- **Depends on**: change 8 (`action-resolver`) for `ActionResolver.resolve()`, `ActionContext`,
  `register_effect_handler()`, `PendingEffect`, `SNAPSHOTTED_SURFACES`; change 5
  (`skills-equipment`) for `SkillHandler.effective_value()`; change 6 (`buffs-rulebook`) for
  `evaluate_combat_modifiers()`; change 2 (`lore-world-data`) for `RaceProfile.static_baseline` and
  `STATIC_TIER_REGISTRY`/`MonsterTier` as calibration reference points.
- **Consumers deferred to later changes**: change 10 (`overwhelm-resolution`) is expected to call this
  change's `effective_power()` for its own threshold check and to compress the `EventLog`s this
  change's turn loop produces; change 11 (`world-clock`) is expected to read the round-count time
  report and decide how to advance; change 12 (`map-anchor-grid`) is expected to supply the
  coordinates that let `is_in_range()` become a real positional check.
