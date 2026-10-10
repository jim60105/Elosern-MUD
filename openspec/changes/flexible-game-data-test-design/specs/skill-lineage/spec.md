# Spec Delta

## MODIFIED Requirements

### Requirement: The fire lineage ships as the authored branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored fire tree of the node-data
authority (`docs/lore/skill-trees/fire.md`). `fire_arrow` is a root with no prerequisites. The
structure is a branching DAG whose strict topological canopy is `crimson_apotheosis` (consuming both
authored parents, itself consumed by no edge). The five element-mastery passives SHALL NOT be tree
nodes (PASSIVE skills are never consumed by edges and never accrue).

#### Scenario: The fire tree validates with the canopy last
- **WHEN** the registry loads with the authored fire edges
- **THEN** the topological order runs `fire_arrow` first and `crimson_apotheosis` last (consuming two
  parents and consumed by no edge), `sacrificial_flame` is consumed only by the capstone edge at
  its authored threshold, and every edge threshold is >= 1

#### Scenario: Mastery passives stay out of the graph
- **WHEN** the reverse-edge map is inspected for `fire_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The first-round spine survives verbatim
- **WHEN** the authored fire edges are declared
- **THEN** `fire_ball` requires `fire_arrow` >= its declared edge threshold
- **AND** `scorching_wave` requires `fire_ball` >= its declared edge threshold
- **AND** `firestorm` requires `scorching_wave` >= its declared edge threshold
- **AND** `lava_burst` requires `firestorm` >= its declared edge threshold
- **AND** `dragon_flame` requires `lava_burst` >= its declared edge threshold
- **AND** `sacrificial_flame` requires `dragon_flame` >= its declared edge threshold

#### Scenario: Sister spells keep their leaf edges onto the spine
- **WHEN** the authored fire edges are declared
- **THEN** `flame_shroud` requires `scorching_wave` >= its declared edge threshold
- **AND** `hellfire` requires `firestorm` >= its declared edge threshold
- **AND** `final_blaze` requires `hellfire` >= its declared edge threshold

#### Scenario: The catalog wave adds the third branch child
- **WHEN** the catalog wave extends the fire tree
- **THEN** `scorching_armor` requires `scorching_wave` >= its declared edge threshold, the third child of the branch point

#### Scenario: The capstone demands both authored parents
- **WHEN** the catalog wave extends the fire tree
- **THEN** the two-parent capstone `crimson_apotheosis` requires `sacrificial_flame` >= its declared edge threshold AND
  `final_blaze` >= its declared edge threshold

#### Scenario: Sacrificial flame yields its canopy status
- **WHEN** the reverse-edge map is inspected for `sacrificial_flame`
- **THEN** it is no longer a canopy node: its authored edge feeds the capstone

#### Scenario: Threshold tuning preserves topology
- **WHEN** a valid positive edge threshold changes
- **THEN** topology/reference checks remain green; fixed synthetic trees independently prove multi-parent qualification, reverse-edge caps and exact boundary behavior


### Requirement: The wind lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored wind tree of the node-data authority (`docs/lore/skill-trees/wind.md`): TWO roots ;  `gale_step` (mobility) and `wind_blade` (destruction) ;  each with no prerequisites. The structure is a two-root DAG whose strict topological canopy is `sky_apotheosis`; `wind_mastery` and `flight` SHALL NOT be tree nodes (PASSIVE skills are never consumed by edges and never accrue).

#### Scenario: The wind tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored wind edges
- **THEN** the topological order runs both roots (`gale_step`, `wind_blade`) before their descendants and `sky_apotheosis` last (consuming two parents and consumed by no edge), `sky_tempest` and `vacuum_severance` are consumed only by the canopy edge at its authored threshold, and every edge threshold is >= 1

#### Scenario: Both branches of the destruction root validate in parallel
- **WHEN** the reverse-edge map is inspected for `tornado_blade`
- **THEN** it is consumed by exactly two edges (storm_domain at its declared edge threshold and gale_dance_strike at its declared edge threshold ;  the two authored branch children), each branch progresses through validation independently, and no cross-branch edge exists between the storm and dance chains

#### Scenario: Mastery and movement passives stay out of the graph
- **WHEN** the reverse-edge map is inspected for `wind_mastery` and `flight`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The mobility chain is linear
- **WHEN** the authored wind edges are declared
- **THEN** `gale_chain_step` requires `gale_step` >= its declared edge threshold
- **AND** `afterimage_step` requires `gale_chain_step` >= its declared edge threshold
- **AND** `haste_domain` requires `afterimage_step` >= its declared edge threshold, a branch-terminal leaf

#### Scenario: The destruction branch point feeds both authored children
- **WHEN** the authored wind edges are declared
- **THEN** `tornado_blade` requires `wind_blade` >= its declared edge threshold ;  the branch point feeding BOTH authored children
- **AND** `storm_domain` requires `tornado_blade` >= its declared edge threshold
- **AND** `gale_dance_strike` requires `tornado_blade` >= its declared edge threshold

#### Scenario: The storm branch chain
- **WHEN** the authored wind edges are declared
- **THEN** `heavens_wrath_storm` requires `storm_domain` >= its declared edge threshold
- **AND** `sky_tempest` requires `heavens_wrath_storm` >= its declared edge threshold

#### Scenario: The dance branch chain
- **WHEN** the authored wind edges are declared
- **THEN** `sky_rending_slash` requires `gale_dance_strike` >= its declared edge threshold
- **AND** `vacuum_severance` requires `sky_rending_slash` >= its declared edge threshold

#### Scenario: The two-parent 神格 canopy demands both parents
- **WHEN** the authored wind edges are declared
- **THEN** the two-parent 神格 canopy `sky_apotheosis` requires `sky_tempest` >= its declared edge threshold AND
  `vacuum_severance` >= its declared edge threshold ;  consuming both authored parents and itself consumed by no edge

#### Scenario: Threshold tuning preserves topology
- **WHEN** a valid positive edge threshold changes
- **THEN** topology/reference checks remain green; fixed synthetic trees independently prove multi-parent qualification, reverse-edge caps and exact boundary behavior


### Requirement: The ice lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored ice tree of the node-data
authority (`docs/lore/skill-trees/ice.md`): TWO roots ;  `frost_breath` (遲緩路線) and `ice_shard`
(監禁路線) ;  each with no prerequisites. The two routes are otherwise independent chains; they
converge ONLY at the strict topological canopy `eternal_frost_apotheosis`. The element-mastery
passive SHALL NOT be a tree node.

#### Scenario: The ice tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored ice edges
- **THEN** the topological order runs both roots (`frost_breath`, `ice_shard`) before their
  descendants and `eternal_frost_apotheosis` last (consuming two parents and consumed by no edge),
  `eternal_ice_field` and `absolute_zero` are consumed only by the canopy edge at its authored threshold, and
  every edge threshold is >= 1

#### Scenario: Both branch points gate exactly their two authored children
- **WHEN** the reverse-edge map is inspected for `ice_wall` and `ice_prison`
- **THEN** `ice_wall` is consumed by exactly two edges (frost_mire at its declared edge threshold and permafrost_domain at its declared edge threshold)
  and `ice_prison` is consumed by exactly two edges (blizzard at its declared edge threshold and crystal_shatter at its declared edge threshold), each
  route progresses through validation independently, and no cross-route edge exists between the
  slow line and the imprisonment line outside the canopy's two authored parent edges

#### Scenario: The mastery passive stays out of the graph
- **WHEN** the reverse-edge map is inspected for `ice_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The slow line branch point feeds both authored children
- **WHEN** the authored ice edges are declared
- **THEN** `ice_wall` requires `frost_breath` >= its declared edge threshold ;  the branch point feeding BOTH authored children
- **AND** `frost_mire` requires `ice_wall` >= its declared edge threshold, a branch-terminal leaf
- **AND** `permafrost_domain` requires `ice_wall` >= its declared edge threshold

#### Scenario: The permafrost chain continues
- **WHEN** the authored ice edges are declared
- **THEN** `absolute_tundra` requires `permafrost_domain` >= its declared edge threshold
- **AND** `eternal_ice_field` requires `absolute_tundra` >= its declared edge threshold

#### Scenario: The imprisonment line branch point feeds both authored children
- **WHEN** the authored ice edges are declared
- **THEN** `frost_arrow_rain` requires `ice_shard` >= its declared edge threshold
- **AND** `ice_prison` requires `frost_arrow_rain` >= its declared edge threshold ;  the second branch point feeding BOTH
  authored children
- **AND** `blizzard` requires `ice_prison` >= its declared edge threshold
- **AND** `crystal_shatter` requires `ice_prison` >= its declared edge threshold, a branch-terminal leaf

#### Scenario: The blizzard chain continues
- **WHEN** the authored ice edges are declared
- **THEN** `absolute_zero` requires `blizzard` >= its declared edge threshold

#### Scenario: The canopy demands both authored parents
- **WHEN** the authored ice edges are declared
- **THEN** `eternal_frost_apotheosis` requires `eternal_ice_field` >= its declared edge threshold AND `absolute_zero` >= its declared edge threshold

#### Scenario: The canopy consumes both routes and nothing consumes it
- **WHEN** the canopy's edges are inspected
- **THEN** `eternal_frost_apotheosis` consumes both authored parents and is itself consumed by no
  edge ;  the lore's 匯合 of 遲緩 and 監禁 at the 神格 rung

#### Scenario: PASSIVE rationale for staying out of the graph
- **WHEN** the element-mastery passive is considered as a tree node
- **THEN** it is excluded because PASSIVE skills are never consumed by edges and never accrue

#### Scenario: Threshold tuning preserves topology
- **WHEN** a valid positive edge threshold changes
- **THEN** topology/reference checks remain green; fixed synthetic trees independently prove multi-parent qualification, reverse-edge caps and exact boundary behavior


### Requirement: The lightning lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored lightning tree of the node-data
authority (`docs/lore/skill-trees/lightning.md`): TWO roots ;  `static_ward` (先制路線) and
`spark_shock` (過載路線) ;  each with no prerequisites. The two routes are otherwise independent
chains; they converge ONLY at the strict topological canopy `thunder_apotheosis`. The
element-mastery passive SHALL NOT be a tree node.

#### Scenario: The lightning tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored lightning edges
- **THEN** the topological order runs both roots (`static_ward`, `spark_shock`) before their
  descendants and `thunder_apotheosis` last (consuming two parents and consumed by no edge),
  `judgement_thunder` and `divine_lightning_slaughter` are consumed only by the canopy edge at
  its authored threshold, and every edge threshold is >= 1

#### Scenario: Both branch points gate exactly their authored children
- **WHEN** the reverse-edge map is inspected for `spark_shock`, `thunder_combo` and the two
  branch-terminal leaves
- **THEN** `spark_shock` is consumed by exactly two edges (chain_lightning at its declared edge threshold and paralyzing_bolt
  at its declared edge threshold) and `thunder_combo` by exactly two (thunder_gods_haste at its declared edge threshold and thunder_shatter_strike at
  5), `thunder_shatter_strike` and `thunder_prison` consume exactly one edge each and are consumed
  by none, and no cross-route edge exists between the initiative line and the overload line outside
  the canopy's two authored parent edges

#### Scenario: The mastery passive stays out of the graph
- **WHEN** the reverse-edge map is inspected for `lightning_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge

#### Scenario: The initiative line branch point feeds both authored children
- **WHEN** the authored lightning edges are declared
- **THEN** `lightning_flicker` requires `static_ward` >= its declared edge threshold
- **AND** `thunder_combo` requires `lightning_flicker` >= its declared edge threshold ;  the branch point feeding BOTH authored
  children
- **AND** `thunder_gods_haste` requires `thunder_combo` >= its declared edge threshold
- **AND** `thunder_shatter_strike` requires `thunder_combo` >= its declared edge threshold, a branch-terminal leaf

#### Scenario: The haste chain continues
- **WHEN** the authored lightning edges are declared
- **THEN** `judgement_thunder` requires `thunder_gods_haste` >= its declared edge threshold

#### Scenario: The overload root branches at itself
- **WHEN** the authored lightning edges are declared
- **THEN** `chain_lightning` requires `spark_shock` >= its declared edge threshold AND `paralyzing_bolt` requires
  `spark_shock` >= its declared edge threshold ;  the root's own branch point

#### Scenario: The overload chains continue
- **WHEN** the authored lightning edges are declared
- **THEN** `lightning_strike` requires `chain_lightning` >= its declared edge threshold
- **AND** `thunder_prison` requires `paralyzing_bolt` >= its declared edge threshold, a branch-terminal leaf
- **AND** `heavens_thunder` requires `lightning_strike` >= its declared edge threshold
- **AND** `divine_lightning_slaughter` requires `heavens_thunder` >= its declared edge threshold

#### Scenario: The canopy demands both authored parents
- **WHEN** the authored lightning edges are declared
- **THEN** `thunder_apotheosis` requires `judgement_thunder` >= its declared edge threshold AND
  `divine_lightning_slaughter` >= its declared edge threshold

#### Scenario: The canopy consumes both routes and nothing consumes it
- **WHEN** the canopy's edges are inspected
- **THEN** `thunder_apotheosis` consumes both authored parents and is itself consumed by no
  edge ;  the lore's 匯合 of 先制 and 過載 at the 神格 rung

#### Scenario: PASSIVE rationale for staying out of the graph
- **WHEN** the element-mastery passive is considered as a tree node
- **THEN** it is excluded because PASSIVE skills are never consumed by edges and never accrue

#### Scenario: Threshold tuning preserves topology
- **WHEN** a valid positive edge threshold changes
- **THEN** topology/reference checks remain green; fixed synthetic trees independently prove multi-parent qualification, reverse-edge caps and exact boundary behavior

