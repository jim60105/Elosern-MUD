## Purpose

Defines the typed effect-ID parsing module `world/skills/effects.py`: one frozen
dataclass per recognized effect prefix, a single `parse_effect` dispatch, and
the registry-load-time validation guarantee that an unrecognized prefix fails
at import, not silently at use.

## Requirements

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
`stimulus`, `pleasure_peak`, `gauge_transfer`, `revoke_grants`, `reveal_disguise`). `parse_effect` SHALL raise `ValueError` for any prefix
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
  any `pleasure_peak:<suffix>` form raises, and the enumeration above is exactly the recognized set

`revoke_grants` SHALL be a BARE prefix: it parses into a payload-free frozen marker dataclass, and any
payload (`revoke_grants:<anything>`) SHALL raise `ValueError` at parse and therefore at registry load.

#### Scenario: The bare revoke prefix parses into its marker dataclass
- **WHEN** `parse_effect("revoke_grants")` is called
- **THEN** it returns the payload-free revoke-grants dataclass

#### Scenario: A payload on the revoke prefix fails at registry load
- **WHEN** a skill declares `revoke_grants:all`
- **THEN** `parse_effect` raises `ValueError` and the registry fails to import

`reveal_disguise` SHALL accept exactly two closed grammar forms: the bare prefix, parsing to a
typed dataclass carrying the mundane-only strength, and `reveal_disguise:true_name`, parsing to the
same dataclass carrying the any-provenance strength. Every other payload SHALL raise `ValueError` at
parse and therefore at registry load.

#### Scenario: The bare reveal prefix parses at mundane-only strength
- **WHEN** `parse_effect("reveal_disguise")` is called
- **THEN** it returns the reveal dataclass carrying the mundane-only strength

#### Scenario: The true-name form parses at any-provenance strength
- **WHEN** `parse_effect("reveal_disguise:true_name")` is called
- **THEN** it returns the reveal dataclass carrying the any-provenance strength

#### Scenario: An unknown reveal payload fails at registry load
- **WHEN** a skill declares `reveal_disguise:everything`
- **THEN** `parse_effect` raises `ValueError` and the registry fails to import

### Requirement: A damage effect can declare the absence of an element
`parse_effect` SHALL accept the reserved element segment `none` on the `damage` prefix, returning a
typed damage effect whose element is `None` and whose school is the declared school. Every other
element segment SHALL keep parsing exactly as before, and the parsed element SHALL remain a value no
settlement path consumes: the school selects the attacking stat, and elemental affinity scales
practice only for a skill whose own element appears on a magic-school damage effect, which an
elementless effect can never satisfy.

#### Scenario: The reserved token parses to an absent element
- **WHEN** `parse_effect("damage:none:physical")` is called
- **THEN** it returns the damage effect type with an absent element and the school `physical`, and the
  same call for every registry element key returns that element unchanged

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

### Requirement: An elementless damage effect and a declared skill element are mutually exclusive
A skill definition SHALL fail construction when it declares an element together with an elementless
damage effect: the two authorities would then disagree about whether the skill has an element, and
presentation reads one while the effect declares the other. The check is one-directional by design —
an element-bearing damage effect on a skill that declares no element stays legal, because that shape
predates this change across shipped and synthetic definitions and is not this change's concern. A
skill with no damage effect at all SHALL be unaffected.

#### Scenario: An elementless effect on an element-bearing skill fails at load
- **WHEN** a skill is constructed declaring an element together with an elementless damage effect
- **THEN** construction raises with the contradiction named, and the same failure occurs at module
  import when such a definition is placed in the shipped registry — a startup failure, never a silent
  runtime mismatch

#### Scenario: A consistent or pre-existing declaration still constructs
- **WHEN** a skill declares no element with only elementless damage effects, or declares an element
  with damage effects of that element, or declares no element alongside an element-bearing damage
  effect, or declares no damage effect at all
- **THEN** construction succeeds and the definition exposes its declared element unchanged

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

### Requirement: Conditional damage policies compose without double matching
A damage effect SHALL support a validated target-fact predicate, conditional attack multiplier, conditional defense bypass and maximum-HP fraction. Multiple matching facts within one ANY predicate SHALL activate a policy once. Defaults SHALL preserve ordinary damage. Other elements SHALL be able to use the same policy behavior. Additionally, the predicate vocabulary SHALL accept a validated dynamic-fact entry of the form `buff:<definition-key>`, naming a loaded buff definition whose live, unexpired instance on the target IS the matching fact at settlement time; the entry SHALL be rejected at policy construction when the key names no loaded definition, and every other namespaced entry form SHALL keep failing exactly as before. A `buff:` entry SHALL match only through the target's current buff state — never through static affinity or classification data — and SHALL compose with bare static facts, the conditional multiplier, the conditional bypass and the maximum-HP fraction under the identical any-match-once-per-strike semantics, at any point in the action's life (a marker applied, expired or removed between authoring and settlement flips the fact with the instance). A policy MAY additionally declare the independent boolean `unconditional_defense_bypass` (default False), which ignores defense subtraction for EVERY target regardless of predicate match. Construction SHALL reject `unconditional_defense_bypass=True` co-declared with a non-empty `bypass_defense=True` (one meaning, one field) and accept it with an empty predicate (reducing to the shipped unconditional-execution behavior) or with any predicate set; the shipped conditional `bypass_defense` semantics stay unchanged, and every existing policy (empty or non-empty predicate, with or without conditional bypass) behaves bit-identically.

#### Scenario: Two facts match once
- **WHEN** a target matches both configured alternative classifications
- **THEN** the declared conditional multiplier applies once, not once per fact

#### Scenario: Bypass and bonus are independent
- **WHEN** a configured defense-bypass predicate matches without an attack bonus declaration
- **THEN** defense is ignored and no undeclared bonus appears

#### Scenario: Percent rider requires a hit
- **WHEN** a configured percent-HP damage effect misses
- **THEN** it deals zero damage including its percentage component

#### Scenario: A marker-fact entry matches while the live instance lasts
- **WHEN** a synthetic spell declares a `buff:` predicate entry with a conditional multiplier and strikes the same target before application, while a live synthetic buff instance of the named key is applied, and after that instance expires
- **THEN** only the during-instance strike receives the declared multiplier once, the other strikes deal ordinary policy-free damage, and no other policy component changes

#### Scenario: A marker entry composes any-match-once with static facts
- **WHEN** one ANY predicate declares both a static classification fact and a `buff:` fact, and the target satisfies both
- **THEN** the conditional multiplier applies once, not once per matching entry

#### Scenario: Only the buff namespace enters; unknown keys fail closed
- **WHEN** a policy declares `buff:<unknown-key>`, `terrain:cracked`, `hp_loss` or any other non-buff namespaced or unknown entry
- **THEN** construction raises naming the offending entry, and bare vocabulary entries keep their existing accepted/rejected set unchanged

#### Scenario: Unconditional bypass rides independently of the dynamic fact
- **WHEN** a synthetic policy declares a `buff:` predicate entry with a conditional multiplier plus `unconditional_defense_bypass`, and strikes the same high-defense target while standing-on-the-marker and while not standing on it
- **THEN** both strikes ignore defense subtraction while only the marker-standing strike receives the declared multiplier, a predicate-bearing `bypass_defense=True` policy keeps bypassing only on a static-predicate match, an empty-predicate `bypass_defense=True` policy keeps bypassing unconditionally, and a policy declaring both bypass fields True is rejected at construction

### Requirement: A follow-up strike repeats damage on evidence or unconditionally without repeating the action
A validated damage policy SHALL permit up to two extra independent strikes — either against a target with matching recent evidence (the evidence-conditional shape: `repeat_when` naming a recognized evidence kind, pinned to exactly one extra strike) or unconditionally on every successful action resolution (the predicate-free shape: an extra-strike declaration of one or two with no `repeat_when`). Each strike SHALL have an independent hit roll and the same coefficient/policy. No strike's miss SHALL suppress any later strike. The action SHALL pay resources/time and award eligible practice once, project ordered damage correctly across every strike, and retain all rolls while emitting at most one terminal defeat or knockout for a target regardless of the declared count. The extra-strike count SHALL stay within the closed set {0, 1, 2} of ADDITIONAL strikes (total strikes = 1 + the declared count); every other shipped `DamagePolicy` validation SHALL stay fail-closed exactly as before — the unknown-evidence-kind rejection, the boolean-count rejection, and the 「`repeat_when` requires `extra_strikes` of exactly one」 pin included — and the construction rule 「an extra strike requires `repeat_when`」 SHALL stay retired so the predicate-free shape is legal vocabulary for any element.

#### Scenario: A first miss does not suppress the second roll
- **WHEN** fixed rolls make the first strike miss and the follow-up hit on an eligible target under an evidence-conditional policy
- **THEN** only the second damages HP and both rolls are recorded for one paid cast

#### Scenario: Ineligible target has one strike
- **WHEN** recent evidence is missing or expired for an evidence-conditional policy
- **THEN** only the ordinary strike occurs

#### Scenario: Repeated damage is atomic and nonlethal aware
- **WHEN** two strikes cross a protected target or a later commit step fails
- **THEN** successful settlement floors HP at 1 with one knockout; a failed settlement restores all HP and evidence

#### Scenario: An unconditional policy always resolves two independent strikes
- **WHEN** a synthetic damage policy declares its extra strike with no evidence predicate and strikes any living target under each fixed roll pair (hit-hit, miss-hit, hit-miss, miss-miss)
- **THEN** exactly two independent hit rolls are recorded and each landing strike deals the same coefficient/policy damage, whatever recent evidence the target does or does not hold, and a policy-free control skill on the same target still resolves exactly one strike

#### Scenario: The predicate-free shape is validated like every other policy
- **WHEN** policies declare an extra strike with a valid evidence kind, with no predicate, with an unknown evidence kind, with a boolean or out-of-cap strike count, or with `repeat_when` and a strike count other than one
- **THEN** the well-formed shapes construct (conditional and unconditional at each legal count), and each malformed combination — a boolean count, a count above the closed set, any count alongside an unknown evidence kind, or `repeat_when` with a count other than one — still raises at construction exactly as before the widening

#### Scenario: Two extra strikes resolve three independent rolls in one paid cast
- **WHEN** a synthetic unconditional policy declares two extra strikes against one living target under fixed rolls covering an all-hit sweep and a hit-miss-hit sweep
- **THEN** exactly three independent hit rolls are recorded in order, each landing strike deals the same coefficient/policy damage with ordered HP projection across the sweep, resources and practice move once, and per-strike diversion planning keeps honoring the shipped cap and gauge ledgers across all three strikes

#### Scenario: The terminal emission stays singular across the widest sweep
- **WHEN** three strikes together cross an unprotected target's lethal threshold, and separately cross a protected companion's floor under the nonlethal policy
- **THEN** the unprotected crossing produces at most one defeat credit for the cast and the protected crossing floors HP at 1 with exactly one knockout mark, no per-strike duplication of either terminal surface

#### Scenario: A three-strike sweep rolls back as one unit
- **WHEN** a later commit step fails midway through a three-strike settlement
- **THEN** every staged strike's HP movement, diversion spending, and evidence are restored to the pre-cast state

### Requirement: Peak effects and marker-selected state maxima are validated typed behavior
Effect authoring SHALL accept a peak effect with declared recipient policy and an optional marker-bound maximum on a state-derived magnitude. Unknown effect syntax, invalid marker references and contradictory recipient policies SHALL fail before runtime. These declarations SHALL use the same behavior for synthetic spells of any element.

#### Scenario: Typed declaration is executable outside light
- **WHEN** a synthetic non-light spell declares a self peak and a marker-bound state magnitude
- **THEN** it follows the same recipient and bounded-state behavior without a light-spell identity requirement

#### Scenario: Malformed peak or marker is rejected
- **WHEN** authoring supplies unknown peak syntax or an unresolved configured marker
- **THEN** the definition is rejected rather than silently producing no effect
