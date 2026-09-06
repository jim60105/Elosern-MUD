# sexual-act-seeds delta

## RENAMED Requirements

- FROM: `### Requirement: The combat seed credits hostile_act_count on the actor only`
- TO: `### Requirement: The combat seed credits hostile_act_count on both participants`

## MODIFIED Requirements

### Requirement: The combat seed credits hostile_act_count on both participants
`combat_tease` SHALL declare `actor_counters=("hostile_act_count",)` and
`participant_counters=("hostile_act_count",)`. A hostile sexual act happens
between two bodies, and `hostile_act_count` records participation from
either side.

#### Scenario: Casting combat_tease increments both participants' hostile_act_count
- **WHEN** entity A casts `combat_tease` on entity B, both starting at
  `hostile_act_count == 0`
- **THEN** `A.sexual.hostile_act_count` equals `1` and `B.sexual.hostile_act_count` equals `1`
  afterward
