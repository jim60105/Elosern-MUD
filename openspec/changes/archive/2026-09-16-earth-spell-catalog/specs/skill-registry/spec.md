## REMOVED Requirements

### Requirement: SKILL_REGISTRY contains the full 土-element spell set
**Reason**: The old requirement mandates a duplicated dev-era ten-row data contract (the 2026-08-12 set — no prerequisites, no coefficients, an off-tree bind node, no terrain behavior). The ratified wave NON-GOAL rules out earth catalog/data-contract tests: no key-set equality, no row mirroring, no MP-cost/cap/tier table assertions, no echo of the skill-tree table.
**Migration**: Delete the earth catalog echo table and its test class in `world/skills/tests/test_spell_catalogs.py`, the earth rows in the tier-correspondence table in `world/skills/tests/test_cost_tiers.py`, and the obsolete traceability/freeze entries during the separately authorized main-sync. Replace this requirement with the behavioral terrain-and-guard progression requirement below, backed by synthetic behavior tests and one disposable real-engine scenario. The dev-era registry rows are deleted wholesale without an alias (zero users), including the bind node and its control row; re-homed buff keys carry the tree's authored numbers with no aliasing. No saved-data migration is introduced.

## ADDED Requirements

### Requirement: Earth spell progression composes executable terrain-and-guard behavior
The earth spell family SHALL provide the documented two-root 護甲/地形 progression as executable skill behavior using the common effect, audience, policy, buff, reaction, modifier and lineage mechanisms: a fixed-defense ladder on the defense axis at authored ceilings and durations, an accuracy debuff rung, ground-hazard marker rows whose standing-on-it fact is the live marker instance and whose damage ticks at the authored DoT rungs and durations, the ice slow-rung key reused as pure consumer data beside every fissure, a synergy strike priced once on a standing-on-the-marker target while ignoring defense unconditionally for every target, devastation area rungs, an on-physical-hit counter settlement at the authored coefficient mounted by a detectable self-buff and silent against magic attackers, and a two-parent capstone stacking damage, devastation, the top-rung full-field marker and the slow rung as independent effect components — with the retired bind node's 束縛 verb staying exclusively ice's.

#### Scenario: The defense ladder guards observable stats at settlement
- **WHEN** synthetic earth self-cast and ally-area defense compositions mirroring the authored ceilings and durations resolve through ordinary action settlement and the clock advances
- **THEN** each guardian's effective defense rises by exactly the authored amount for the authored duration, ally-area casts spare enemies, and defense recovers on expiry

#### Scenario: Fissure hazards burn whoever keeps standing on them
- **WHEN** a synthetic area composition applies a marker hazard plus the reused slow rung to a victim and the clock ticks past several intervals, then the victim flees the battlefield mid-duration and separately the hazard expires while its holder stays fighting
- **THEN** the standing victim loses exactly the authored per-interval DoT and carries the authored agility debuff, the hazard stops ticking the moment the holder leaves the battlefield while a non-marker buff of the holder persists unchanged, and expiry ends both the ticking and the standing-on-it fact

#### Scenario: The synergy strike prices the marker once and bypasses defense always
- **WHEN** a synthetic execution composition declaring the marker-fact predicate, a conditional multiplier and the unconditional bypass strikes the same high-defense target while standing on a fissure and while not, plus a target standing on a parallel-duration fissure rung
- **THEN** both marker rungs receive the same single multiplier application with defense ignored, the off-marker strike still ignores defense at base coefficient without the multiplier, and no strike receives the multiplier twice

#### Scenario: The carapace returns physical pain and ignores everything else
- **WHEN** a synthetic self-buff carrier of the counter rule is struck by a landed physical attack, a magic attack, a missed swing, and a damaging tick
- **THEN** only the physical attacker takes the holder's effective attack times the authored coefficient minus its defense exactly once, the attacker's own counter rule does not chain, and the tick and magic paths move no HP back to any attacker

#### Scenario: Devastation and execution rungs behave through the shared policies
- **WHEN** synthetic devastation and execution earth compositions hit a mixed area and a high-defense single target
- **THEN** the devastation rung adds its authored maximum-HP fraction on hit through the existing rider and the execution rung ignores defense subtraction, with no earth-specific code

#### Scenario: Two roots, branches, and the two-parent capstone gate through the lineage engine
- **WHEN** a synthetic family replicates the documented two-root branching, both branch points, and the two-parent capstone prerequisite shape
- **THEN** use rejects until every authored threshold is met, capstone attainment follows both terminal branches, and prerequisite caps stay derived from the shared reverse-edge map

#### Scenario: Retired dev-era bindings resolve as ordinary rejections
- **WHEN** a caller references the deleted bind node or its control binding, or casts a never-existing key through the ordinary cast surface after replacement
- **THEN** it rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on
