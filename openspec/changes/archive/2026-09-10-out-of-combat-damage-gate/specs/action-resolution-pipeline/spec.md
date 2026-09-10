## ADDED Requirements

### Requirement: A damaging action never resolves without a battlefield
`world/rules/action.py` SHALL declare `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`, and
`world/rules/player_messages.py` SHALL supply its Traditional Chinese player-facing line.
`ActionResolver`'s capability step SHALL reject a request with that reason when the resolved
`SkillDef`'s parsed `effects` carry at least one `world.skills.effects.DamageEffect` **and**
`request.context.battlefield is None`. The rejection SHALL occur before any resource is spent,
before `roll_d100()` is called, before any `PendingEffect` is staged, and before any world-clock
access, so a refused request touches no surface and persists nothing. The condition SHALL be
expressed as one shared predicate over the skill definition and the context, consumed by both
`ActionResolver` and `world/rules/action_preview.py`, so preview, combat-session submission
revalidation, and authoritative resolution cannot disagree.

The reason's name states the player-facing rule while the condition tests for the battlefield's
absence: from exploration the only way to obtain a battlefield is to open combat on a co-located
monster, so the two coincide, and the resolver stays free of any typeclass dependency.

Indirect hp movement SHALL NOT satisfy the condition: a skill carrying a `SexualDrainEffect` but no
`DamageEffect` is not a damaging action for this gate, matching
`overwhelm-threshold`'s `commanded_damage_reaches_enemy()` so both damage-shaped questions in the
codebase read the same definition.

#### Scenario: A damaging skill permitted outside combat is still refused without a battlefield
- **WHEN** `ActionResolver.resolve()` is called for a skill declaring `usable_out_of_combat=True`
  whose effects include `damage:<element>:<school>`, with a `RoomActionContext`
- **THEN** it returns `ActionResult(outcome="rejected", reason=RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)`,
  no resource is deducted, no roll is made, no effect is staged, and no clock is read

#### Scenario: The same skill resolves normally with a battlefield
- **WHEN** the identical request is resolved with a `BattlefieldActionContext` instead
- **THEN** the gate does not fire and resolution proceeds through the ordinary pipeline

#### Scenario: A non-damaging skill outside combat is unaffected
- **WHEN** a skill declaring `usable_out_of_combat=True` with no `DamageEffect` among its effects is
  resolved with a `RoomActionContext`
- **THEN** the gate does not fire and resolution proceeds exactly as before this change

#### Scenario: Indirect hp movement is not damage for this gate
- **WHEN** a skill declaring `usable_out_of_combat=True` whose effects include a drain that moves a
  target's pleasure into the caster's own hp, mp, and sp, but no `DamageEffect`, is resolved with a
  `RoomActionContext`
- **THEN** the gate does not fire

#### Scenario: The shared preview reports the same stable reason
- **WHEN** the shared preview query is asked about a damaging, out-of-combat-permitted skill with a
  `RoomActionContext`
- **THEN** it reports disabled with `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`, agreeing with
  `ActionResolver.preflight()` for the identical request

#### Scenario: The gate is evaluated per request, never from a catalog snapshot
- **WHEN** the gate's implementation is inspected
- **THEN** its condition is computed from the resolved `SkillDef`'s own effects and the request's own
  context, with no enumeration of registry keys and no dependence on how many skills currently
  declare `usable_out_of_combat=True`

### Requirement: The out-of-combat gates fire in a fixed, specified order
`ActionResolver`'s capability step SHALL evaluate the `usable_out_of_combat` gate **before** the
damaging-action gate. A skill that does not declare `usable_out_of_combat` SHALL therefore continue
to reject with `RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT` outside combat, whether or not it
carries a `DamageEffect`; `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET` SHALL be reachable only for
skills the registry does permit outside combat. `world/rules/action_preview.py` SHALL evaluate the
two conditions in the same order.

#### Scenario: An unflagged damage skill still reports the flag rejection
- **WHEN** a skill carrying a `DamageEffect` and declaring `usable_out_of_combat=False` is resolved
  with a `RoomActionContext`
- **THEN** the reason is `RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT`, not
  `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`

#### Scenario: Preview agrees with resolve on which of the two reasons applies
- **WHEN** the shared preview and `ActionResolver.preflight()` are both asked about an unflagged
  damage skill, and then about a flagged one, each with a `RoomActionContext`
- **THEN** both report `SKILL_NOT_USABLE_OUT_OF_COMBAT` for the first and
  `DAMAGE_REQUIRES_MONSTER_TARGET` for the second

## MODIFIED Requirements

### Requirement: Neither ActionResolver nor targeting branches on combat state
`world/rules/action.py` and `world/rules/targeting.py` SHALL contain no conditional that distinguishes
combat from non-combat behavior other than exactly two explicitly marked gates: the
`usable_out_of_combat` gate, and the damaging-action gate that rejects a `DamageEffect`-carrying
skill when `request.context.battlefield is None`. Both SHALL be marked as such at their sites, and
both SHALL read the context's battlefield rather than any combat-state token. All other
combat-vs-non-combat behavior SHALL be expressed entirely through which concrete `ActionContext`
implementation the caller supplies.

#### Scenario: A source scan finds no undeclared combat-state branch
- **WHEN** `world/rules/action.py`, `world/rules/targeting.py`, and `world/rules/event_log.py` are
  scanned for the literal tokens `in_combat`, `is_combat`, `combat_state`, and
  `isinstance(context, Battlefield`
- **THEN** none of the tokens appear anywhere in these three files

#### Scenario: Exactly the two sanctioned gates exist
- **WHEN** `world/rules/action.py` and `world/rules/targeting.py` are inspected for conditionals
  reading `context.battlefield`
- **THEN** the only such conditionals distinguishing combat from non-combat behavior are the
  `usable_out_of_combat` gate and the damaging-action gate, each marked at its site

#### Scenario: A battlefield defeat stages events and planners only
- **WHEN** a battlefield-backed action reduces a resolved `Monster` with a known `threat_tier` from
  positive HP to zero
- **THEN** the action stages the defeat EventLog entry (carrying `monster_tier`) and the
  event-effect planners derived from it, and no progression effect of any kind

#### Scenario: No public callable takes a combat-shaped parameter
- **WHEN** every public callable in `action.py`, `targeting.py`, and `event_log.py` has its signature
  inspected
- **THEN** no parameter is named `in_combat`, `combat_state`, `turn`, or `is_combat`

#### Scenario: Identical code, different ActionContext, different faction outcome
- **WHEN** `ActionResolver.resolve()` is called twice with byte-identical `ActionRequest`s (same actor,
  same `skill_key` whose `SkillDef.faction_constraint` is `FactionConstraint.SELF_ONLY`) differing only in
  which `ActionContext` is supplied — once with `RoomActionContext`, once with a test double whose
  `relation_to()` reports `Relation.SELF` for the same target
- **THEN** the `RoomActionContext` call rejects with `RejectReason.TARGET_FACTION_FORBIDDEN` and the
  test-double call succeeds, with no difference in `action.py`'s or `targeting.py`'s executed source
  between the two calls
