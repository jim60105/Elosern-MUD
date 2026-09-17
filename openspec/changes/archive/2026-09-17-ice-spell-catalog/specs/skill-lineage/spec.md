## ADDED Requirements

### Requirement: The ice lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored ice tree of the node-data
authority (`docs/lore/skill-trees/ice.md`): TWO roots — `frost_breath` (遲緩路線) and `ice_shard`
(監禁路線) — each with no prerequisites. The slow line runs `ice_wall` requires `frost_breath` >= 3
— the branch point feeding BOTH authored children: `frost_mire` requires `ice_wall` >= 3 (branch-
terminal leaf) and `permafrost_domain` requires `ice_wall` >= 3. The permafrost chain continues
`absolute_tundra` requires `permafrost_domain` >= 8 and `eternal_ice_field` requires
`absolute_tundra` >= 8. The imprisonment line runs `frost_arrow_rain` requires `ice_shard` >= 3;
`ice_prison` requires `frost_arrow_rain` >= 3 — the second branch point feeding BOTH authored
children: `blizzard` requires `ice_prison` >= 5 and `crystal_shatter` requires `ice_prison` >= 5
(branch-terminal leaf). The blizzard chain continues `absolute_zero` requires `blizzard` >= 8. The
two routes are otherwise independent chains; they converge ONLY at the strict topological canopy
`eternal_frost_apotheosis`, requiring `eternal_ice_field` >= 10 AND `absolute_zero` >= 10
(consuming both authored parents, itself consumed by no edge) — the lore's 匯合 of 遲緩 and 監禁 at
the 神格 rung. The element-mastery passive SHALL NOT be a tree node (PASSIVE skills are never
consumed by edges and never accrue).

#### Scenario: The ice tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored ice edges
- **THEN** the topological order runs both roots (`frost_breath`, `ice_shard`) before their
  descendants and `eternal_frost_apotheosis` last (consuming two parents and consumed by no edge),
  `eternal_ice_field` and `absolute_zero` are consumed only by the canopy edge at threshold 10, and
  every edge threshold is >= 1

#### Scenario: Both branch points gate exactly their two authored children
- **WHEN** the reverse-edge map is inspected for `ice_wall` and `ice_prison`
- **THEN** `ice_wall` is consumed by exactly two edges (frost_mire at 3 and permafrost_domain at 3)
  and `ice_prison` is consumed by exactly two edges (blizzard at 5 and crystal_shatter at 5), each
  route progresses through validation independently, and no cross-route edge exists between the
  slow line and the imprisonment line outside the canopy's two authored parent edges

#### Scenario: The mastery passive stays out of the graph
- **WHEN** the reverse-edge map is inspected for `ice_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge
