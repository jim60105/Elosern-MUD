# sexual-catalog-shame Delta Specification

## MODIFIED Requirements

### Requirement: Every act except shame_provocative_gaze reuses the self_exposure event; no new sexual.yaml row is added
`shame_half_expose_chest`, `shame_half_expose_lower`, `shame_loosen_collar`, `shame_full_expose`,
`shame_public_masturbation`, `shame_public_performance`, `shame_devoted_pose`, and
`shame_shameless_declaration` SHALL each declare `"self_exposure"` in `sexual_events`.
`shame_provocative_gaze` SHALL declare `sexual_events=()`. `world/rules/rulebook/sexual.yaml` SHALL
gain no rule row from this change.

#### Scenario: Casting a Tier 1 act raises the actor's own exposure
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_half_expose_chest` on
  itself
- **THEN** `entity.sexual.exposure`'s ordinal increases by exactly `1`

#### Scenario: shame_provocative_gaze does not raise the actor's own exposure
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_provocative_gaze`
- **THEN** the actor's `exposure` ordinal is unchanged afterward

#### Scenario: An AREA shame act's self_exposure reaches every participant
- **WHEN** an entity whose `exposure` is at its vocabulary floor casts `shame_public_performance`
  targeting one other entity
- **THEN** the target's `exposure` ordinal increases by exactly `1`, and the actor's `exposure`
  ordinal also increases by exactly `1` — the performing actor is publicly exposed too, per the
  participant-scoped `sexual_event:` semantics `sexual-intercourse-acts` establishes (partner
  design.md D-3)
