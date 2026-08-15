## MODIFIED Requirements

### Requirement: Per-round upkeep ticks buffs and advances sexual decay by the round duration
`world/rules/combat.py`'s per-round upkeep SHALL call change 6's `tick_buffs(entity)` for every living
roster member unconditionally and SHALL call change 7's
`world.rules.sexual_state.decay_tick(entity, round_seconds)` with the configured round duration.
Immediately after `decay_tick`, the upkeep SHALL call `world.rules.sexual_state.climax_settlement_
action(entity)` and, when it returns `"extend"` or `"end"`, SHALL emit the correspondingly named event
(`climax_extended` or `climax_ends`) through `world.rules.sexual_transitions.apply_event()`. The
upkeep SHALL collect the damaging tick records `tick_buffs` returns, per roster member, and SHALL
hand them to the round's upkeep settlement (`world/rules/upkeep.py`) so the round's EventLogs and
staged effects include the settled tick damage, defeat crossings, kill XP, and quest effects.
`run_round` SHALL accept keyword-only `simulated` and `nonlethal_keys` policy flags and SHALL forward
them to the upkeep settlement.

#### Scenario: Buff ticks run every round with no self-arming guard
- **WHEN** a round completes with a poisoned combatant present
- **THEN** `tick_buffs()` is called for that combatant exactly once, unconditionally, with no
  try/except around the call

#### Scenario: Sexual decay accumulates exactly one round of elapsed time
- **WHEN** a round completes for a living roster member
- **THEN** `decay_tick` is called once for that entity with
  `COMBAT_YAML["round"]["seconds"]`

#### Scenario: A roster member in 進行中 with no staged extension climaxes by the end of the round
- **WHEN** a round completes for a living roster member whose `climax_phase` is `進行中` and who has no
  staged climax extension
- **THEN** `climax_ends` fires for that entity during that round's upkeep, immediately after
  `decay_tick`, and `climax_phase` becomes `餘韻`

#### Scenario: A roster member in 進行中 with a staged extension remains locked for another round
- **WHEN** a round completes for a living roster member whose `climax_phase` is `進行中` and who has an
  extension staged via `stage_climax_extension()`
- **THEN** `climax_extended` fires for that entity during that round's upkeep instead of `climax_ends`,
  and `climax_phase` remains `進行中`

#### Scenario: Upkeep tick records reach the round settlement
- **WHEN** a round completes with a `fire_scorch`-afflicted living roster member whose tick fires
- **THEN** the round's EventLogs include the tick's `damage` entry and, on a lethal crossing, a single `target_defeated` entry, staged with the round's other effects

#### Scenario: Round policy flags reach the upkeep settlement
- **WHEN** `run_round` is called with `simulated=True` or with `nonlethal_keys` naming a roster member
- **THEN** upkeep defeat entries are tagged `simulated` with no kill credit, and protected members floor at 1 HP and are marked knocked out instead of defeated
