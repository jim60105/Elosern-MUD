## REMOVED Requirements

### Requirement: SKILL_REGISTRY contains the full 水-element spell set
**Reason**: The old requirement mandates a duplicated ten-row data contract (the 2026-08-12 dev-era set, including five HP-heal spells the water tree's healing-funnel seam retires). The ratified wave NON-GOAL rules out water catalog/data-contract tests: no key-set equality, no row mirroring, no MP-cost/cap/tier table assertions, no echo of the skill-tree table.
**Migration**: Delete the water catalog echo table and its test class in `world/skills/tests/test_spell_catalogs.py`, the water rows in the tier-correspondence table, and the obsolete traceability/freeze entries during the separately authorized main-sync. Replace this requirement with the behavioral mana-tide progression requirement below, backed by synthetic behavior tests and one disposable real-engine scenario. The dev-era registry rows are deleted wholesale without an alias (zero users). No saved-data migration is introduced.

## ADDED Requirements

### Requirement: Water spell progression composes executable mana-tide behavior
The water spell family SHALL provide the documented two-root tide/deep-sea progression as executable skill behavior using the common effect, audience, policy, buff, modifier and reaction mechanisms: MP drain with caster recovery, MP-loss DoT tiers, an MP-diverting damage shield, marker-bonus and area MP restoration with a team share-bonus marker, execution-tier MP removal with bounded regen freeze, a source-qualified depletion reaction with a target-state damage redirect, a devastation area rung, and a two-parent capstone that drains every enemy and restores every ally in one paid cast. Branch and merge prerequisites SHALL gate use through the shared lineage engine independently of ownership, with tip caps from the existing reverse-edge derivation. The superseded HP-heal water spells SHALL be removed without an alias. Verification SHALL use synthetic configurations exercising the shared mechanisms plus one disposable real-engine scenario observing gauge, buff, lock and practice state — never catalog-row equality, key-set, cost/tier table, or skill-tree-table echo assertions.

#### Scenario: The mana-tide verb is observable at settlement
- **WHEN** synthetic water compositions mirroring the documented clauses resolve through ordinary action settlement
- **THEN** the target's MP pool, the caster's recovery, DoT ticks, shield diversion, restoration, suffocation lock, regen freeze and the capstone's enemy-drain/ally-restore all change observable state with one paid cast and atomic rollback

#### Scenario: Two roots, branch, and convergence gate through the lineage engine
- **WHEN** a synthetic family replicates the documented branching and the two-parent capstone prerequisite shape
- **THEN** use rejects until every authored threshold is met, capstone attainment follows both terminal branches, and caps stay derived from the shared reverse-edge map

#### Scenario: The family stays non-healing and light stays complementary
- **WHEN** the water family is exercised against injured allies
- **THEN** no water node restores HP — MP-family effects only — while HP restoration remains another family's authored behavior

#### Scenario: Retired keys resolve as ordinary rejections
- **WHEN** a player casts a deleted dev-era key through the ordinary cast surface after replacement
- **THEN** it rejects with the existing unknown-skill reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast path could land on
