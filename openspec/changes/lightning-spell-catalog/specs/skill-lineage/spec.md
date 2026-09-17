## ADDED Requirements

### Requirement: The lightning lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored lightning tree of the node-data
authority (`docs/lore/skill-trees/lightning.md`): TWO roots — `static_ward` (先制路線) and
`spark_shock` (過載路線) — each with no prerequisites. The initiative line runs `lightning_flicker`
requires `static_ward` >= 3; `thunder_combo` requires `lightning_flicker` >= 3 — the branch point
feeding BOTH authored children: `thunder_gods_haste` requires `thunder_combo` >= 5 and
`thunder_shatter_strike` requires `thunder_combo` >= 5 (branch-terminal leaf). The haste chain
continues `judgement_thunder` requires `thunder_gods_haste` >= 8. The overload line runs
`chain_lightning` requires `spark_shock` >= 3 AND `paralyzing_bolt` requires `spark_shock` >= 3 (the
root's own branch point); `lightning_strike` requires `chain_lightning` >= 3; `thunder_prison`
requires `paralyzing_bolt` >= 3 (branch-terminal leaf); `heavens_thunder` requires
`lightning_strike` >= 5; `divine_lightning_slaughter` requires `heavens_thunder` >= 8. The two
routes are otherwise independent chains; they converge ONLY at the strict topological canopy
`thunder_apotheosis`, requiring `judgement_thunder` >= 10 AND `divine_lightning_slaughter` >= 10
(consuming both authored parents, itself consumed by no edge) — the lore's 匯合 of 先制 and 過載 at
the 神格 rung. The element-mastery passive SHALL NOT be a tree node (PASSIVE skills are never
consumed by edges and never accrue).

#### Scenario: The lightning tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored lightning edges
- **THEN** the topological order runs both roots (`static_ward`, `spark_shock`) before their
  descendants and `thunder_apotheosis` last (consuming two parents and consumed by no edge),
  `judgement_thunder` and `divine_lightning_slaughter` are consumed only by the canopy edge at
  threshold 10, and every edge threshold is >= 1

#### Scenario: Both branch points gate exactly their authored children
- **WHEN** the reverse-edge map is inspected for `spark_shock`, `thunder_combo` and the two
  branch-terminal leaves
- **THEN** `spark_shock` is consumed by exactly two edges (chain_lightning at 3 and paralyzing_bolt
  at 3) and `thunder_combo` by exactly two (thunder_gods_haste at 5 and thunder_shatter_strike at
  5), `thunder_shatter_strike` and `thunder_prison` consume exactly one edge each and are consumed
  by none, and no cross-route edge exists between the initiative line and the overload line outside
  the canopy's two authored parent edges

#### Scenario: The mastery passive stays out of the graph
- **WHEN** the reverse-edge map is inspected for `lightning_mastery`
- **THEN** no entry is consumed by or consumes any prerequisite edge
