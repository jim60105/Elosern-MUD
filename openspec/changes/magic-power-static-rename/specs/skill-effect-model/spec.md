## MODIFIED Requirements

### Requirement: parse_effect classifies every declared prefix into a typed dataclass
`world/skills/effects.py` SHALL define `parse_effect(effect_id: str)` returning one of a fixed set of
frozen dataclasses, one per recognized prefix (`stat_multiply`, `growth_rate`, `element_mastery_rank`,
`sexual_magic_mastery`, `passive_buff`, `combat_prediction`, `passive_trait`, `movement`,
`weapon_style`, `confer_skill_partial`, `set_disguise`, `buff_apply`, `self_buff_apply`,
`confer_growth_rate`, `sexual_event`, `damage`, `heal`, `self_heal`, `cleanse`, `disengage`,
`divine_mystery`). `parse_effect` SHALL raise `ValueError` for any prefix not in this set.
`growth_rate` SHALL be recognized because
`reincarnation_boon_elosia` already declares `growth_rate:practice:100`, which
`world/rules/progression.py` consumes; omitting it would make the registry's own import fail the
"every existing entry parses" scenario below.

#### Scenario: A known prefix parses into its dataclass
- **WHEN** `parse_effect("stat_multiply:atk_phys:100")` is called
- **THEN** it returns a `StatMultiplyEffect(trait="atk_phys", multiplier=100.0)` instance

#### Scenario: The read-time growth_rate prefix parses into its dataclass
- **WHEN** `parse_effect("growth_rate:practice:100")` is called
- **THEN** it returns a `GrowthRateEffect(stat="practice", multiplier=100.0)` instance, and
  `parse_effect("growth_rate:magic:100")` raises `ValueError` (the retired stat key fails closed
  at parse and therefore at registry load)

#### Scenario: heal and self_heal parse into their dataclasses
- **WHEN** `parse_effect("heal:single")`, `parse_effect("heal:area")`, and
  `parse_effect("self_heal")` are called
- **THEN** they return `HealEffect(shape="single")`, `HealEffect(shape="area")`, and
  `SelfHealEffect()` respectively

#### Scenario: A malformed heal payload raises
- **WHEN** `parse_effect("heal:allies")` or `parse_effect("self_heal:single")` is called
- **THEN** it raises `ValueError`

#### Scenario: An unknown prefix raises
- **WHEN** `parse_effect("definitely_not_a_real_prefix:x")` is called
- **THEN** it raises `ValueError`
