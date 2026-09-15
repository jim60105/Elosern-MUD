## REMOVED Requirements

### Requirement: SKILL_REGISTRY contains the full 暗-element spell set
**Reason**: The old requirement mandates a duplicated ten-row data contract (the 2026-08-12 dev-era set — no prerequisites, no coefficients, a non-locking fear marker, and erosion ticks whose HP is never recovered). The ratified wave NON-GOAL rules out dark catalog/data-contract tests: no key-set equality, no row mirroring, no MP-cost/cap/tier table assertions, no echo of the skill-tree table.
**Migration**: Delete the dark catalog echo table and its test class in `world/skills/tests/test_spell_catalogs.py`, the dark rows in the tier-correspondence table, and the obsolete traceability/freeze entries during the separately authorized main-sync. Replace this requirement with the behavioral curse/erosion-progression requirement below, backed by synthetic behavior tests and one disposable real-engine scenario. The dev-era registry rows are deleted wholesale without an alias (zero users); re-homed buff keys carry the tree's authored numbers with no aliasing. No saved-data migration is introduced.

## ADDED Requirements

### Requirement: Dark spell progression composes executable curse and erosion behavior
The dark spell family SHALL provide the documented two-root curse/erosion progression as executable skill behavior using the common effect, audience, policy, buff, modifier and reaction mechanisms: stat-debuff ladders on authored axes and durations, a psychological action lock on one buffs key independent of any physical-stillness key, damage-bearing erosion DoTs whose every actual tick loss is transferred in full to the grant-time origin caster and extinguished with either party's death, an execution rung that ignores defense, a devastation area rung, cast-time self-recovery keyed to a declared fraction of the caster's own missing HP, and a two-parent capstone stacking damage, devastation, a wide stat debuff and self-recovery as independent effect components. Branch and merge prerequisites SHALL gate use through the shared lineage engine independently of ownership, with prerequisite caps derived from the reverse-edge map (leaf cap unchanged).

#### Scenario: The curse ladder weakens observable stats at settlement
- **WHEN** synthetic dark debuff compositions mirroring the authored axes and durations resolve through ordinary action settlement and the clock advances
- **THEN** the victims' effective stats drop by the authored amounts for the authored durations and recover on expiry, and the feared victim's next turn is skipped by the shared action-lock consumer until the marker ends — while a physically-stilled victim's distinct key is untouched by the fear key and vice versa

#### Scenario: Erosion transfers its whole loss to the origin caster
- **WHEN** a synthetic damage-plus-erosion composition ticks a victim over several intervals, including one area composition with per-victim origins and one interval where the caster is dead or the victim reaches its HP floor
- **THEN** each living origin caster gains exactly the HP each of their victims actually lost, no credit flows after either party's death or the buff's expiry, and the victim's single loss dispatch and the round's death settlement are unchanged

#### Scenario: Recovery rides the caster's own missing HP, never the victim's
- **WHEN** a synthetic damage-plus-missing-fraction-self-recovery composition resolves from a wounded caster against a fuller enemy
- **THEN** the caster recovers exactly the authored fraction of their own missing HP clamped at their maximum, the enemy's HP state never enters the amount, and a dead caster revives nothing

#### Scenario: Execution and devastation rungs behave through the shared policies
- **WHEN** synthetic execution-rung and devastation-rung dark compositions hit a high-defense target and a mixed area
- **THEN** the execution rung ignores defense subtraction while the ordinary rung does not, and the devastation rung adds its authored maximum-HP fraction on hit through the existing rider with no dark-specific code

#### Scenario: Two roots, branch, and convergence gate through the lineage engine
- **WHEN** a synthetic family replicates the documented branching and the two-parent capstone prerequisite shape
- **THEN** use rejects until every authored threshold is met, capstone attainment follows both terminal branches, and prerequisite caps stay derived from the shared reverse-edge map

#### Scenario: Retired dev-era bindings resolve as ordinary rejections
- **WHEN** a caller references a deleted dev-era buff binding or casts a never-existing key through the ordinary cast surface after replacement
- **THEN** it rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on
