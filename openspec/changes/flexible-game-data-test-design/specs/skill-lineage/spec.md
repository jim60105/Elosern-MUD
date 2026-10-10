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

### Requirement: can_use_skill is the single shared use-eligibility predicate
`can_use_skill(entity, skill)` SHALL be a pure query returning False unless the key is owned, identity/restrictions pass and every prerequisite key is owned at or above its declared minimum proficiency. The shared predicate SHALL gate ACTIVE spells and weapon skills alike.

#### Scenario: A mid-tree spell is gated by its own edge
- **WHEN** a fixed synthetic tree gives t_storm a t_wave prerequisite at level 3 and the owner has t_wave level 2
- **THEN** eligibility is False regardless of t_storm's own proficiency

#### Scenario: The exact threshold passes
- **WHEN** the synthetic owner's t_wave reaches 3
- **THEN** eligibility is True, without pinning any shipped edge

#### Scenario: The gate is school-agnostic
- **WHEN** an owned ACTIVE weapon skill has an unmet prerequisite
- **THEN** it uses the same False eligibility path as spells

#### Scenario: A root skill with no prereqs is usable on ownership
- **WHEN** an identity-eligible owner requests a synthetic root without prerequisites
- **THEN** eligibility is True regardless of proficiency

#### Scenario: Every consumer reads the single gate
- **WHEN** resolver step-1/preflight/resolve, action preview, submission revalidation, both skill menus or default attack policy needs eligibility
- **THEN** each consumes the same shared predicate rather than ownership-plus-MP-only logic

#### Scenario: An unmet chain is rejected as an unknown skill
- **WHEN** resolver step-1 sees an owned skill with an unmet chain
- **THEN** it rejects with UNKNOWN_SKILL and names the first unmet edge in declared order

#### Scenario: No mastery-tier override returns
- **WHEN** 主宰-tier entry is evaluated
- **THEN** all declared prerequisites use AND semantics with no mastery-tier override

#### Scenario: cost_tiers stays cosmetic
- **WHEN** a skill declares cost_tiers
- **THEN** it remains a display-only data label

### Requirement: Practice saturates at the derived tip cap
For skill S, cap(S) SHALL be the maximum minimum proficiency of all edges consuming S, or the authored progression tip cap when no edge consumes S. Once proficiency reaches that cap, further practice SHALL NOT accrue. Synthetic numeric fixtures SHALL NOT approve shipped edge/tip values.

#### Scenario: A fully consumed node stops at its edge
- **WHEN** a synthetic root is consumed by an edge requiring level 3 and continues practice at level 3
- **THEN** its stored XP stops increasing at level 3

#### Scenario: The canopy node caps at the yaml default
- **WHEN** a synthetic canopy with no consumers has a fixed synthetic tip cap 10
- **THEN** accrual saturates at 10; production canopy cap follows its current declaration

#### Scenario: A saturation ceiling still unlocks its child
- **WHEN** a synthetic parent caps at 5 because its child requires 5 and practice reaches 5
- **THEN** the child passes eligibility

#### Scenario: One shared award primitive clamps every writer
- **WHEN** saturation is enforced
- **THEN** one shared sole proficiency award primitive clamps storage at cap(S)

#### Scenario: Both accrual entry points route through the primitive
- **WHEN** per-use grants or booked-practice settlement award XP
- **THEN** both use that shared primitive and cannot diverge at cap boundaries

#### Scenario: The cap never starves a consuming edge
- **WHEN** a consumed skill's cap is derived
- **THEN** it is not below any consuming threshold, so saturation cannot block a child

### Requirement: The freeform scale ladder is anchored to proficiency
Allowed freeform scales SHALL derive from the authored progression ladder over the skill's OWN proficiency, gated by its element-mastery key. Rungs above the skill's derived cap SHALL never unlock. Numeric ladder examples SHALL use fixed synthetic rows rather than approve production thresholds or scale values.

#### Scenario: A mastery holder at level 0 sees only the small rungs
- **WHEN** a fixed synthetic ladder allows 0.25 unconditionally, 0.5 at 1, 1.0 at 3, 2.0 at 6 and 4.0 at 10, and an entitled synthetic skill owner is at level 0
- **THEN** allowed scales are (0.25,)

#### Scenario: Canopy proficiency unlocks the 4.0 rung
- **WHEN** that synthetic skill reaches level 10 under synthetic tip cap 10
- **THEN** 4.0 appears

#### Scenario: A capped mid-tree skill stops below the canopy rungs
- **WHEN** a synthetic mid-tree skill with cap 5 is practiced past its cap under the same fixture
- **THEN** its maximum scale is 1.0, with the level-6 and level-10 rungs absent

#### Scenario: No mastery still means no ladder
- **WHEN** an actor lacks the required element-mastery key
- **THEN** the scale set is empty regardless of proficiency

#### Scenario: Tip caps prune unreachable rungs
- **WHEN** a rung threshold exceeds the derived tip cap
- **THEN** it never unlocks

#### Scenario: The ladder is fully deterministic
- **WHEN** scales are derived
- **THEN** registry and proficiency state alone determine them, with no hidden information

#### Scenario: All surfaces share one derivation
- **WHEN** the resolver gate, preview and combat panel require allowed scales
- **THEN** they consume the same skill-anchored derivation

### Requirement: Import and scene-build auto-seed prerequisite proficiency exactly
Within the all-or-nothing import transaction, missing prerequisite proficiency SHALL seed exactly to its declared requirement, never above, and ownership SHALL extend to transitive closure. Explicit proficiency SHALL always win, even below eligibility. Scene spawn and preset activation SHALL share the same closure/seed mechanisms.

#### Scenario: A deep imported skill arrives usable
- **WHEN** a fixed synthetic import owns t_storm requiring t_wave level 3 with no explicit t_wave proficiency
- **THEN** the loaded owner has the closed chain, t_wave exactly level 3 and passing eligibility

#### Scenario: Explicit proficiency beats auto-seed
- **WHEN** that synthetic record explicitly gives t_wave XP 120, level 2
- **THEN** level 2 remains and the unmet edge is not overwritten

#### Scenario: Auto-seed never overshoots
- **WHEN** a fixed synthetic edge requires level 5
- **THEN** seeded XP is exactly 250 under the existing 50-XP-per-level mechanism

#### Scenario: Malformed imports still reject all-or-nothing
- **WHEN** another invalid field accompanies auto-seeding
- **THEN** the whole record rejects and nothing persists, including seeded values

#### Scenario: An unregistered proficiency key rejects the record
- **WHEN** a record includes not_a_skill with XP 50
- **THEN** validation names the key and persists nothing

#### Scenario: Preset activation shares the same helpers
- **WHEN** preset activation seeds an edge
- **THEN** it produces the same result as import for identical skill inputs via the same two helpers

#### Scenario: Normalization precedes semantic validation
- **WHEN** an import is processed
- **THEN** auto-seed normalization precedes semantic validation and schema range checks still reject malformed records wholesale

#### Scenario: Explicit proficiency always wins
- **WHEN** an import has an explicit proficiency entry
- **THEN** it wins even if its edge remains unmet

#### Scenario: Explicit keys resolve in the registry against the raw record
- **WHEN** explicit proficiency keys are validated
- **THEN** validation reads the raw record before normalization, naming and rejecting unknown keys rather than dropping/persisting them

#### Scenario: The NPC spawn path shares the helper
- **WHEN** scene-builder NPC spawn seeds lineage proficiency
- **THEN** it uses the character-loader's shared helper

#### Scenario: Preset activation composes the helpers directly
- **WHEN** preset activation seeds proficiency
- **THEN** it composes ownership closure and proficiency seed directly over declared keys, not the import-record wrapper

#### Scenario: Exactly three production callers
- **WHEN** production closure/seed callers are counted
- **THEN** there are exactly three, with no reimplemented closure/seed algorithm


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
  its declared positive edge threshold), `thunder_shatter_strike` and `thunder_prison` consume exactly one edge each and are consumed
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

