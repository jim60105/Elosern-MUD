## REMOVED Requirements

### Requirement: SKILL_REGISTRY contains the full 火-element spell set
**Reason**: The old requirement mandates a duplicated dev-era ten-row data contract (the 2026-08-12 set — no prerequisites beyond a partial chain, no coefficients, an off-tree `self_heal` healing clause on the 燃身 cost node, no ignite/lava/capstone behavior). The ratified wave NON-GOAL rules out fire catalog/data-contract tests: no key-set equality, no row mirroring, no MP-cost/cap/tier table assertions, no echo of the skill-tree table.
**Migration**: Delete the fire catalog echo table and its echo methods in `world/skills/tests/test_spell_catalogs.py` (the builder-shape MECHANIC test relocates beside the remaining builder users; the bare-`self_heal`-prefix parse test already lives in the parse-dispatch class and is untouched; the sibling `FireLineageTreeCatalogTests` — the skill-lineage capability's shipped-content contract — updates in place to the authored twelve-edge tree per this change's skill-lineage delta), the fire tier-label echo in `world/skills/tests/test_cost_tiers.py`, and the obsolete traceability/freeze entries during the separately authorized main-sync. Replace this requirement with the behavioral burn-and-immolation progression requirement below, backed by synthetic behavior tests and one disposable real-engine scenario. The dev-era registry rows are deleted wholesale without an alias (zero users), including the off-tree `self_heal` clause on the immolation node (治療 is light's exclusive verb); the re-homed burn key carries the tree's authored number with no aliasing. No saved-data migration is introduced.

## ADDED Requirements

### Requirement: Fire spell progression composes executable burn-and-immolation behavior
The fire spell family SHALL provide the documented HP・消滅 progression as executable skill behavior using the common effect, audience, policy, buff, reaction and lineage mechanisms: burn damage-over-time rows on the hp axis at the authored rungs and durations with the reused family key re-homed without alias, an on-physical-hit ignition of the attacker mounted by a detectable self-only armor buff through the shared outcome-reaction vocabulary (an ignition applied to the strike's source with grant-time attribution, never a reflected damage counter), a ground-lava marker hazard whose standing-on-it fact is the live marker instance and whose damage ticks at the authored DoT rung with the shared battlefield-exit extinguishment, a 處決級 execution rung that ignores defense subtraction through the shared damage policy, immolation cast costs priced as authored static coefficients beside a self-burn row that lands as an independent effect component regardless of the damage leg, and a three-way branch-point lineage whose two-parent 神格 capstone gates through the shared lineage engine with prerequisite caps derived from the shared reverse-edge map. No fire-specific behavior code SHALL exist: every clause above is data over the shipped event, marker, policy and lineage vocabularies.

#### Scenario: The burn ladder scorches at the authored rung and expires
- **WHEN** a synthetic single-target fire composition dealing its authored coefficient plus the family burn row resolves through ordinary action settlement and the clock advances past several tick intervals and then past expiry
- **THEN** the victim loses exactly the authored per-interval burn amount each interval for exactly the authored duration alongside the landed damage, the burned fact is true for every interval and false after expiry, and no other entity changes

#### Scenario: The burning armor ignites physical attackers and nothing else
- **WHEN** a synthetic self-only armor carrier is struck by a landed physical attack from a living attacker, then by a magic attack, a missed swing, a damaging tick, and a sourceless write, and separately by a physical attacker immune to the ignition and by one already carrying it
- **THEN** only the qualifying physical attacker holds the live authored ignition instance with grant-time attribution to the armor holder refreshed once per qualifying strike, the ignition ticks the attacker's hp at its authored rung while it lasts, the magic/miss/tick/sourceless paths and the immune attacker apply nothing, no damage ever moves back to any attacker, the attacker's own ignition never spawns a second event, and the ignition never disappears with the armor — it lives on the attacker's own clock

#### Scenario: The lava hazard burns whoever keeps standing on it and steps off when they leave
- **WHEN** a synthetic area fire composition applies the authored lava marker to a victim and the clock ticks past several intervals, then the victim flees the battlefield mid-duration, and separately the hazard expires while its holder stays fighting
- **THEN** the standing victim loses exactly the authored per-interval DoT each interval, the standing-on-it fact is true for every interval, the hazard stops ticking the moment the holder leaves the battlefield while the holder's non-marker buffs persist unchanged, and expiry ends both the ticking and the standing-on-it fact

#### Scenario: The execution rung ignores defense and the immolation costs are paid on cast
- **WHEN** a synthetic 處決級 composition strikes a high-defense target, and separately an immolation composition with its authored overflow coefficient and its self-burn cost component resolves with and without the damage leg landing
- **THEN** the execution strike's final damage skips the defense subtraction entirely, the immolation's damage settles at its authored static coefficient, the caster carries the authored self-burn instance ticking at its authored rung and duration whether or not the damage leg lands, and no healing of any kind is applied by the immolation composition

#### Scenario: The capstone burns enemies and itself as three independent components
- **WHEN** a synthetic two-parent capstone area composition with its authored static coefficient, its enemy-side authored burn component and its self-burn cost component resolves against a mixed battlefield
- **THEN** every selected enemy takes the authored coefficient damage and carries the authored enemy burn rung, the caster alone carries the authored self-burn rung, the ally targets take neither leg, and each component settles independently

#### Scenario: Branching and the two-parent capstone gate through the lineage engine
- **WHEN** a synthetic family replicates the documented root chain, the three-way branch point, the branch-terminal leaves and the two-parent capstone prerequisite shape
- **THEN** use rejects until every authored threshold is met, the capstone unlocks only when BOTH authored parents reach their authored thresholds, each branch progresses independently, and prerequisite caps stay derived from the shared reverse-edge map with leaves at the shared tip cap

#### Scenario: Retired dev-era clauses resolve as ordinary rejections
- **WHEN** a caller casts a never-existing fire key through the ordinary cast surface after replacement, or a previously declared fire skill's off-tree healing clause is referenced as an effect binding
- **THEN** each rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on
