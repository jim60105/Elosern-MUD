## RENAMED Requirements

- FROM: `### Requirement: The fire lineage ships as the first-round linear tree`
- TO: `### Requirement: The fire lineage ships as the authored branching tree with a two-parent canopy`

## MODIFIED Requirements

### Requirement: The fire lineage ships as the authored branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored fire tree of the node-data
authority (`docs/lore/skill-trees/fire.md`): the first-round spine survives verbatim — `fire_ball`
requires `fire_arrow` >= 3; `scorching_wave` requires `fire_ball` >= 3; `firestorm` requires
`scorching_wave` >= 3; `lava_burst` requires `firestorm` >= 5; `dragon_flame` requires `lava_burst`
>= 8; `sacrificial_flame` requires `dragon_flame` >= 8 — and the sister spells keep their leaf edges
onto the same spine: `flame_shroud` requires `scorching_wave` >= 3, `hellfire` requires `firestorm`
>= 5, and `final_blaze` requires `hellfire` >= 5. The catalog wave ADDS the branching edges:
`scorching_armor` requires `scorching_wave` >= 3 (the third child of the branch point), and the
two-parent capstone `crimson_apotheosis` requires `sacrificial_flame` >= 10 AND `final_blaze` >= 10.
`fire_arrow` is a root with no prerequisites. The structure is therefore a branching DAG whose strict
topological canopy is `crimson_apotheosis` (consuming both authored parents, itself consumed by no
edge); `sacrificial_flame` is no longer a canopy node — its Lv.10 edge feeds the capstone. The five
element-mastery passives SHALL NOT be tree nodes (PASSIVE skills are never consumed by edges and
never accrue).

#### Scenario: The fire tree validates with the canopy last
- **WHEN** the registry loads with the authored fire edges
- **THEN** the topological order runs `fire_arrow` first and `crimson_apotheosis` last (consuming two
  parents and consumed by no edge), `sacrificial_flame` is consumed only by the capstone edge at
  threshold 10, and every edge threshold is >= 1

#### Scenario: Mastery passives stay out of the graph
- **WHEN** the reverse-edge map is inspected for `fire_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge
