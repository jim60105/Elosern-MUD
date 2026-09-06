# sexual-catalog-shame delta

## RENAMED Requirements

- FROM: `### Requirement: shame_provocative_gaze credits hostile_act_count on the actor only, never on a target`
- TO: `### Requirement: shame_provocative_gaze credits hostile_act_count on both participants`

## MODIFIED Requirements

### Requirement: shame_provocative_gaze credits hostile_act_count on both participants
`shame_provocative_gaze` SHALL declare `actor_counters=("hostile_act_count",)`
and `participant_counters=("hostile_act_count",)`. The provoked target was
subjected to a hostile sexual act, and `hostile_act_count` records
participation from either side. The counter stays asymmetric for the
direction-bound shame counters: the four public-exposure acts keep
`participant_counters=()` because `exposure_act_count` records one's own
exposure and `watched_count` records one's own watched experience — an
audience member underwent neither.

#### Scenario: Casting shame_provocative_gaze credits both participants
- **WHEN** entity A casts `shame_provocative_gaze` targeting entity B, both starting at
  `hostile_act_count == 0`
- **THEN** `A.sexual.hostile_act_count` equals `1` and `B.sexual.hostile_act_count` equals `1`
  afterward

#### Scenario: Public-exposure acts still credit direction-bound counters on the actor only
- **WHEN** an entity at `watched_count=10, exposure_act_count=20` casts `shame_public_performance`
  targeting one hostile entity
- **THEN** afterward the actor's `watched_count` equals `11` and `exposure_act_count` equals `21`,
  and the target's `watched_count` and `exposure_act_count` are unchanged
