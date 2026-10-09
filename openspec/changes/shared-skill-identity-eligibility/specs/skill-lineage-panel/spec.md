# Spec Delta

## MODIFIED Requirements

### Requirement: The lineage read model is pure, derived, and side-effect-free
`world/rules/lineage_query.py` SHALL define the frozen dataclasses
`LineageNodeView(skill_key, display_name_zh, owned, usable, level, xp_into_level,
xp_to_next_level, capped, prereq_text_zh)`, `LineageChainView(root_skill_key,
element_or_style_zh, nodes, consumed, meter)`, and `LineageView(chains,
completed_count, total_count)`, derived solely from the entity's persistent identity, `entity.db.skill_proficiency`
and `SKILL_REGISTRY` prerequisite data (plus the cached reverse-edge map and the
shared `can_use_skill` predicate and pure identity qualification).

#### Scenario: A capped mid-tree node reports saturation
- **WHEN** the view is built for an entity whose `fire_arrow` practice has saturated at its derived cap
- **THEN** the node carries `capped == True`, `xp_to_next_level == 0`, and `usable` agrees with `can_use_skill`

#### Scenario: A locked node names its missing edge
- **WHEN** the view is built for an entity owning `firestorm` with `scorching_wave` level 2
- **THEN** the `firestorm` node carries `usable == False` and `prereq_text_zh` naming 灼熱波動 at Lv.3

#### Scenario: The view is byte-identical across builds and writes nothing
- **WHEN** the view is built twice for one entity with no state change in between
- **THEN** the two `LineageView` instances are equal and entity/world state is unchanged

#### Scenario: Nodes are topologically ordered
- **WHEN** a chain view is built
- **THEN** `nodes` SHALL be in topological order

#### Scenario: Consumed means every node capped
- **WHEN** a chain view is built
- **THEN** `consumed` SHALL be true exactly when every node is capped

#### Scenario: Meter is shallowest-uncapped progress
- **WHEN** a chain view is built
- **THEN** `meter` SHALL be the 0..1 shallowest-uncapped progress

#### Scenario: Prereq text renders the unsatisfied edge
- **WHEN** a node has an unsatisfied prerequisite edge
- **THEN** `prereq_text_zh` SHALL render it as 「需「X Lv.N」」 from registry data and be empty for roots and unlocked nodes

#### Scenario: Chains come only from consumed roots
- **WHEN** chains are generated
- **THEN** they SHALL be generated exactly from the roots that at least one prerequisite edge consumes; a prerequisite-less skill nobody consumes is not a 系譜樹 and starts no chain. Each chain is the identity-eligible reverse-edge closure from its identity-eligible root, chains in registry order; excluded nodes and chains contribute no completion or total count

#### Scenario: Building a view has no side effects
- **WHEN** any view is built
- **THEN** it SHALL NOT create, mutate, or persist any entity or world state

## ADDED Requirements

### Requirement: Lineage filtering preserves racial discovery without exposing monster chains
Lineage SHALL filter identity-ineligible entries without using resource affordability or ownership as catalog admission. Roots not consumed by any prerequisite SHALL remain absent.

#### Scenario: Identity affects counts
- **WHEN** monster-only and character-racial synthetic chains are projected for an eligible character
- **THEN** monster entries affect no chains or counts, while eligible racial nodes remain visible with normal owned and usable fields

