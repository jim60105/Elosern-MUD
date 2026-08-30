## ADDED Requirements

### Requirement: The lineage read model is pure, derived, and side-effect-free
`world/rules/lineage_query.py` SHALL define the frozen dataclasses
`LineageNodeView(skill_key, display_name_zh, owned, usable, level, xp_into_level,
xp_to_next_level, capped, prereq_text_zh)`, `LineageChainView(root_skill_key,
element_or_style_zh, nodes, consumed, meter)`, and `LineageView(chains,
completed_count, total_count)`, derived solely from `entity.db.skill_proficiency`
and `SKILL_REGISTRY` prerequisite data (plus the cached reverse-edge map and the
shared `can_use_skill` predicate). `nodes` SHALL be in topological order;
`consumed` SHALL be true exactly when every node is capped; `meter` SHALL be the
0..1 shallowest-uncapped progress; `prereq_text_zh` SHALL render the unsatisfied
edge as 「需「X Lv.N」」 from registry data and be empty for roots and unlocked
nodes. Building any view SHALL NOT create, mutate, or persist any entity or
world state.

#### Scenario: A capped mid-tree node reports saturation
- **WHEN** the view is built for an entity whose `fire_arrow` practice has saturated at its derived cap
- **THEN** the node carries `capped == True`, `xp_to_next_level == 0`, and `usable` agrees with `can_use_skill`

#### Scenario: A locked node names its missing edge
- **WHEN** the view is built for an entity owning `firestorm` with `scorching_wave` level 2
- **THEN** the `firestorm` node carries `usable == False` and `prereq_text_zh` naming 灼熱波動 at Lv.3

#### Scenario: The view is byte-identical across builds and writes nothing
- **WHEN** the view is built twice for one entity with no state change in between
- **THEN** the two `LineageView` instances are equal and entity/world state is unchanged

### Requirement: The lineage panel ships as one bounded versioned OOB contract
The presentation registry SHALL register panel name `lineage` at schema version 1
with the standard availability discriminator. The payload SHALL serialize the
`LineageView` under the conventional caps `LINEAGE_MAX_CHAINS`,
`LINEAGE_MAX_NODES_PER_CHAIN`, and bounded text lengths, truncating in a fixed
declared order. The four contract mirrors — protocol validator, panel view, JS
validator, and boundary tests — SHALL ship in lockstep, and boundary tests SHALL
pin every cap.

#### Scenario: Oversized content truncates deterministically
- **WHEN** an entity's registry lineage exceeds `LINEAGE_MAX_CHAINS`
- **THEN** the payload truncates in the declared order, remains schema-valid, and no cap violation reaches the browser

#### Scenario: A malformed source fails the panel closed
- **WHEN** `db.skill_proficiency` carries a structurally invalid entry for a registry skill
- **THEN** the `lineage` panel becomes unavailable through the common unavailable form with no fabricated node values

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

#### Scenario: Telnet output matches the view
- **WHEN** a player runs `lineage`
- **THEN** the printed tree equals the `LineageView` content (same nodes, levels, saturation markers, prereq texts) and world/entity state is unchanged

### Requirement: A newly usable skill pushes one derived unlock notification
When a practice grant makes `can_use_skill` flip from false to true for any skill
whose prerequisite edges consume the granted skill (reverse-edge map), the system
SHALL push exactly one Traditional-Chinese unlock toast (e.g. 「新法術可用：火焰風暴」)
through the existing OOB toast/menu channel to a puppeted client (and the
equivalent text line to Telnet). Unlock state SHALL be recomputed from
proficiency, never persisted, and SHALL NOT fire during import or scene-build
auto-seed.

#### Scenario: Meeting an edge announces the child node
- **WHEN** practice on `scorching_wave` reaches level 3 for an entity owning `firestorm`
- **THEN** exactly one unlock toast naming 火焰風暴 is pushed, and a second grant at the same level pushes none

#### Scenario: Auto-seed notifies nobody
- **WHEN** an import auto-seed satisfies deep prerequisite edges
- **THEN** no unlock toast is produced
