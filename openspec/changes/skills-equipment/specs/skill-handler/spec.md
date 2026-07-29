## ADDED Requirements

### Requirement: SkillHandler is accessible from a LivingEntity via a facade property
`LivingEntity` SHALL expose a `skill_handler` property returning a `SkillHandler` instance bound to
that entity, reading the raw `{"active": [...], "passive": [...]}` structure change 4's loader already
writes to `entity.skills` without requiring any change to how that attribute is populated or mounted.

#### Scenario: skill_handler reads the raw skills dict change 4's loader writes
- **WHEN** `entity.skills` is `{"active": ["fire_ball"], "passive": ["defense_instinct"]}`
- **THEN** `entity.skill_handler.owned_keys()` returns a list containing both `"fire_ball"` and
  `"defense_instinct"`

#### Scenario: skill_handler tolerates an entity never populated by the import loader
- **WHEN** `entity.skills` is `None` (an entity never run through change 4's loader)
- **THEN** `entity.skill_handler.owned_keys()` returns an empty list rather than raising

#### Scenario: Assigning entity.skills directly continues to work unmodified
- **WHEN** code assigns `entity.skills = {"active": [...], "passive": [...]}` directly, the same way
  change 4's `instantiate_character()` already does
- **THEN** the assignment succeeds with no error, and a subsequently constructed `entity.skill_handler`
  reflects the newly assigned data

### Requirement: effective_value is the sole resolution-time multiplier application point and never writes to entity.traits
`SkillHandler.effective_value(trait_key)` SHALL compute a derived value by reading
`entity.traits.<trait_key>.value` (the stored base value) and multiplying it by every currently-owned
active skill's matching `stat_multiply:<trait_key>:<multiplier>` effect and every applicable conferred
grant's `scale` (see the conferral requirement below), returning the result. This function and every
other function in `world/skills/handler.py` SHALL NOT assign to `entity.traits.<any key>.value`,
`.base`, or `.mod`.

#### Scenario: effective_value multiplies the base trait value by an owned skill's multiplier
- **WHEN** an entity's `entity.traits.atk_phys.value` is `88` and the entity owns the
  `body_enhancement_extreme` skill (`stat_multiply:atk_phys:1000`) as active
- **THEN** `entity.skill_handler.effective_value("atk_phys")` returns `88000`

#### Scenario: effective_value never mutates the stored trait value
- **WHEN** `effective_value("atk_phys")` is called on any entity
- **THEN** `entity.traits.atk_phys.value` is exactly the same before and after the call

#### Scenario: No function in world/skills/handler.py assigns to entity.traits
- **WHEN** `world/skills/handler.py`'s source is inspected
- **THEN** it contains no assignment expression targeting `entity.traits.<anything>`, `.base`, or
  `.mod` anywhere in the module

#### Scenario: An entity with no matching multiplier skill returns the unmultiplied base value
- **WHEN** an entity owns no skill whose `effects` include a `stat_multiply:atk_phys:*` entry
- **THEN** `entity.skill_handler.effective_value("atk_phys")` returns exactly
  `entity.traits.atk_phys.value`

#### Scenario: Every static trait's stored base value stays within its documented band regardless of effective_value calls
- **WHEN** `effective_value()` is called any number of times, for any trait, on any entity
- **THEN** `entity.traits.atk_phys`, `agility`, and `defense`'s stored base values remain within the
  exact `StaticBand`/`static_band` range documented for that entity's race or monster tier — the same
  invariant change 3's D-7 established for construction, now unbroken by this change's
  resolution-time computation too

### Requirement: A skill can confer a scaled-down partial effect of another entity's skill (統御術)
`world/skills/handler.py` SHALL define a frozen `ConferredSkillGrant` dataclass (`source_key`,
`skill_key`, `trait_keys`, `scale`) and `SkillHandler.conferred_grants()`/`grant_conferred()` methods
operating on a new, additive attribute `entity.db.skill_grants`. `effective_value()` SHALL fold every
applicable grant's `scale` into its multiplier computation, in addition to the entity's own owned
skills.

#### Scenario: A conferred grant applies its own scale, independent of the source skill's own multiplier
- **WHEN** an entity has no `body_enhancement` skill of its own but has a `ConferredSkillGrant` with
  `skill_key="body_enhancement"`, `trait_keys=("atk_phys", "agility", "defense")`, `scale=0.1` (a
  ×10 partial effect of a ×100 source skill), and a base `atk_phys` of `60`
- **THEN** `entity.skill_handler.effective_value("atk_phys")` returns `600` — a ×10 multiplier — not
  `6000` (which would be the source's own full ×100)

#### Scenario: grant_conferred records a grant without performing any ownership or resource check
- **WHEN** `entity.skill_handler.grant_conferred("elosia", "body_enhancement", ("atk_phys",
  "agility", "defense"), 0.1)` is called
- **THEN** `entity.skill_handler.conferred_grants()` includes a `ConferredSkillGrant` with exactly
  those field values, and no exception is raised regardless of whether `"elosia"` is a real,
  reachable, or currently-owning entity

#### Scenario: Casting 統御術 during play is not implemented by this change
- **WHEN** the codebase added by this change is inspected for any code path that creates a
  `ConferredSkillGrant` as a result of resource checks, targeting, or an `ActionResolver`-style
  invocation
- **THEN** no such code path exists — `grant_conferred()` is a plain, unconditional data write, and
  the cast-time creation flow is a declared seam for change 8, not built here

### Requirement: The 狀態偽裝 skill's effect resolution can only ever touch disguised_stats, never entity.traits
`world/skills/handler.py` SHALL define `apply_disguise_effect(entity, overrides)` as the complete
effect-resolution body for the `status_disguise` `SkillDef`, and this function SHALL contain no
reference to `entity.traits` anywhere in its definition.

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

### Requirement: No public function in world/skills/ branches on combat state
Every public callable in `world/skills/handler.py` and `world/skills/equipment.py` SHALL accept no
parameter representing whether the entity is currently in combat, and SHALL contain no conditional
branch keyed on such a concept — matching design doc §5.2's statement that "a skill does not know
whether it is in combat."

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
