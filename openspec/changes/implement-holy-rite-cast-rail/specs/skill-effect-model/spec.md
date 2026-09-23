# skill-effect-model — delta for implement-holy-rite-cast-rail

## MODIFIED Requirements

### Requirement: parse_effect classifies every declared prefix into a typed dataclass
`world/skills/effects.py` SHALL define `parse_effect(effect_id: str)` returning one of a fixed set of
frozen dataclasses, one per recognized prefix. The recognized set is the complete set
already dispatched by `world/skills/effects.py` plus `stimulus` (introduced by
`light-sacrament-casting`, which syncs before this change) plus `pleasure_peak` plus `gauge_transfer` plus
`revoke_grants` (introduced by `conferral-revocation`, which syncs before this change) plus this change's
`reveal_disguise`,
namely: (`stat_multiply`, `growth_rate`, `sexual_magic_mastery`, `passive_buff`, `combat_prediction`,
`passive_trait`, `movement`, `weapon_style`, `confer_skill_partial`, `set_disguise`, `buff_apply`,
`self_buff_apply`, `confer_growth_rate`, `sexual_event`, `sexual_event_actor`, `sexual_event_target`,
`pleasure`, `sexual_counter`, `act_pair_event`, `damage`, `heal`, `self_heal`, `cleanse`, `disengage`,
`divine_mystery`, `divine_pleasure_max`, `divine_climax_extension_stage`, `divine_drain`,
`divine_saturate_sensitivity`, `divine_clamp_shame`, `divine_mark_submission`, `divine_restore_purity`,
`stimulus`, `pleasure_peak`, `gauge_transfer`, `revoke_grants`, `reveal_disguise`, plus `rite_blessing` and `rite_shelter` (introduced by `implement-holy-rite-cast-rail`). `rite_blessing` SHALL parse exactly `rite_blessing:<buff-key>` into a frozen typed dataclass carrying the `buffs.yaml` buff key (any other payload — bare, empty, or multi-segment — raises `ValueError` at parse and therefore at registry load). `rite_shelter` SHALL be a BARE prefix parsing into a payload-free frozen marker dataclass; any payload (`rite_shelter:<anything>`) SHALL raise `ValueError` at parse and therefore at registry load. `parse_effect` SHALL raise `ValueError` for any prefix
not in this set and SHALL retain every prefix previously recognized, so no shipped skill fails to
parse. `growth_rate` SHALL parse exactly the four-segment form
`growth_rate:<stat>:<multiplier>:<scope>`, where `<stat>` is `practice` (the retired `magic` stat
key keeps failing closed), `<multiplier>` is a finite non-negative number, and `<scope>` is a key of
`ELEMENT_REGISTRY` naming the one lineage tree whose practice the effect accelerates. The parsed
`GrowthRateEffect` SHALL carry that scope. The previous three-segment form
`growth_rate:<stat>:<multiplier>` SHALL raise `ValueError` and therefore fail registry load, so an
unscoped growth rate cannot survive as data with its old global meaning.
`gauge_transfer` SHALL parse `gauge_transfer:<gauge>:<drain|restore>:fixed:<positive int>`,
`gauge_transfer:<gauge>:<drain|restore>:fraction:<finite fraction in (0,1]>` and
`gauge_transfer:<gauge>:<drain|restore>:all` — with `<gauge>` from the closed set {`mp`, `hp`} and
`hp` admitted for `drain` only — into one frozen typed dataclass, and SHALL reject every other
payload at parse (and therefore at registry load). The corresponding immutable
`GaugeTransferPolicy` on `EffectPolicy` SHALL validate fail-closed like `DamagePolicy`: recovery share
within [0,1], bonus entries naming only existing buff-definition keys, bonuses declared only for
restore directions, an hp restore direction rejected as a construction error (HP restoration is the
heal effect's exclusive verb), and no potency coefficient attached to a transfer occurrence.
`self_heal` SHALL accept exactly two grammar forms on its one recognized prefix: the bare form,
parsing to the defaulted stat-basis `SelfHealEffect` exactly as before, and
`self_heal:missing_fraction:<finite fraction in (0,1]>`, parsing to a typed `SelfHealEffect`
carrying the missing-HP magnitude basis and its validated fraction. Every other `self_heal` payload
SHALL keep raising `ValueError` (and therefore failing at registry load), and a non-identity potency
coefficient attached to a `missing_fraction` occurrence SHALL be rejected at skill construction
(the declared fraction IS the magnitude).

#### Scenario: A known prefix parses into its dataclass
- **WHEN** `parse_effect("stat_multiply:atk_phys:100")` is called
- **THEN** it returns a `StatMultiplyEffect(trait="atk_phys", multiplier=100.0)` instance

#### Scenario: The read-time growth_rate prefix parses into its dataclass
- **WHEN** `parse_effect("growth_rate:practice:5:wind")` is called
- **THEN** it returns a `GrowthRateEffect` carrying `stat="practice"`, `multiplier=5.0` and
  `scope="wind"`

#### Scenario: Every unscoped or malformed growth_rate payload fails closed
- **WHEN** `parse_effect("growth_rate:practice:100")`, `parse_effect("growth_rate:magic:5:wind")`,
  `parse_effect("growth_rate:practice:5:notanelement")` and
  `parse_effect("growth_rate:practice:-1:wind")` are called
- **THEN** each raises `ValueError` at parse and therefore at registry load — the three-segment form
  because a growth rate must name its tree, the second because the retired stat key stays closed, the
  third because the scope is not an `ELEMENT_REGISTRY` key, and the fourth because the multiplier is
  negative

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

#### Scenario: Self-heal magnitude modes parse and every other payload fails closed
- **WHEN** `parse_effect("self_heal")` and `parse_effect("self_heal:missing_fraction:0.1")` are
  called, and separately `parse_effect("self_heal:missing_fraction")`,
  `parse_effect("self_heal:missing_fraction:0")`, `parse_effect("self_heal:missing_fraction:1.5")`,
  `parse_effect("self_heal:missing_fraction:-0.1")`, `parse_effect("self_heal:missing_fraction:abc")`
  and `parse_effect("self_heal:missing_fraction:0.1:extra")` are called, and authoring attaches a
  non-identity potency coefficient to a missing-fraction occurrence
- **THEN** the bare form returns the defaulted stat-basis dataclass, the fraction form returns the
  typed dataclass carrying the missing-HP basis and its fraction, every malformed form raises
  `ValueError` before any cast is possible, and the coefficient attachment raises at skill
  construction

#### Scenario: Every shipped registry effect still parses
- **WHEN** `SKILL_REGISTRY` is imported after this change and every registered effect string is parsed
- **THEN** no shipped sexual-act, divine or stimulus effect raises, the bare `pleasure_peak` parses,
  any `pleasure_peak:<suffix>` form raises, the bare `rite_shelter` and `rite_blessing:martial_blessing` parse, and the enumeration above is exactly the recognized set

`revoke_grants` SHALL be a BARE prefix: it parses into a payload-free frozen marker dataclass, and any
payload (`revoke_grants:<anything>`) SHALL raise `ValueError` at parse and therefore at registry load.

#### Scenario: The bare revoke prefix parses into its marker dataclass
- **WHEN** `parse_effect("revoke_grants")` is called
- **THEN** it returns the payload-free revoke-grants dataclass

#### Scenario: A payload on the revoke prefix fails at registry load
- **WHEN** a skill declares `revoke_grants:all`
- **THEN** `parse_effect` raises `ValueError` and the registry fails to import

`reveal_disguise` SHALL be a BARE prefix: it parses into a payload-free frozen marker dataclass
carrying no strength, and any payload — including the retired `reveal_disguise:true_name` form —
SHALL raise `ValueError` at parse and therefore at registry load. The grammar carries no strength
because a veil has only one grade: nothing in this world veils an entity except the bloodline-gated
divine mystery, so a reveal either lifts a veil or finds none.

#### Scenario: The bare reveal prefix parses into its marker dataclass
- **WHEN** `parse_effect("reveal_disguise")` is called
- **THEN** it returns the payload-free reveal marker dataclass, which carries no strength field —
  the mundane-only strength no longer exists

#### Scenario: The retired true-name form fails at parse
- **WHEN** `parse_effect("reveal_disguise:true_name")` is called
- **THEN** it raises `ValueError` and the registry fails to import — the strength-carrying grammar is
  retired, and an unqualified reveal now has the any-provenance meaning the suffix used to mark

#### Scenario: An unknown reveal payload fails at registry load
- **WHEN** a skill declares `reveal_disguise:everything`
- **THEN** `parse_effect` raises `ValueError` and the registry fails to import

#### Scenario: The rite prefixes parse their grammar and fail closed
- **WHEN** `parse_effect("rite_blessing:martial_blessing")` and `parse_effect("rite_shelter")` are
  called, and separately `parse_effect("rite_blessing")`, `parse_effect("rite_blessing:a:b")`,
  `parse_effect("rite_shelter:today")` and `parse_effect("rite_blessing:")` are called
- **THEN** the first two return the typed rite dataclasses, each malformed form raises `ValueError`
  before any cast is possible, and a registry row declaring `rite_blessing:martial_blessing`
  round-trips through `parsed_effects`
