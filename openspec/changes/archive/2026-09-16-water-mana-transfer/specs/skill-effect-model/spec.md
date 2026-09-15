## MODIFIED Requirements

### Requirement: parse_effect classifies every declared prefix into a typed dataclass
`world/skills/effects.py` SHALL define `parse_effect(effect_id: str)` returning one of a fixed set of
frozen dataclasses, one per recognized prefix. The recognized set is the complete set
already dispatched by `world/skills/effects.py` plus `stimulus` (introduced by
`light-sacrament-casting`, which syncs before this change) plus `pleasure_peak` plus this change's
`gauge_transfer`,
namely: (`stat_multiply`, `growth_rate`, `sexual_magic_mastery`, `passive_buff`, `combat_prediction`,
`passive_trait`, `movement`, `weapon_style`, `confer_skill_partial`, `set_disguise`, `buff_apply`,
`self_buff_apply`, `confer_growth_rate`, `sexual_event`, `sexual_event_actor`, `sexual_event_target`,
`pleasure`, `sexual_counter`, `act_pair_event`, `damage`, `heal`, `self_heal`, `cleanse`, `disengage`,
`divine_mystery`, `divine_pleasure_max`, `divine_climax_extension_stage`, `divine_drain`,
`divine_saturate_sensitivity`, `divine_clamp_shame`, `divine_mark_submission`, `divine_restore_purity`,
`stimulus`, `pleasure_peak`, `gauge_transfer`). `parse_effect` SHALL raise `ValueError` for any prefix
not in this set and SHALL retain every prefix previously recognized, so no shipped skill fails to
parse. `growth_rate` SHALL be recognized because
`reincarnation_boon_elosia` already declares `growth_rate:practice:100`, which
the registry parses at load (the magic-XP consumer retired with
`magic-xp-engine-retirement`; the prefix stays until the use-driven ladder
lands); omitting it would make the registry's own import fail the
"every existing entry parses" scenario below.
`gauge_transfer` SHALL parse `gauge_transfer:<gauge>:<drain|restore>:fixed:<positive int>`,
`gauge_transfer:<gauge>:<drain|restore>:fraction:<finite fraction in (0,1]>` and
`gauge_transfer:<gauge>:<drain|restore>:all` — with `<gauge>` from the closed set {`mp`, `hp`} and
`hp` admitted for `drain` only — into one frozen typed dataclass, and SHALL reject every other
payload at parse (and therefore at registry load). The corresponding immutable
`GaugeTransferPolicy` on `EffectPolicy` SHALL validate fail-closed like `DamagePolicy`: recovery share
within [0,1], bonus entries naming only existing buff-definition keys, bonuses declared only for
restore directions, an hp restore direction rejected as a construction error (HP restoration is the
heal effect's exclusive verb), and no potency coefficient attached to a transfer occurrence.

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

#### Scenario: Standard stimulus accepts only declared participant scopes
- **WHEN** a synthetic spell declares stimulus:actor, stimulus:target or stimulus:both
- **THEN** it can execute its configured participant stimulus, while unknown scopes or numeric string suffixes fail authoring

#### Scenario: Gauge transfer modes parse and malformations fail closed
- **WHEN** `parse_effect("gauge_transfer:mp:drain:fraction:0.2")`, `parse_effect("gauge_transfer:mp:restore:fixed:40")`
  and `parse_effect("gauge_transfer:hp:drain:all")` are called, and separately `parse_effect("gauge_transfer:mp:drain:half")`,
  `parse_effect("gauge_transfer:mp:drain:fraction:1.5")`, `parse_effect("gauge_transfer:drain")`,
  `parse_effect("gauge_transfer:sp:drain:fixed:5")` and `parse_effect("gauge_transfer:hp:restore:fixed:40")` are called
- **THEN** the first three return the transfer dataclass with the declared gauge, direction and magnitude mode,
  and each malformed or illegal form raises `ValueError` before any cast is possible

#### Scenario: An invalid transfer policy fails at construction
- **WHEN** authoring attaches a recovery share outside [0,1], a per-stack bonus naming an unknown buff key,
  a bonus on a drain direction, an hp restore declaration, or a non-identity potency coefficient to a transfer policy
- **THEN** skill construction raises and no cast can be attempted

#### Scenario: Every shipped registry effect still parses
- **WHEN** `SKILL_REGISTRY` is imported after this change and every registered effect string is parsed
- **THEN** no shipped sexual-act, divine or stimulus effect raises, the bare `pleasure_peak` parses,
  any `pleasure_peak:<suffix>` form raises, and the enumeration above is exactly the recognized set

### Requirement: Effect audiences select recipients without changing skill faction constraints
Each effect SHALL permit an immutable audience of selected candidates, self, selected allies including selected self, or selected enemies. Unconfigured effects SHALL use the complete validated selection. Relation-based audiences SHALL never add unselected entities. Self-bound effects SHALL validate the actor and bind it once. An effect MAY additionally declare one immutable audience condition from the closed gauge-state vocabulary (the recipient's MP maximum zero, or positive), validated at authoring and evaluated at planning; a condition without an audience is contradictory and fails authoring. Invalid or contradictory audience declarations SHALL fail authoring.

#### Scenario: Same mechanism serves an alternate element
- **WHEN** a synthetic alternate-element spell combines enemy damage and ally recovery in a mixed selection
- **THEN** only enemies lose HP and only selected allies/self recover, while unselected bystanders remain unchanged

#### Scenario: Ordinary targeting remains free
- **WHEN** an unconfigured attack targets a companion or an unconfigured heal targets an enemy
- **THEN** the selected target receives the ordinary effect

#### Scenario: Explicit self binding is independent
- **WHEN** the caster is not in the explicit pool but one declared effect is self-bound
- **THEN** the actor receives that effect exactly once after ordinary validation

#### Scenario: A gauge-state condition rides an audience
- **WHEN** a synthetic component declares an audience plus one gauge-state condition, and separately an authoring declares the condition alone or both mutually exclusive facts together
- **THEN** the well-formed declaration restricts that component's recipients to the matching subset of its audience, while each contradictory declaration fails at skill construction
