## ADDED Requirements

### Requirement: Buff application has one public entry point carrying both grant-time guards
`world/rules/buffs.py` SHALL expose a public buff-application function taking an entity, a buff
definition key, an optional instance key, and arbitrary cache data. Every deterministic caller that
applies a buff SHALL use it rather than calling `BuffHandler.add()` directly, because two grant-time
guards live in it and nowhere else: (1) a debuff whose definition key is immunized by the target's
worn equipment SHALL NOT be written at all, and (2) a definition declaring
`stacking: unique_per_source` SHALL raise when no `source_key` is supplied. Neither guard SHALL be
weakened or made optional for any caller.

#### Scenario: An immunized debuff is refused, not half-applied
- **WHEN** the public entry point is called with a debuff-polarity key the target's worn equipment
  immunizes against
- **THEN** no buff is written and the target's active buff set is unchanged

#### Scenario: A unique_per_source buff without a source key raises
- **WHEN** the public entry point is called for a definition declaring
  `stacking: unique_per_source` with no `source_key` in the supplied data
- **THEN** it raises rather than writing an unattributable instance

#### Scenario: A caller outside the buffs module applies a buff through the entry point
- **WHEN** a deterministic module other than `world/rules/buffs.py` applies a buff
- **THEN** it does so through the public entry point, and no module outside `world/rules/buffs.py`
  calls `entity.buffs.add(...)` directly
