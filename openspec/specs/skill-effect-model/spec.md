## Purpose

Defines the typed effect-ID parsing module `world/skills/effects.py`: one frozen
dataclass per recognized effect prefix, a single `parse_effect` dispatch, and
the registry-load-time validation guarantee that an unrecognized prefix fails
at import, not silently at use.

## Requirements

### Requirement: parse_effect classifies every declared prefix into a typed dataclass
`world/skills/effects.py` SHALL define `parse_effect(effect_id: str)` returning one of a fixed set of
frozen dataclasses, one per recognized prefix (`stat_multiply`, `growth_rate`, `element_mastery_rank`,
`sexual_magic_mastery`, `passive_buff`, `combat_prediction`, `passive_trait`, `movement`,
`weapon_style`, `confer_skill_partial`, `set_disguise`, `buff_apply`, `self_buff_apply`,
`confer_growth_rate`, `sexual_event`, `damage`, `heal`, `self_heal`, `cleanse`, `disengage`,
`divine_mystery`). `parse_effect` SHALL raise `ValueError` for any prefix not in this set.
`growth_rate` SHALL be recognized because
`reincarnation_boon_elosia` already declares `growth_rate:magic:100`, which
`world/rules/progression.py` consumes; omitting it would make the registry's own import fail the
"every existing entry parses" scenario below.

#### Scenario: A known prefix parses into its dataclass
- **WHEN** `parse_effect("stat_multiply:atk_phys:100")` is called
- **THEN** it returns a `StatMultiplyEffect(trait="atk_phys", multiplier=100.0)` instance

#### Scenario: The read-time growth_rate prefix parses into its dataclass
- **WHEN** `parse_effect("growth_rate:magic:100")` is called
- **THEN** it returns a `GrowthRateEffect(stat="magic", multiplier=100.0)` instance

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

### Requirement: SkillDef.__post_init__ rejects unparseable effects at construction
`SkillDef.__post_init__` SHALL call `parse_effect` on every string in `effects` and store the results
in a new `parsed_effects: tuple` field. Construction SHALL fail with the underlying `ValueError` if any
effect string does not parse.

#### Scenario: Registering a skill with an unrecognized effect prefix fails at import time
- **WHEN** a `SkillDef` is constructed with `effects=["not_a_real_prefix:x"]`
- **THEN** construction raises `ValueError`, and if this occurs inside `SKILL_REGISTRY`'s module-level
  construction, the module fails to import — a server startup failure, not a runtime no-op

#### Scenario: Every existing SKILL_REGISTRY entry still parses after this change
- **WHEN** `world.skills.registry` is imported
- **THEN** import succeeds, and every entry's `parsed_effects` is non-empty for every entry whose
  `effects` list is non-empty

### Requirement: passive_trait effects are declared inert by design, not by omission
`parse_effect("passive_trait:<name>")` SHALL return a `FlavorEffect(name=<name>)` instance. No
consumer in `world/rules/` or `world/skills/` SHALL read `FlavorEffect` to produce any mechanical
effect — its presence is purely descriptive.

#### Scenario: elf_longevity parses as flavor with no mechanical hook
- **WHEN** `parse_effect("passive_trait:elf_longevity")` is called
- **THEN** it returns `FlavorEffect(name="elf_longevity")`, and no function in `world/rules/combat.py`,
  `world/rules/progression.py`, or `world/rules/combat_modifiers.py` references `FlavorEffect`
