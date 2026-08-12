## ADDED Requirements

### Requirement: flight and flash_step are PASSIVE
`flight` and `flash_step` SHALL declare `kind=SkillKind.PASSIVE` (reclassified from the previous
`SkillKind.ACTIVE`, which had no working cast path — `movement` was never registered in `action.py`'s
`_EFFECT_HANDLERS`). Ownership alone triggers the waiver behavior defined by the
`movement-cost-charging` capability; no cast action exists for either skill.

#### Scenario: flight is not castable via the normal ACTIVE-skill cast path
- **WHEN** a player attempts to cast `flight`
- **THEN** the attempt is rejected the same way casting any other `PASSIVE` skill is rejected
