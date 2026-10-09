## Purpose

Defines read-only skill queries, transient trait multipliers, scaled conferred grants, and the
single-writer boundaries for disguise effects and other persistent skill state.

## Requirements

### Requirement: SkillHandler is mounted directly as entity.skills
`LivingEntity` SHALL expose `entity.skills` as a `SkillHandler` instance bound to that entity — per
design doc §5.2, `skills` **is** the `SkillHandler`, the same relationship `traits` has to
`TraitHandler` — replacing change 3's placeholder `AttributeProperty`. The handler SHALL read its
backing data from the private `entity.db.skills` attribute, holding the
`{"active": [...], "passive": [...]}` structure change 4's loader writes there.

#### Scenario: entity.skills reads the raw skills dict from entity.db.skills
- **WHEN** `entity.db.skills` is `{"active": ["fire_ball"], "passive": ["defense_instinct"]}`
- **THEN** `entity.skills.owned_keys()` returns a list containing both `"fire_ball"` and
  `"defense_instinct"`

#### Scenario: entity.skills tolerates an entity never populated by the import loader
- **WHEN** `entity.db.skills` is `None` (an entity never run through change 4's loader)
- **THEN** `entity.skills.owned_keys()` returns an empty list rather than raising

#### Scenario: entity.skills has no bare-assignment form
- **WHEN** code attempts `entity.skills = {"active": [...], "passive": [...]}` directly
- **THEN** the assignment raises, since `entity.skills` is a read-only computed property returning a
  `SkillHandler` instance — the same way `entity.traits = {...}` is not a valid operation

#### Scenario: Writing to entity.db.skills directly is reflected by entity.skills
- **WHEN** code assigns `entity.db.skills = {"active": [...], "passive": [...]}` directly, the way
  change 4's landed `instantiate_character()` does
- **THEN** the assignment succeeds with no error, and `entity.skills` subsequently reflects the newly
  assigned data

### Requirement: effective_value is the sole resolution-time multiplier application point and never writes to entity.traits
`SkillHandler.effective_value(trait_key)` SHALL compute a derived value by reading
`entity.traits.<trait_key>.value` (the stored base value) and multiplying it by every currently-owned
active skill's matching `stat_multiply:<trait_key>:<multiplier>` effect and every applicable
source-skill multiplier times its conferred grant's fractional `scale` (see the conferral requirement
below), returning the result.

#### Scenario: effective_value multiplies the base trait value by an owned skill's multiplier
- **WHEN** an entity's `entity.traits.atk_phys.value` is `88` and the entity owns the
  `body_enhancement_extreme` skill (`stat_multiply:atk_phys:1000`) as active
- **THEN** `entity.skills.effective_value("atk_phys")` returns `88000`

#### Scenario: effective_value never mutates the stored trait value
- **WHEN** `effective_value("atk_phys")` is called on any entity
- **THEN** `entity.traits.atk_phys.value` is exactly the same before and after the call

#### Scenario: No function in world/skills/handler.py assigns to entity.traits
- **WHEN** `world/skills/handler.py`'s source is inspected
- **THEN** it contains no assignment expression targeting `entity.traits.<anything>`, `.base`, or
  `.mod` anywhere in the module

#### Scenario: Duplicate active skill keys resolve idempotently
- **WHEN** the same active skill key occurs more than once for an entity
- **THEN** its multiplier is applied once, resolution-idempotent rather than applying the multiplier
  repeatedly

#### Scenario: A contradictory SkillDef multiplier raises
- **WHEN** a single `SkillDef` defines more than one multiplier for the same trait and is encountered
- **THEN** the encounter raises, because a `SkillDef` SHALL NOT define more than one multiplier for
  the same trait

#### Scenario: An entity with no matching multiplier skill returns the unmultiplied base value
- **WHEN** an entity owns no skill whose `effects` include a `stat_multiply:atk_phys:*` entry
- **THEN** `entity.skills.effective_value("atk_phys")` returns exactly
  `entity.traits.atk_phys.value`

#### Scenario: Duplicate owned keys do not compound a multiplier
- **WHEN** an entity's active list contains `body_enhancement` twice
- **THEN** `effective_value("atk_phys")` applies its ×100 multiplier once, not twice

#### Scenario: A skill cannot define two multipliers for the same trait
- **WHEN** multiplier resolution encounters two `stat_multiply` effects for the same trait in one
  skill definition
- **THEN** it raises rather than silently choosing one interpretation

#### Scenario: Every static trait's stored base value stays within its documented band regardless of effective_value calls
- **WHEN** `effective_value()` is called any number of times, for any trait, on any entity
- **THEN** `entity.traits.atk_phys`, `agility`, and `defense`'s stored base values remain within the
  exact `StaticBand`/`static_band` range documented for that entity's race or monster tier — the same
  invariant change 3's D-7 established for construction, now unbroken by this change's
  resolution-time computation too

### Requirement: The 狀態偽裝 skill's effect resolution can only ever touch disguised_stats, never entity.traits
`world/rules/skill_effects.py` SHALL define `apply_disguise_effect(entity, overrides)` as the
deterministic-core write for the `status_disguise` `SkillDef`, and this function SHALL contain no
reference to `entity.traits` anywhere in its definition. No module under `world/skills/` SHALL write
persistent state.

The values the veil writes SHALL be DERIVED deterministically from the race registry's mundane bands
and SHALL NOT be supplied through `event_context`.

#### Scenario: apply_disguise_effect only changes disguised_stats
- **WHEN** `apply_disguise_effect(entity, {"atk_phys": 60})` is called on an entity whose true
  `atk_phys` base is `88`
- **THEN** `entity.db.disguised_stats["atk_phys"]` equals `60`, and `entity.traits.atk_phys.value`
  still equals `88`

#### Scenario: The function's source contains no reference to entity.traits
- **WHEN** `apply_disguise_effect`'s source code is inspected
- **THEN** it contains no reference to `entity.traits`, `get_display_value`, or any other trait-reading
  or trait-writing expression — the function's only side effect is assigning
  `entity.db.disguised_stats`

#### Scenario: Casting the veil with no supplied context veils the caster
- **WHEN** an unveiled entity casts the veil at itself with no `disguise` key in `event_context`
- **THEN** its displayed combat five all read the mundane ceilings the race registry declares, while
  every true trait value is unchanged

#### Scenario: The derived values carry no literal
- **WHEN** the mundane band values in the race registry are changed
- **THEN** the values a fresh veil writes change with them, because the recipe reads the registry

#### Scenario: Casting the veil at another entity veils that entity
- **WHEN** an entity casts the veil at a different entity
- **THEN** the target's displayed combat five read the derived values and the caster's own display is
  unchanged

#### Scenario: Casting the veil at a divinely-veiled self lifts it
- **WHEN** an entity carrying a veil of divine provenance casts the veil at itself again
- **THEN** its disguise layer and provenance record are cleared and `get_display_value` returns true
  values for every key

#### Scenario: Casting the veil over an authored veil refreshes rather than lifts
- **WHEN** an entity that started the game wearing an authored (mundane) disguise declaration casts the
  veil at itself
- **THEN** it is veiled at the derived values with divine provenance, and its display is NOT reverted
  to true values

#### Scenario: Displayed combat five render at the mundane band ceilings
- **WHEN** the veil derives its displayed values
- **THEN** each of the displayed combat five is rendered at the ceiling of the corresponding mundane
  band the registry already declares, so no balance constant is duplicated in code

#### Scenario: Derivation lives beside the write
- **WHEN** the veil's derived values are computed
- **THEN** derivation lives beside the write rather than inside it, so the write keeps its narrow
  single-writer contract

#### Scenario: The write records divine provenance
- **WHEN** the veil write stores a layer
- **THEN** it also records the veil's PROVENANCE as divine

#### Scenario: Self-cast toggles against a divine veil only
- **WHEN** a veil is cast at the actor
- **THEN** it SHALL clear the layer when the actor already carries a divine veil, and SHALL apply the
  derived veil when the actor carries none or carries a veil of mundane provenance

#### Scenario: The verb never lifts a veil it did not place
- **WHEN** the veil verb is cast and the target's veil was not placed by that verb
- **THEN** the veil the verb did not place is never lifted by casting the verb

#### Scenario: Casting the veil at an already-veiled other refreshes rather than lifts
- **WHEN** an entity casts the veil at a different entity that already carries a veil
- **THEN** the target stays veiled at the derived values, because only a self-cast toggles

### Requirement: world/skills is read-only and does not branch on combat state
Every public callable in `world/skills/handler.py` and `world/skills/equipment.py` SHALL accept no
parameter representing whether the entity is currently in combat, and SHALL contain no conditional
branch keyed on such a concept — matching design doc §5.2's statement that "a skill does not know
whether it is in combat." No production module under `world/skills/` SHALL write an entity's
persistent attributes or import mutators from `world.rules/`.

#### Scenario: No public function signature includes a combat-state parameter
- **WHEN** every public function and method in `world/skills/handler.py` and
  `world/skills/equipment.py` is inspected via `inspect.signature()`
- **THEN** no parameter name matches `in_combat`, `combat_state`, `is_combat`, or `turn`

#### Scenario: ActionResolver is the declared, undocumented-as-built seam for invoking these functions
- **WHEN** the codebase added by this change is inspected
- **THEN** it contains no `ActionResolver` class or equivalent turn-scheduling/out-of-combat-command
  dispatch logic — this change provides only the pure query/data functions a future `ActionResolver`
  (change 8) is expected to call from both the combat turn loop and out-of-combat command handling,
  per design doc §5.2's own statement that both call paths invoke the identical resolver

#### Scenario: Persistent writes stay inside the deterministic core
- **WHEN** production modules under `world/skills/` are inspected
- **THEN** they contain no persistent entity-state assignment and do not import
  `world.rules` mutators

### Requirement: owned_keys() includes every unlocked sexual act, and base_owned_keys() exposes the pre-extension set
`SkillHandler` SHALL expose `base_owned_keys()`, returning exactly the entity's imported active and
passive keys plus `INNATE_SKILL_ORDER` — the same list `owned_keys()` returned before this
requirement. `owned_keys()` SHALL return `base_owned_keys()` extended with every key in
`entity.sexual.unlocked_act_keys()` (when the entity has a `sexual` attribute), sorted, appended
after the base list.

#### Scenario: base_owned_keys() matches owned_keys()'s pre-extension behaviour exactly
- **WHEN** `base_owned_keys()` is called on any entity
- **THEN** it returns the entity's imported active and passive keys followed by `INNATE_SKILL_ORDER`,
  with no unlocked act key present

#### Scenario: owned_keys() includes unlocked sexual acts
- **WHEN** `owned_keys()` is called on an entity whose `entity.sexual.unlocked_act_keys()` returns a
  non-empty set
- **THEN** every key in that set is present in the returned list, in addition to every key
  `base_owned_keys()` would return

#### Scenario: owned_keys() equals base_owned_keys() when no act is unlocked
- **WHEN** `owned_keys()` is called on an entity whose `entity.sexual.unlocked_act_keys()` returns an
  empty set
- **THEN** the returned list equals `base_owned_keys()`'s return value exactly

#### Scenario: An entity with no sexual attribute still resolves owned_keys()
- **WHEN** `owned_keys()` is called on an entity with no `sexual` attribute at all
- **THEN** it returns `base_owned_keys()`'s value without raising

#### Scenario: handler.py reads sexual state duck-typed
- **WHEN** `world/skills/handler.py` needs the entity's sexual state
- **THEN** it reads it through a duck-typed `getattr(entity, "sexual", None)`

#### Scenario: world/skills/ keeps its independence from world/rules/
- **WHEN** `world/skills/handler.py` resolves owned keys
- **THEN** it imports nothing from `world.rules`, preserving `universal-action-ownership`'s existing
  "world/skills/ does not depend on world/rules/" requirement

#### Scenario: An unmaterialized entity's owned_keys() stays side-effect-free
- **WHEN** `owned_keys()` is called on an entity whose sexual handler was never mounted, while the
  catalogue contains a seed act (an act with an empty `unlock` mapping)
- **THEN** the seed act's key is present in the returned list, the act's key is absent when it has a
  nonzero counter threshold instead, and the sexual handler is still not materialized afterwards
  (no `sexual_traits` attribute created) — preview and no-create status reads stay side-effect-free

#### Scenario: world/skills/handler.py imports nothing from world.rules
- **WHEN** `world/skills/handler.py`'s import statements are inspected
- **THEN** none of them reference any `world.rules.*` module, and the sexual-state read is a
  duck-typed attribute access, not an import

### Requirement: Conferral records a data-scaled grant of every skill its caster owns (統御術)
`world/skills/handler.py` SHALL define a frozen `ConferredSkillGrant` dataclass (`source_key`,
`skill_key`, `scale`) and a read-only `SkillHandler.conferred_grants()` query over the
attribute `entity.db.skill_grants`. `effective_value()` SHALL fold every applicable source skill's
matching multiplier multiplied by the grant's fractional `scale` into its multiplier computation, in
addition to the entity's own owned skills. The store SHALL be keyed by `(source_key, skill_key)`.

#### Scenario: A conferred grant applies its own scale, independent of the source skill's own multiplier
- **WHEN** an entity has no `body_enhancement` skill of its own but has a `ConferredSkillGrant` with
  `skill_key="body_enhancement"`, `scale=0.1` (a ×10 partial effect of a ×100 source skill), and a base
  `atk_phys` of `60`
- **THEN** `entity.skills.effective_value("atk_phys")` returns `600` — a ×10 multiplier — not `6000`
  (which would be the source's own full ×100), with the affected trait(s) derived from
  `body_enhancement`'s own `parsed_effects` rather than a stored `trait_keys` field

#### Scenario: A conferred grant reaches rule-table adjustments, not only stat_multiply
- **WHEN** an entity has a `ConferredSkillGrant` with `skill_key="defense_instinct"`, `scale=0.5`, and
  does not own `defense_instinct` itself
- **THEN** `evaluate_combat_modifiers(entity)`'s bundle includes half of `defense_instinct`'s own
  `skill_owned` rule adjustment

#### Scenario: The deterministic-core primitive records a grant after resolver validation
- **WHEN** `record_conferred_grant(entity, "elosia", "body_enhancement", 0.1)` is called by
  deterministic resolution
- **THEN** `entity.skills.conferred_grants()` includes a `ConferredSkillGrant` with exactly those field
  values

#### Scenario: Conferring a gate-type effect is rejected
- **WHEN** `record_conferred_grant` or its resolver-level caller attempts to confer a skill whose sole
  parsed effect is `SexualMasteryEffect` or `DisguiseEffect`
- **THEN** the attempt raises `EFFECT_RESOLUTION_FAILED` and no `ConferredSkillGrant` is recorded

#### Scenario: Conferring an element-mastery skill is still rejected
- **WHEN** `record_conferred_grant` or its resolver-level caller attempts to confer a skill such as
  `fire_mastery` whose only parsed effect is the retired-cast-gate flavor
  `passive_trait:element_mastery`
- **THEN** the attempt raises `EFFECT_RESOLUTION_FAILED` (no continuous-valued effect to scale) and no
  `ConferredSkillGrant` is recorded

#### Scenario: Conferring a skill without any continuous effect is rejected
- **WHEN** `record_conferred_grant` or its resolver-level caller attempts to confer a skill whose
  parsed effects include no `StatMultiplyEffect` and no `RuleTableEffect` (for example a damage-only
  or flavor-only skill)
- **THEN** the attempt raises `EFFECT_RESOLUTION_FAILED` and no `ConferredSkillGrant` is recorded

#### Scenario: A conferral cast resolves without any supplied event context
- **WHEN** an entity that directly owns at least one conferrable passive casts a conferral skill at a
  valid target through an ordinary cast path, with no conferral keys in `event_context`
- **THEN** the cast resolves and the target holds one grant per conferrable owned skill, each at the
  occurrence's declared scale

#### Scenario: The node's declared scale is the recorded scale
- **WHEN** the conferring occurrence declares a coefficient of `0.25`
- **THEN** every grant the cast records carries `scale == 0.25`, whatever any caller-supplied context
  contains

#### Scenario: A caster with nothing conferrable is rejected, not silently committed
- **WHEN** an entity owning no skill that passes the conferrability shape validation casts a conferral
  skill
- **THEN** the action is rejected with `EFFECT_RESOLUTION_FAILED` and no grant is recorded

#### Scenario: Re-conferring the same skill from the same source replaces the grant
- **WHEN** the same source confers the same skill to the same target twice, at scale `0.1` then `0.25`
- **THEN** `conferred_grants()` holds exactly one grant for that pair, at scale `0.25`, and
  `effective_value()` folds the source multiplier once

#### Scenario: Two different sources conferring the same skill both count
- **WHEN** two different source entities each confer the same skill to one target
- **THEN** `conferred_grants()` holds two grants and both fold into `effective_value()`

#### Scenario: Conferring a skill the source does not own is rejected
- **WHEN** a conferral is attempted for a skill absent from the conferring entity's own owned keys
- **THEN** it raises `EFFECT_RESOLUTION_FAILED` and no `ConferredSkillGrant` is recorded

#### Scenario: A conferred grant cannot be conferred onward
- **WHEN** an entity that holds a skill only as a `ConferredSkillGrant` attempts to confer that same
  skill to a third entity
- **THEN** the attempt is rejected, because the ownership precondition reads direct ownership only

#### Scenario: The grant store is kept separate from owned skills
- **WHEN** conferral grants are stored
- **THEN** `entity.db.skill_grants` is kept separate from `entity.db.skills`'s import-populated
  `{"active": [...], "passive": [...]}` structure

#### Scenario: Grant trait keys derive at resolution time
- **WHEN** a conferred grant is resolved
- **THEN** its affected trait keys are derived from the referenced skill's own `parsed_effects` rather
  than duplicated in the grant record, because `trait_keys` is no longer a stored field

#### Scenario: The skill_owned context builder folds conferred adjustments
- **WHEN** the `skill_owned` rule-table context builder (`world/rules/combat_modifiers.py`, added by
  `skill-owned-rule-condition`) evaluates a grant referencing a skill whose parsed effect is a
  `RuleTableEffect`
- **THEN** it folds the conferred grant's scaled adjustment into its evaluated bundle

#### Scenario: ElementMasteryEffect left the gate-type enumeration
- **WHEN** a `<element>_mastery` skill is assessed for conferrability
- **THEN** `ElementMasteryEffect` left the gate-type enumeration together with the retired cast gate
  (`magic-xp-engine-retirement`): these skills now carry only the inert `passive_trait:element_mastery`
  flavor effect and are therefore rejected by the no-continuous-effect clause instead

#### Scenario: The write primitive lives in the single-writer core
- **WHEN** a conferral grant is written
- **THEN** the write primitive lives at `world.rules.skill_effects.record_conferred_grant()` so
  `world/skills/` remains outside the single-writer core

#### Scenario: A repeated conferral refreshes rather than compounds
- **WHEN** a grant is recorded for a `(source_key, skill_key)` pair that already has one
- **THEN** that grant is REPLACED rather than a second appended, so a repeated conferral refreshes the
  scale instead of compounding the multiplier

#### Scenario: Direct ownership gates the write path
- **WHEN** the conferral write path records a skill the conferring entity does not DIRECTLY own at
  record time
- **THEN** it rejects with the same `EFFECT_RESOLUTION_FAILED` rejection the shape validation uses, so
  a conferred grant can never exceed — or be chained onward from — what its source itself holds

#### Scenario: Scale comes from the node's coefficient, not context
- **WHEN** a conferral records its scale
- **THEN** the scale is read from the conferring skill's own per-occurrence `EffectPolicy.coefficient`
  and is not supplied through `event_context`

#### Scenario: The conferred set is derived, not chosen
- **WHEN** a conferral cast resolves
- **THEN** one grant is recorded for every skill the caster directly owns that passes the
  conferrability shape validation, each at that node's scale

#### Scenario: The growth-rate effect follows the data-derived scale rule
- **WHEN** a conferred growth-rate effect is applied
- **THEN** the same data-derived scale rule applies as for the conferral scale

### Requirement: The conferral store has a revocation primitive reachable from a skill
A deterministic-core revocation primitive SHALL exist in the same module as the conferral write. It
SHALL clear the target's recorded skill grants and remove every `conferred_growth_rate` buff instance
on that target, regardless of which source wrote them, leaving the target's own owned skills and every
other buff untouched.

#### Scenario: Revocation clears both halves of the conferral vocabulary
- **WHEN** the revocation primitive runs on a target holding grants from two different sources and an
  active `conferred_growth_rate` buff
- **THEN** the target holds no conferred grant, no `conferred_growth_rate` buff instance remains, and
  `effective_value()` returns the unmultiplied base for the affected traits

#### Scenario: Revocation leaves the target's own skills and unrelated buffs alone
- **WHEN** revocation runs on a target that owns its own multiplier passive and carries an unrelated
  active buff
- **THEN** the owned passive still folds into `effective_value()` and the unrelated buff instance is
  still active

#### Scenario: Revocation on a target with nothing conferred is a clean no-op
- **WHEN** revocation runs on a target holding no grant and no conferred growth-rate buff
- **THEN** it completes without raising and changes no stored state

#### Scenario: A rolled-back revocation restores both stores
- **WHEN** a resolution that revoked grants has a later pending effect fail, restoring the action
  snapshot
- **THEN** the target's `skill_grants` and buff store are byte-equal to their pre-action values

#### Scenario: Revocation is reachable from a skill
- **WHEN** a skill declares the `revoke_grants` effect prefix whose handler declares the
  `skill_grants` and `buffs` surfaces
- **THEN** revocation is reachable through it, so both writes ride the existing snapshot/restore face

#### Scenario: Revocation is total rather than selective
- **WHEN** a revocation is invoked
- **THEN** it takes no source filter and no skill filter

### Requirement: The disguise layer has an unconditional reveal primitive
A deterministic-core reveal primitive SHALL exist in the same module as the disguise write, clearing a
target's disguise layer and its placement record whenever the target carries a veil. It SHALL be
reachable from a skill through a bare, payload-free `reveal_disguise` effect prefix whose handler
declares the `traits` surface.

#### Scenario: A reveal lifts an authored veil
- **WHEN** a reveal resolves against a target carrying an authored disguise declaration
- **THEN** the target's disguise layer and placement record are cleared and `get_display_value`
  returns true values

#### Scenario: A reveal lifts a veil the verb placed
- **WHEN** a reveal resolves against a target whose veil was written by the veil verb during play
- **THEN** the target's disguise layer and placement record are cleared

#### Scenario: No weaker reveal can be expressed
- **WHEN** a skill declares any payload on the `reveal_disguise` prefix
- **THEN** the registry fails to load, because a reveal that stops at some veils cannot be spelled:
  every reveal that parses pierces any veil

#### Scenario: A reveal against an unveiled target is a clean no-op
- **WHEN** a reveal resolves against a target carrying no disguise layer
- **THEN** the action completes without raising and changes no stored state

#### Scenario: A reveal never exposes anything but the veil's removal
- **WHEN** any reveal resolves
- **THEN** the only state it touches is the target's disguise layer and placement record; no true
  trait value, identity field, or persona record is read or written

#### Scenario: A reveal takes no strength and branches on nothing
- **WHEN** a reveal resolves against any veil
- **THEN** the primitive takes NO strength argument and does not branch on any property of the veil it
  finds: this world admits exactly one grade of veil, because only the bloodline-gated divine mystery
  can write one, so a reveal either lifts what it finds or finds nothing

#### Scenario: A reveal never reads the placement record
- **WHEN** a reveal primitive runs
- **THEN** it does not read the placement record, which belongs to the veil verb's self-cast branch
  alone

#### Scenario: An unveiled-target reveal is reported, not rejected
- **WHEN** a reveal resolves against an unveiled target
- **THEN** it is a reported no-op rather than a rejection, so the attempt neither leaks the absence of
  a veil through a rejection reason nor fails the action

### Requirement: Identity-ineligible owned and conferred passive effects are inert
Passive queries SHALL apply identity qualification to directly owned and conferred skill effects before computing any trait or rule contribution. Reads SHALL create no handlers or persistent state, and unrestricted shared skills SHALL retain their existing behavior.

#### Scenario: Misconfigured passive has no influence
- **WHEN** an entity has an identity-ineligible owned or conferred multiplier/rule-table passive
- **THEN** effective traits and rule-table values equal the control without that passive

#### Scenario: Eligible reuse remains unchanged
- **WHEN** eligible character and monster owners read an unrestricted synthetic passive
- **THEN** both retain its existing effect and no persistent state changes
