## MODIFIED Requirements

### Requirement: Per-round upkeep ticks buffs and advances sexual decay by the round duration
`world/rules/combat.py`'s per-round upkeep SHALL call change 6's `tick_buffs(entity)` for every living roster member unconditionally and SHALL call change 7's `world.rules.sexual_state.decay_tick(entity, round_seconds)` with the configured round duration. The upkeep SHALL collect the damaging tick records `tick_buffs` returns, per roster member, and SHALL hand them to the round's upkeep settlement (`world/rules/upkeep.py`) so the round's EventLogs and staged effects include the settled tick damage, defeat crossings, kill XP, and quest effects. `run_round` SHALL accept keyword-only `simulated` and `nonlethal_keys` policy flags and SHALL forward them to the upkeep settlement.

#### Scenario: Buff ticks run every round with no self-arming guard
- **WHEN** a round completes with a poisoned combatant present
- **THEN** `tick_buffs()` is called for that combatant exactly once, unconditionally, with no try/except around the call

#### Scenario: Sexual decay accumulates exactly one round of elapsed time
- **WHEN** a round completes for a living roster member
- **THEN** `decay_tick` is called once for that entity with `COMBAT_YAML["round"]["seconds"]`

#### Scenario: Upkeep tick records reach the round settlement
- **WHEN** a round completes with a `fire_scorch`-afflicted living roster member whose tick fires
- **THEN** the round's EventLogs include the tick's `damage` entry and, on a lethal crossing, a single `target_defeated` entry, staged with the round's other effects

#### Scenario: Round policy flags reach the upkeep settlement
- **WHEN** `run_round` is called with `simulated=True` or with `nonlethal_keys` naming a roster member
- **THEN** upkeep defeat entries are tagged `simulated` with no kill credit, and protected members floor at 1 HP and are marked knocked out instead of defeated
