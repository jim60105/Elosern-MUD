# Spec Delta

## MODIFIED Requirements

### Requirement: The lineage read model is pure, derived, and side-effect-free
`world/rules/lineage_query.py` SHALL define frozen dataclasses for a member's lineage as connected skill graphs: `LineageNodeView`, `LineageEdgeView`, `LineageGraphView` and `LineageView`, derived solely from stored identity, `entity.db.skill_proficiency`, registry prerequisites, the reverse-edge map and `can_use_skill`. Each dataclass's declared fields are enumerated in the first scenario.

#### Scenario: The views expose their declared fields
- **WHEN** a lineage view is built
- **THEN** `LineageNodeView` carries `skill_key`, `display_name_zh`, `owned`, `usable`, `ready`, `level`, `xp_into_level`, `xp_to_next_level`, `capped`, `prereq_text_zh`, `depth`; `LineageEdgeView` carries `from_key`, `to_key`, `min_level`; `LineageGraphView` carries `graph_id`, `group_label_zh`, `root_keys`, `nodes`, `edges`, `owned_count`, `total_count`, `consumed`; and `LineageView` carries `graphs`, `completed_count`, `total_count`

#### Scenario: A capped mid-tree node reports saturation
- **WHEN** the view is built for a fixed synthetic entity whose `t_root` practice has saturated at its derived cap
- **THEN** the node carries `capped == True`, `xp_to_next_level == 0`, and `usable` agrees with `can_use_skill`

#### Scenario: A locked node names its missing edge
- **WHEN** the view is built for a fixed synthetic entity owning `t_child` with `t_parent` level 2
- **THEN** the `t_child` node carries `usable == False` and `prereq_text_zh` naming the synthetic parent at Lv.3

#### Scenario: The view is byte-identical across builds and writes nothing
- **WHEN** the view is built twice for one entity with no state change in between
- **THEN** the two `LineageView` instances are equal and entity/world state is unchanged

#### Scenario: Nodes are topologically ordered
- **WHEN** a graph view is built
- **THEN** `nodes` SHALL be in topological order, each node appears exactly once even when it merges two parents, and `depth` is its longest prerequisite path from a root

#### Scenario: Consumed means every node capped
- **WHEN** a graph view is built
- **THEN** `consumed` is true exactly when every ACTIVE node is owned, usable and XP-capped, and every PASSIVE node is owned and usable without needing passive XP

#### Scenario: Meter is shallowest-uncapped progress
- **WHEN** a graph view is built
- **THEN** no meter is computed or serialized; `owned_count` and `total_count` report the graph's owned and total nodes instead

#### Scenario: Prereq text renders the unsatisfied edge
- **WHEN** a node has an unsatisfied prerequisite edge
- **THEN** `prereq_text_zh` SHALL render it as 「需「X Lv.N」」 from registry data and be empty for roots and unlocked nodes

#### Scenario: Chains come only from consumed roots
- **WHEN** graphs are generated
- **THEN** each graph SHALL be one connected component of the identity-eligible prerequisite graph (edges in both directions), with every node that declares no prerequisite listed in `root_keys` in registry order; a component with no edge SHALL be emitted only when its single skill is owned; excluded nodes contribute no counts

#### Scenario: Building a view has no side effects
- **WHEN** any view is built
- **THEN** it SHALL NOT create, mutate, or persist any entity or world state

#### Scenario: Edges carry their minimum level
- **WHEN** a synthetic child requires its synthetic parent at Lv.3
- **THEN** the synthetic graph carries exactly one edge from parent to child with `min_level == 3`, and a two-parent merge node carries one edge per parent

#### Scenario: Ready marks an unowned node whose prerequisites are met
- **WHEN** an identity/effect-eligible node is unowned and its directly owned prerequisites meet every edge, including the full lawful closure for an elemental mastery
- **THEN** the node carries `ready == True`, and no owned node is ever ready

#### Scenario: Valid synthetic installed and grafted lineage reaches both consumers
- **WHEN** a valid synthetic companion's lineage is read repeatedly through authenticated text and the viewed-member panel after synthetic installation and browser graft completion
- **THEN** both surfaces are available with matching bounded roots, node identities and prerequisite edges, every node is topologically ordered once, and stored member and world state remain unchanged

#### Scenario: Valid merge graphs are distinguished from malformed cycles
- **WHEN** lineage consumers read a valid branching graph with a two-parent merge, and separately encounter malformed or cyclic source data
- **THEN** the valid graph remains readable with consistent prerequisite edges and counts, while invalid sources retain safe refusal or unavailable responses without fabricated nodes or query-time repair

#### Scenario: A usable passive completes without passive practice
- **WHEN** a synthetic mastery is directly owned and usable at its genuine unpractised level
- **THEN** its node is complete with zero XP-to-next-level, and its graph can be consumed without any passive XP

#### Scenario: An unusable passive prevents completion
- **WHEN** a passive is unowned or its lawful closure fails while all ACTIVE nodes are XP-capped
- **THEN** the graph is incomplete and does not increase the completed count
