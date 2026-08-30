# combat-upkeep-settlement Specification

## Purpose
The deterministic boundary that turns damaging rate ticks into attributed defeat events, kill XP, and
quest effects inside the combat-round transaction (fix-dot-kill-credit).

## Requirements
### Requirement: Damaging rate ticks settle through a deterministic event-producing boundary within the combat round
`world/rules/upkeep.py` SHALL provide an upkeep settlement that consumes the damaging tick records `tick_buffs` returns and turns them into round events and staged effects. For each record in application order, the settlement SHALL emit a `damage` EventLog entry reporting the actual applied amount (the delta clamped by the target's pre-tick HP, matching the action path's gauge clamp) and, when the record's pre-tick HP was positive and its delta crosses to zero or below, exactly one `target_defeated` crossing entry per target (deduplicated by dbref), with the same entry shape as the action pipeline's defeat entries: `data["target_id"]` as int dbref, `data["monster_tier"]` as `threat_tier` when present, and a boolean `data["simulated"]` tag when the round is simulated. The settlement SHALL stage the nonlethal floors, knockout marks, and quest planner effects as `PendingEffect` values committed within the session's combat-round transaction, and SHALL append the upkeep EventLogs to the round's logs so the session's friendly-fire scan evaluates them like any action damage entry.

#### Scenario: A lethal rate tick on the last living foe emits the defeat entry and the round settles as victory
- **WHEN** combat upkeep fires a damaging tick that reduces the final living foe from positive HP to zero
- **THEN** the round's EventLogs contain a `damage` entry and a single `target_defeated` entry naming that foe, and the session's terminal outcome is victory

#### Scenario: Multiple damaging DoTs in one tick emit exactly one defeat entry
- **WHEN** `poisoned` and `fire_scorch` both fire in the same upkeep tick and the first tick is the lethal one
- **THEN** the round contains one `target_defeated` entry for the target, credited to the lethal tick's source, and the later tick adds only a `damage` entry

#### Scenario: A tick on a nearly dead target reports the applied amount
- **WHEN** a -5 tick lands on a living target at 2 HP
- **THEN** the `damage` entry reports `amount == 2` (the HP actually removed, clamped at zero) and the target's HP is 0

#### Scenario: A target the applying action already killed never settles twice
- **WHEN** a buff-applying action already reduced the target to zero HP in the same or an earlier round
- **THEN** upkeep skips the non-living target, no additional defeat entry or quest effect is produced, and the round's defeat entries remain exactly the action's

### Requirement: Upkeep kill credit requires validated, resolvable source identity
The upkeep settlement SHALL attribute a lethal rate tick to the entity whose dbref the buff cache stores as `source_pk`, resolved against the battlefield roster or the object database. An attributed lethal tick SHALL stage the same EventLog and quest-effect consumers as an action-pipeline defeat, credited to the resolved source in the same round commit; a tick with no cached `source_pk`, an unresolvable (deleted or absent) source, a non-Monster target, or a target outside the tier registry SHALL grant no credit at all. The upkeep settlement SHALL NOT write any progression state for any tick. An unattributed lethal tick SHALL still apply its HP damage but SHALL emit no EventLog entries and stage no quest effects.

#### Scenario: An attributed lethal tick on a tiered monster credits the caster's defeat entry once
- **WHEN** the player's `fire_scorch` tick causes the lethal HP crossing of a `Monster` with `threat_tier == "low"` during combat upkeep
- **THEN** the defeat entry names the player as source, carries `monster_tier == "low"`, and commits exactly once with that round, with no progression award

#### Scenario: A deleted or absent source grants no credit
- **WHEN** a lethal rate tick's cached `source_pk` resolves to no entity (or is absent from the buff cache)
- **THEN** the target's HP still crosses, but no EventLog entries or quest effects are produced

#### Scenario: A non-Monster target grants no monster-tier credit
- **WHEN** an attributed lethal tick kills an NPC or companion rather than a `Monster`
- **THEN** the defeat entry carries no `monster_tier` and no tier-derived credit is staged

### Requirement: Upkeep settlement honors simulated and nonlethal combat policy
`run_round` SHALL accept keyword-only `simulated` and `nonlethal_keys` policy flags and SHALL forward them to the upkeep settlement. In a simulated round (guild examination) the settlement SHALL tag every upkeep `target_defeated` entry `simulated=True`. For a target whose key is in `nonlethal_keys` (an allied companion), an upkeep lethal crossing SHALL floor the target at 1 HP, mark the target knocked out on the battlefield, and emit a `target_knocked_out` entry (the same shape the action path emits for a nonlethal crossing) instead of a `target_defeated` entry, with no kill credit.

#### Scenario: A guild-examination tick kill grants no credit
- **WHEN** a damaging tick lethally crosses the examiner inside a simulated (guild-exam) round
- **THEN** the defeat entry carries `simulated=True`, and no quest DEFEAT progress or protected-entity failure results

#### Scenario: An upkeep tick on a protected companion floors and marks knocked out
- **WHEN** a damaging tick would cross an allied companion named in `nonlethal_keys`
- **THEN** the companion's HP is set to 1, the companion is marked knocked out on the battlefield, a `target_knocked_out` entry is emitted, and no `target_defeated` entry or kill credit is produced

### Requirement: Upkeep tick damage outside combat rounds produces no events or credit
Callers of `tick_buffs` outside the combat-round settlement (the world-clock settlement path) SHALL ignore the returned tick records: the records SHALL cause no EventLog entries and no quest effects on their own.

#### Scenario: A clock-driven tick changes HP only
- **WHEN** the world-clock settlement invokes `tick_buffs` for an entity with an active damaging buff and discards the return value
- **THEN** the entity's HP changes by the rate delta and no event log, quest log, or progression attribute changes as a result
