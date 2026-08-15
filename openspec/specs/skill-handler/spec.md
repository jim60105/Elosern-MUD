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
below), returning the result. This function and every other function in `world/skills/handler.py`
SHALL NOT assign to `entity.traits.<any key>.value`,
`.base`, or `.mod`.
Duplicate occurrences of the same active skill key SHALL be resolution-idempotent rather than
applying its multiplier repeatedly. A single `SkillDef` SHALL NOT define more than one multiplier
for the same trait; encountering such a contradictory definition SHALL raise.

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

### Requirement: A skill can confer a scaled-down partial effect of another entity's skill (統御術)
`world/skills/handler.py` SHALL define a frozen `ConferredSkillGrant` dataclass (`source_key`,
`skill_key`, `scale`) and a read-only `SkillHandler.conferred_grants()` query over the additive
attribute `entity.db.skill_grants`, kept separate from `entity.db.skills`'s import-populated
`{"active": [...], "passive": [...]}` structure. `trait_keys` is no longer a stored field — it is
derived at resolution time from the referenced skill's own `parsed_effects` rather than duplicated in
the grant record. `effective_value()` SHALL fold every applicable source skill's matching multiplier
multiplied by the grant's fractional `scale` into its multiplier computation, in addition to the
entity's own owned skills. The `skill_owned` rule-table context builder (`world/rules/
combat_modifiers.py`, added by `skill-owned-rule-condition`) SHALL likewise fold a conferred grant's
scaled adjustment into its evaluated bundle when the grant references a skill whose parsed effect is a
`RuleTableEffect`. Conferral of a skill carrying a gate-type effect
(`ElementMasteryEffect`, `SexualMasteryEffect`, `DisguiseEffect`) SHALL raise
`EFFECT_RESOLUTION_FAILED` at cast-resolution time rather than silently
applying a no-op scale, and conferral of a skill carrying no continuous-valued
effect any grant consumer can resolve (no `StatMultiplyEffect` and no
`RuleTableEffect`) SHALL likewise be rejected instead of recording a silent
no-op grant. The write primitive SHALL live at
`world.rules.skill_effects.record_conferred_grant()` so `world/skills/` remains
outside the single-writer core.

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
  parsed effect is `ElementMasteryEffect`, `SexualMasteryEffect`, or `DisguiseEffect`
- **THEN** the attempt raises `EFFECT_RESOLUTION_FAILED` and no `ConferredSkillGrant` is recorded

#### Scenario: Conferring a skill without any continuous effect is rejected
- **WHEN** `record_conferred_grant` or its resolver-level caller attempts to confer a skill whose
  parsed effects include no `StatMultiplyEffect` and no `RuleTableEffect` (for example a damage-only
  or flavor-only skill)
- **THEN** the attempt raises `EFFECT_RESOLUTION_FAILED` and no `ConferredSkillGrant` is recorded

#### Scenario: Casting 統御術 during play is not implemented by this change
- **WHEN** the codebase added by this change is inspected for any code path that creates a
  `ConferredSkillGrant` as a result of resource checks, targeting, or an `ActionResolver`-style
  invocation
- **THEN** no such code path exists — this change generalizes the persistence primitive and its
  consumers only; the cast-time `_handle_confer_skill_partial` handler in `action.py` (already landed)
  is updated to stop passing `confer_trait_keys` in its event context, since the field no longer exists

### Requirement: The 狀態偽裝 skill's effect resolution can only ever touch disguised_stats, never entity.traits
`world/rules/skill_effects.py` SHALL define `apply_disguise_effect(entity, overrides)` as the
deterministic-core write for the `status_disguise` `SkillDef`, and this function SHALL contain no
reference to `entity.traits` anywhere in its definition. No module under `world/skills/` SHALL write
persistent state.

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
after the base list. `world/skills/handler.py` SHALL read the entity's sexual state through a
duck-typed `getattr(entity, "sexual", None)` and SHALL import nothing from `world.rules`, preserving
`universal-action-ownership`'s existing "world/skills/ does not depend on world/rules/" requirement.

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
