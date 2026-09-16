## ADDED Requirements

### Requirement: The wind lineage ships as the authored two-root branching tree with a two-parent canopy
`SKILL_REGISTRY` SHALL carry prerequisite edges forming the authored wind tree of the node-data authority (`docs/lore/skill-trees/wind.md`): TWO roots — `gale_step` (mobility) and `wind_blade` (destruction) — each with no prerequisites. The mobility chain is linear: `gale_chain_step` requires `gale_step` >= 3; `afterimage_step` requires `gale_chain_step` >= 3; `haste_domain` requires `afterimage_step` >= 5 (branch-terminal leaf). The destruction chain runs `tornado_blade` requires `wind_blade` >= 3 — the branch point feeding BOTH authored children: `storm_domain` requires `tornado_blade` >= 3 and `gale_dance_strike` requires `tornado_blade` >= 3. The storm branch runs `heavens_wrath_storm` requires `storm_domain` >= 5 and `sky_tempest` requires `heavens_wrath_storm` >= 8; the dance branch runs `sky_rending_slash` requires `gale_dance_strike` >= 8 and `vacuum_severance` requires `sky_rending_slash` >= 8. The two-parent 神格 canopy `sky_apotheosis` requires `sky_tempest` >= 10 AND `vacuum_severance` >= 10 — consuming both authored parents and itself consumed by no edge. The structure is therefore a two-root DAG whose strict topological canopy is `sky_apotheosis`; `wind_mastery` and `flight` SHALL NOT be tree nodes (PASSIVE skills are never consumed by edges and never accrue).

#### Scenario: The wind tree validates with two roots and the canopy last
- **WHEN** the registry loads with the authored wind edges
- **THEN** the topological order runs both roots (`gale_step`, `wind_blade`) before their descendants and `sky_apotheosis` last (consuming two parents and consumed by no edge), `sky_tempest` and `vacuum_severance` are consumed only by the canopy edge at threshold 10, and every edge threshold is >= 1

#### Scenario: Both branches of the destruction root validate in parallel
- **WHEN** the reverse-edge map is inspected for `tornado_blade`
- **THEN** it is consumed by exactly two edges (storm_domain at 3 and gale_dance_strike at 3 — the two authored branch children), each branch progresses through validation independently, and no cross-branch edge exists between the storm and dance chains

#### Scenario: Mastery and movement passives stay out of the graph
- **WHEN** the reverse-edge map is inspected for `wind_mastery` and `flight`
- **THEN** no entry is consumed by or consumes any prerequisite edge
