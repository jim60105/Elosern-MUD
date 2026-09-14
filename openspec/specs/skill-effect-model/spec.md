## Purpose

Defines the typed effect-ID parsing module `world/skills/effects.py`: one frozen
dataclass per recognized effect prefix, a single `parse_effect` dispatch, and
the registry-load-time validation guarantee that an unrecognized prefix fails
at import, not silently at use.

## Requirements

### Requirement: parse_effect classifies every declared prefix into a typed dataclass
`world/skills/effects.py` SHALL define `parse_effect(effect_id: str)` returning one of a fixed set of
frozen dataclasses, one per recognized prefix (`stat_multiply`, `growth_rate`,
`sexual_magic_mastery`, `passive_buff`, `combat_prediction`, `passive_trait`, `movement`,
`weapon_style`, `confer_skill_partial`, `set_disguise`, `buff_apply`, `self_buff_apply`,
`confer_growth_rate`, `sexual_event`, `damage`, `heal`, `self_heal`, `cleanse`, `disengage`,
`divine_mystery`). `parse_effect` SHALL raise `ValueError` for any prefix not in this set.
`growth_rate` SHALL be recognized because
`reincarnation_boon_elosia` already declares `growth_rate:practice:100`, which
the registry parses at load (the magic-XP consumer retired with
`magic-xp-engine-retirement`; the prefix stays until the use-driven ladder
lands); omitting it would make the registry's own import fail the
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

#### Scenario: The retired element_mastery_rank prefix fails closed
- **WHEN** `parse_effect("element_mastery_rank:主宰")` is called
- **THEN** it raises `ValueError` (the prefix left the recognized set together with the
  retired cast gate)

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

### Requirement: pleasure and sexual_counter parse into bare-key-carrying typed dataclasses
`world/skills/effects.py`'s `parse_effect` SHALL classify `pleasure:<act_key>` into
`PleasureEffect(act_key)` and `sexual_counter:<act_key>` into `SexualCounterEffect(act_key)`, using
the existing `_parse_single_arg` helper. Each dataclass SHALL carry exactly the one field `act_key:
str` and no other data — magnitude, parts, ratio, and counter names are read from
`SEXUAL_ACT_REGISTRY[act_key]` by the consuming effect handler, never encoded in the effect string.

#### Scenario: A well-formed pleasure effect parses
- **WHEN** `parse_effect("pleasure:masturbation_seed")` is called
- **THEN** it returns `PleasureEffect(act_key="masturbation_seed")`

#### Scenario: A well-formed sexual_counter effect parses
- **WHEN** `parse_effect("sexual_counter:masturbation_seed")` is called
- **THEN** it returns `SexualCounterEffect(act_key="masturbation_seed")`

#### Scenario: A malformed effect with no key raises at construction
- **WHEN** `parse_effect("pleasure:")` is called
- **THEN** it raises `ValueError`, matching every other `_parse_single_arg`-based prefix's existing
  behaviour for a missing argument

### Requirement: Per-effect potency is validated independently of effect identity
A skill SHALL support an immutable positive finite potency for each damage or healing effect occurrence. Potency SHALL be independently configurable for repeated effects, default to identity when omitted, and be applied before defense subtraction or healing rounding. Invalid potency or mismatched declarations SHALL fail before a cast can be attempted. Caller-supplied context SHALL NOT override authored potency. Other schools SHALL use the same behavior without named-spell branches.

#### Scenario: Repeated effects retain independent potency
- **WHEN** a synthetic skill contains two damage effects with distinct declared potencies
- **THEN** each strike uses its own potency and neither inherits the preceding effect configuration

#### Scenario: Defensive formula order matters
- **WHEN** equal successful rolls use potency 1 and 2 against nonzero defense
- **THEN** the attack component is scaled before subtracting defense, not the final damage

#### Scenario: Invalid and forged values cannot change a cast
- **WHEN** authoring supplies a boolean/nonfinite/nonpositive potency or a caller supplies a conflicting policy
- **THEN** invalid authoring is rejected and caller policy cannot change the authored resulting HP delta

#### Scenario: Healing composes and remains capped
- **WHEN** a synthetic heal combines potency, equipment gain and allowed freeform scaling
- **THEN** the specified stages apply once, independently clamp each HP gap and never revive an HP-zero recipient

### Requirement: Effect audiences select recipients without changing skill faction constraints
Each effect SHALL permit an immutable audience of selected candidates, self, selected allies including selected self, or selected enemies. Unconfigured effects SHALL use the complete validated selection. Relation-based audiences SHALL never add unselected entities. Self-bound effects SHALL validate the actor and bind it once. Invalid or contradictory audience declarations SHALL fail authoring.

#### Scenario: Same mechanism serves an alternate element
- **WHEN** a synthetic alternate-element spell combines enemy damage and ally recovery in a mixed selection
- **THEN** only enemies lose HP and only selected allies/self recover, while unselected bystanders remain unchanged

#### Scenario: Ordinary targeting remains free
- **WHEN** an unconfigured attack targets a companion or an unconfigured heal targets an enemy
- **THEN** the selected target receives the ordinary effect

#### Scenario: Explicit self binding is independent
- **WHEN** the caster is not in the explicit pool but one declared effect is self-bound
- **THEN** the actor receives that effect exactly once after ordinary validation

### Requirement: Conditional damage policies compose without double matching
A damage effect SHALL support a validated target-fact predicate, conditional attack multiplier, conditional defense bypass and maximum-HP fraction. Multiple matching facts within one ANY predicate SHALL activate a policy once. Defaults SHALL preserve ordinary damage. Other elements SHALL be able to use the same policy behavior.

#### Scenario: Two facts match once
- **WHEN** a target matches both configured alternative classifications
- **THEN** the declared conditional multiplier applies once, not once per fact

#### Scenario: Bypass and bonus are independent
- **WHEN** a configured defense-bypass predicate matches without an attack bonus declaration
- **THEN** defense is ignored and no undeclared bonus appears

#### Scenario: Percent rider requires a hit
- **WHEN** a configured percent-HP damage effect misses
- **THEN** it deals zero damage including its percentage component

### Requirement: A conditional follow-up strike repeats damage without repeating the action
A validated damage policy SHALL permit one extra independent strike against a target with matching recent evidence. Each strike SHALL have an independent hit roll and the same coefficient/policy. The first miss SHALL NOT suppress the second strike. The action SHALL pay resources/time and award eligible practice once, project ordered damage correctly, and retain both rolls while emitting at most one terminal defeat or knockout for a target.

#### Scenario: A first miss does not suppress the second roll
- **WHEN** fixed rolls make the first strike miss and the follow-up hit on an eligible target
- **THEN** only the second damages HP and both rolls are recorded for one paid cast

#### Scenario: Ineligible target has one strike
- **WHEN** recent evidence is missing or expired
- **THEN** only the ordinary strike occurs

#### Scenario: Repeated damage is atomic and nonlethal aware
- **WHEN** two strikes cross a protected target or a later commit step fails
- **THEN** successful settlement floors HP at 1 with one knockout; a failed settlement restores all HP and evidence
