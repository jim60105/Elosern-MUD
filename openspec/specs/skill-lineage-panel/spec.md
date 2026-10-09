## Purpose

Define the pure skill-lineage read model and its user surfaces: the bounded versioned OOB lineage panel contract, the WebClient big-window renderer, the Telnet `lineage` command, and the derived unlock notification riding the post-commit notification channel.

## Requirements

### Requirement: The lineage read model is pure, derived, and side-effect-free
`world/rules/lineage_query.py` SHALL define the frozen dataclasses
`LineageNodeView(skill_key, display_name_zh, owned, usable, level, xp_into_level,
xp_to_next_level, capped, prereq_text_zh)`, `LineageChainView(root_skill_key,
element_or_style_zh, nodes, consumed, meter)`, and `LineageView(chains,
completed_count, total_count)`, derived solely from stored identity, `entity.db.skill_proficiency`,
`SKILL_REGISTRY` prerequisites, the reverse-edge map and the shared `can_use_skill` predicate.

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

### Requirement: The lineage panel ships as one bounded versioned OOB contract
The presentation registry SHALL register panel name `lineage` at schema version 1
with the standard availability discriminator and a `kind` of `lineage` in the
available form. The payload SHALL serialize the
`LineageView` under the conventional caps `LINEAGE_MAX_CHAINS`,
`LINEAGE_MAX_NODES_PER_CHAIN`, and bounded text lengths, truncating in a fixed
declared order (trailing chains, then trailing nodes, then further trailing
chains until the payload fits the envelope limit).

#### Scenario: Oversized content truncates deterministically
- **WHEN** an entity's registry lineage exceeds `LINEAGE_MAX_CHAINS`
- **THEN** the payload truncates in the declared order, remains schema-valid, and no cap violation reaches the browser

#### Scenario: A malformed source fails the panel closed
- **WHEN** `db.skill_proficiency` carries a structurally invalid entry for a registry skill
- **THEN** the `lineage` panel becomes unavailable through the common unavailable form with no fabricated node values

#### Scenario: Counts survive truncation
- **WHEN** the payload truncates
- **THEN** `completed_count` and `total_count` always describe the full, untruncated view

#### Scenario: Contract mirrors ship in lockstep
- **WHEN** the lineage contract changes
- **THEN** the four contract mirrors — protocol validator, panel view, JS validator, and boundary tests — SHALL ship in lockstep, and boundary tests SHALL pin every cap

### Requirement: The WebClient renders the lineage window from the view alone
The stage SHALL carry an icon opening a big-window lineage view. An expanded tree
SHALL render per-node level and an XP meter of `xp_into_level / 50` (e.g.
「23/50 → 下一階」, saturated nodes marked 見頂), locked nodes SHALL carry
`prereq_text_zh`, a collapsed tree SHALL render its chain `meter`, and the header
SHALL show `已完成 completed_count / total_count 樹`. Every rendered value SHALL
come from the panel payload; the client SHALL compute no growth rules.

#### Scenario: Expanded fire tree shows per-node meters
- **WHEN** a player expands the fire chain with `fire_arrow` at 23/50 into level 1
- **THEN** the node row renders the meter 「23/50 → 下一階」 and the header counts only fully-`consumed` chains

#### Scenario: The client invents nothing
- **WHEN** the payload omits a chain (truncated or unavailable)
- **THEN** the window renders no placeholder chain and no invented progress

### Requirement: The lineage Telnet command mirrors the panel surface
A `lineage` command on the `CharacterCmdSet` SHALL print the same tree the panel
renders: chains in registry order, nodes in topological order, 見頂 markers on
saturated nodes, and `prereq_text_zh` on locked nodes. The command SHALL be
available in and out of combat and SHALL mutate nothing.

#### Scenario: The printed tree equals the panel view
- **WHEN** a player types `lineage` in or out of combat
- **THEN** the printed chains, node order, 見頂 markers, and prerequisite lines match the panel's view, and stored state is unchanged

#### Scenario: A malformed record prints one fixed line
- **WHEN** `db.skill_proficiency` carries a structurally invalid entry
- **THEN** the command prints the fixed unavailable line and repairs nothing

### Requirement: A newly usable skill pushes one derived unlock notification
When a practice grant makes `can_use_skill` flip from false to true for any skill
whose prerequisite edges consume the granted skill (reverse-edge map), the system
SHALL stage exactly one Traditional-Chinese unlock line (e.g. 「新法術可用：火焰風暴」)
through the existing post-commit notification channel.

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

### Requirement: Lineage filtering preserves racial discovery without exposing monster chains
Lineage SHALL filter identity-ineligible entries without using resource affordability or ownership as catalog admission. Roots not consumed by any prerequisite SHALL remain absent.

#### Scenario: Identity affects counts
- **WHEN** monster-only and character-racial synthetic chains are projected for an eligible character
- **THEN** monster entries affect no chains or counts, while eligible racial nodes remain visible with normal owned and usable fields
