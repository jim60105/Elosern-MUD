## ADDED Requirements

### Requirement: body_enhancement family is PASSIVE, not ACTIVE
`body_enhancement`, `body_enhancement_extreme`, and `body_enhancement_basic` SHALL declare
`kind=SkillKind.PASSIVE` (reclassified from the previous `SkillKind.ACTIVE`, which had no working cast
path — `stat_multiply` was never registered in `action.py`'s `_EFFECT_HANDLERS`, so every cast attempt
unconditionally rejected `UNKNOWN_EFFECT_ID`). Ownership continues to apply the multiplier via
`SkillHandler.effective_value` exactly as before; this requirement changes only `kind`, not any
multiplier math.

#### Scenario: body_enhancement is not castable via the normal ACTIVE-skill cast path
- **WHEN** a player attempts to cast `body_enhancement`
- **THEN** the attempt is rejected the same way casting any other `PASSIVE` skill is rejected (not
  `UNKNOWN_EFFECT_ID`)

#### Scenario: Ownership still applies the multiplier unconditionally
- **WHEN** an entity owns `body_enhancement_extreme` as a passive skill
- **THEN** `entity.skills.effective_value("atk_phys")` reflects the `stat_multiply:atk_phys:1000`
  multiplier exactly as it did before this change

### Requirement: reincarnation_boon_yuna's effect string is well-formed
`reincarnation_boon_yuna` SHALL declare `effects=["sexual_magic_mastery"]` (corrected from the
malformed three-segment `"element_mastery_rank:性魔法:主宰"`, which did not parse as a recognized
prefix and was inconsistent with every other mastery skill's two-segment form). This fix is a
prerequisite for this change's own registry-load-time validation to succeed on import.

#### Scenario: reincarnation_boon_yuna parses as SexualMasteryEffect
- **WHEN** `SKILL_REGISTRY["reincarnation_boon_yuna"].parsed_effects` is inspected
- **THEN** it contains exactly one `SexualMasteryEffect` instance and no `ElementMasteryEffect`
