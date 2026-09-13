## MODIFIED Requirements

### Requirement: A SINGLE-target sexual act cannot be self-cast
A `SEXUAL_ACT`-category skill with `target_spec=SINGLE` SHALL declare, through the targeting
requirement it produces, that the actor is not an acceptable target; the shared targeting pipeline
(`world/rules/targeting.py`) SHALL enforce that declaration and reject a resolved target identical to
the actor. The prohibition SHALL be owned by the skill definition rather than inferred by the pipeline
from the skill's category, so the pipeline stays free of any skill-category knowledge. The three
SINGLE-target seeds (`partner_caress`, `partner_hand_hold`, `combat_tease`) are two-participant acts by
construction: their `participant_counters` and the resist contest assume a second party, so
self-casting would credit lifetime counters (e.g. `duo_act_count`, `hostile_act_count`) with no partner
present.

#### Scenario: Self-casting a partner seed is rejected without crediting counters
- **WHEN** entity A casts `partner_caress` (or `partner_hand_hold`) with A itself as the target
- **THEN** the cast is rejected and `A.sexual.duo_act_count` remains `0`

#### Scenario: Self-casting the combat seed is rejected without crediting counters
- **WHEN** entity A casts `combat_tease` with A itself as the target
- **THEN** the cast is rejected and `A.sexual.hostile_act_count` remains `0`

#### Scenario: Every SINGLE-target sexual act declares the prohibition itself
- **WHEN** the targeting requirement of every `SEXUAL_ACT`-category skill with `target_spec=SINGLE` is
  inspected
- **THEN** each one carries the self-target prohibition, and the targeting module imports no skill
  category vocabulary to reach the same result
