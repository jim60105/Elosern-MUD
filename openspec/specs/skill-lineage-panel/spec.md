## Purpose

Define the pure skill-lineage read model and its user surfaces: the bounded versioned OOB lineage panel contract, the WebClient big-window renderer, the Telnet `lineage` command, and the derived unlock notification riding the post-commit notification channel.

## Requirements

### Requirement: The lineage read model is pure, derived, and side-effect-free
`world/rules/lineage_query.py` SHALL define frozen dataclasses for a member's lineage as connected skill graphs: `LineageNodeView`, `LineageEdgeView`, `LineageGraphView` and `LineageView`, derived solely from stored identity, `entity.db.skill_proficiency`, registry prerequisites, the reverse-edge map and `can_use_skill`. Each dataclass's declared fields are enumerated in the first scenario.

#### Scenario: The views expose their declared fields
- **WHEN** a lineage view is built
- **THEN** `LineageNodeView` carries `skill_key`, `display_name_zh`, `owned`, `usable`, `ready`, `level`, `xp_into_level`, `xp_to_next_level`, `capped`, `prereq_text_zh`, `depth`; `LineageEdgeView` carries `from_key`, `to_key`, `min_level`; `LineageGraphView` carries `graph_id`, `group_label_zh`, `root_keys`, `nodes`, `edges`, `owned_count`, `total_count`, `consumed`; and `LineageView` carries `graphs`, `completed_count`, `total_count`

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
- **WHEN** a graph view is built
- **THEN** `nodes` SHALL be in topological order, each node appears exactly once even when it merges two parents, and `depth` is its longest prerequisite path from a root

#### Scenario: Consumed means every node capped
- **WHEN** a graph view is built
- **THEN** `consumed` SHALL be true exactly when every node of that graph is capped

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
- **WHEN** 冰槍 requires 冰錐術 Lv 3
- **THEN** the ice graph carries exactly one edge from 冰錐術 to 冰槍 with `min_level == 3`, and a two-parent merge node carries one edge per parent

#### Scenario: Ready marks an unowned node whose prerequisites are met
- **WHEN** a node is not owned and every prerequisite edge's minimum level is met
- **THEN** the node carries `ready == True`, and no owned node is ever ready

#### Scenario: Valid synthetic installed and grafted lineage reaches both consumers
- **WHEN** a valid synthetic companion's lineage is read repeatedly through authenticated text and the viewed-member panel after synthetic installation and browser graft completion
- **THEN** both surfaces are available with matching bounded roots, node identities and prerequisite edges, every node is topologically ordered once, and stored member and world state remain unchanged

#### Scenario: Valid merge graphs are distinguished from malformed cycles
- **WHEN** lineage consumers read a valid branching graph with a two-parent merge, and separately encounter malformed or cyclic source data
- **THEN** the valid graph remains readable with consistent prerequisite edges and counts, while invalid sources retain safe refusal or unavailable responses without fabricated nodes or query-time repair

### Requirement: The lineage panel ships as one bounded versioned OOB contract
The presentation registry SHALL register panel name `lineage` at schema version 2
with the availability discriminator and `kind` `lineage` in the available form,
built for the session's viewed party member (falling back to the commander). The
payload SHALL serialize the `LineageView` graphs under `LINEAGE_MAX_GRAPHS`,
`LINEAGE_MAX_NODES_PER_GRAPH`, `LINEAGE_MAX_EDGES_PER_GRAPH` and bounded text
lengths, truncating in the declared order to fit the envelope, with no version-1
compatibility.

#### Scenario: Oversized content truncates deterministically
- **WHEN** an entity's registry lineage exceeds `LINEAGE_MAX_GRAPHS`
- **THEN** the payload truncates in the declared order, remains schema-valid, and no cap violation reaches the browser

#### Scenario: A malformed source fails the panel closed
- **WHEN** `db.skill_proficiency` carries a structurally invalid entry for a registry skill
- **THEN** the `lineage` panel becomes unavailable through the common unavailable form with no fabricated node values

#### Scenario: Counts survive truncation
- **WHEN** the payload truncates
- **THEN** `completed_count` and `total_count` always describe the full, untruncated view, and no edge references a truncated node

#### Scenario: Contract mirrors ship in lockstep
- **WHEN** the lineage contract changes
- **THEN** the four contract mirrors — protocol validator, panel view, JS validator, and boundary tests — SHALL ship in lockstep, and boundary tests SHALL pin every cap

#### Scenario: The panel follows the viewed member
- **WHEN** the session's viewed member is 艾拉, including while the player possesses 卡恩
- **THEN** the lineage payload describes 艾拉's graphs and is republished by `party.view_member`

### Requirement: The party window lineage tab renders the graphs from the view alone
The party window's 系譜 tab SHALL render the viewed member's `lineage` v2 graphs, with each graph's `owned_count / total_count` and the tab's `已完成 completed_count / total_count 樹`. Every rendered value SHALL come from the panel payload; the client SHALL compute no growth rules and render no chain meter.

#### Scenario: Expanded fire tree shows per-node meters
- **WHEN** a player opens the fire graph with `fire_arrow` at 23/50 into level 1
- **THEN** the node renders the meter 「23/50 → 下一階」 and the tab header counts only fully-`consumed` graphs

#### Scenario: Node states render from the payload
- **WHEN** a graph holds a saturated node, a locked node and a ready node
- **THEN** the saturated node is marked 見頂, the locked node carries `prereq_text_zh`, and the ready node is marked 可解鎖

#### Scenario: The client invents nothing
- **WHEN** the payload omits a graph (truncated or unavailable)
- **THEN** the tab renders no placeholder graph and no invented progress

### Requirement: The lineage Telnet command mirrors the panel surface
A `lineage [<成員>]` command (alias `系譜`) on the `CharacterCmdSet` SHALL print the
same graphs the panel renders for the named member (default: the commander):
graphs in registry order with roots and owned/total counts, nodes in topological
order with their prerequisite edges and minimum levels, 見頂 on saturated nodes,
可解鎖 on ready nodes, and `prereq_text_zh` on locked nodes. It SHALL be available
in and out of combat, SHALL mutate nothing, and SHALL be documented in both player
command documents.

#### Scenario: The printed tree equals the panel view
- **WHEN** a player types `系譜 艾拉` in or out of combat
- **THEN** the printed graphs, node order, edges, 見頂 and 可解鎖 markers, and prerequisite lines match the panel's view for 艾拉, and stored state is unchanged

#### Scenario: A malformed record prints one fixed line
- **WHEN** `db.skill_proficiency` carries a structurally invalid entry
- **THEN** the command prints the fixed unavailable line and repairs nothing

### Requirement: A newly usable skill pushes one derived unlock notification
When a per-use or booked-study practice grant makes `can_use_skill` flip from false to true for any
skill whose prerequisite edges consume the granted skill (reverse-edge map), the system
SHALL stage exactly one Traditional-Chinese unlock line through the existing post-commit
notification channel to the commander: the existing line (e.g. 「新法術可用：火焰風暴」) when the
learner is the commander, and 「{成員} 學會了 {技能}」 when the learner is a companion.

#### Scenario: Meeting an edge announces the child node
- **WHEN** practice on `scorching_wave` reaches level 3 for an entity owning `firestorm`
- **THEN** exactly one unlock toast naming 火焰風暴 is pushed, and a second grant at the same level pushes none

#### Scenario: Auto-seed notifies nobody
- **WHEN** an import auto-seed satisfies deep prerequisite edges
- **THEN** no unlock toast is produced

#### Scenario: The channel is the title-grant toast channel
- **WHEN** an unlock line is staged
- **THEN** it rides the same one title-grant toasts ride: `ActionResult.notifications`, delivered by the owning settlement boundary to every client type as a text line

#### Scenario: Unlock state is derived, never persisted
- **WHEN** unlock state is computed
- **THEN** it SHALL be recomputed from proficiency, never persisted

#### Scenario: Staging waits for commit
- **WHEN** a grant's transaction has not yet committed
- **THEN** the unlock line SHALL be staged only after the transaction that applied the grant commits

#### Scenario: Scene-build auto-seed notifies nobody
- **WHEN** a scene-build auto-seed grants practices
- **THEN** the unlock line SHALL NOT fire

#### Scenario: A companion unlock names the companion
- **WHEN** companion 艾拉's practice on 治癒之光 makes 群體治癒 usable during a field cast
- **THEN** the commander receives exactly one line 「艾拉 學會了 群體治癒」 after the cast commits

#### Scenario: Booked study announces unlocks
- **WHEN** a rest settles 艾拉's booking and the study grant makes 群體治癒 usable
- **THEN** the rest summary delivered to the commander includes 「艾拉 學會了 群體治癒」 once, after the advance commits

### Requirement: Lineage filtering preserves racial discovery without exposing monster chains
Lineage SHALL filter identity-ineligible entries without using resource affordability or ownership as catalog admission. Roots not consumed by any prerequisite SHALL remain absent.

#### Scenario: Identity affects counts
- **WHEN** monster-only and character-racial synthetic chains are projected for an eligible character
- **THEN** monster entries affect no chains or counts, while eligible racial nodes remain visible with normal owned and usable fields
