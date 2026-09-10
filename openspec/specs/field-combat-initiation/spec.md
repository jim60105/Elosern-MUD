# field-combat-initiation Specification

## Purpose

Turn one exploration cast aimed at a living, co-located hostile monster into that combat's opening action, with target-based routing, candidate-battlefield validation, and a single failure boundary spanning engagement and the opening action.

## Requirements

### Requirement: A skill aimed at a co-located hostile monster from exploration always initiates combat
`world/rules/combat_initiation.py` SHALL provide `field_combat_target(actor, target)`, returning
`target` when it is a living `Monster` in the actor's own room and `None` otherwise. Hostility SHALL
be expressed exactly as `engage()` already expresses it — being a `Monster` instance — so no second
notion of hostility is introduced.

`world/rules/combat_initiation.py` SHALL provide
`initiate_field_combat(actor, skill_key, target, scale=1.0)`, which SHALL open one combat session and
resolve the named skill as the actor's first action, **whatever that skill does**. The presence or
absence of a `DamageEffect` SHALL NOT decide whether combat starts; it decides only whether the
encounter is then settled in one shot, which `submit_opening_action()` determines. The function SHALL
return the same result shape as `submit_player_action()` — a rejection, an ordinary round, or a
terminal outcome — so callers share `world/rules/combat_result.py`'s rendering.

#### Scenario: A damaging skill aimed at a room monster opens combat
- **WHEN** `initiate_field_combat()` is called for a damage-carrying skill and a living `Monster` in
  the actor's room
- **THEN** a hostile session is persisted and the skill resolves as the actor's opening action

#### Scenario: A non-damaging skill aimed at a room monster also opens combat
- **WHEN** `initiate_field_combat()` is called for a buff, a heal, a cleanse, a debuff-only skill, or
  a sexual act, aimed at a living `Monster` in the actor's room
- **THEN** a hostile session is persisted, the skill resolves as the actor's opening action, and
  exactly one ordinary round runs — the encounter is not settled in one shot

#### Scenario: Aiming a heal at a monster starts a fight, by design
- **WHEN** `initiate_field_combat()` is called for a healing skill aimed at a room monster
- **THEN** combat starts, the monster is healed by the opening action, and the round proceeds — this
  is the accepted consequence of the target being the discriminator, not a special case

#### Scenario: A non-monster target is not a field-combat target
- **WHEN** `field_combat_target()` is called with an NPC, a companion, the actor itself, an object, a
  monster in another room, or a monster at zero hp
- **THEN** it returns `None`

### Requirement: A damaging skill aimed at anything other than a co-located hostile monster is rejected at the entry
`initiate_field_combat()`'s caller SHALL reject a cast whose skill carries a
`world.skills.effects.DamageEffect` and whose target is not a living co-located `Monster`, with
`RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`. The rejection SHALL occur before any resource is
spent, before any roll, before any session is persisted, and before any world-clock access. A
non-damaging skill aimed at a non-monster SHALL continue to route through
`world/rules/cast_settlement.settle_out_of_combat_cast()` with behaviour unchanged, so sexual acts
and other non-damaging skills remain usable on NPCs exactly as before.

#### Scenario: A damage skill aimed at an NPC is refused with nothing spent
- **WHEN** a player casts a damage-carrying skill at a co-located NPC from exploration
- **THEN** the result is a rejection carrying `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`, no mp or
  sp is deducted, no session is persisted, no roll is made, and the world clock is unchanged

#### Scenario: A sexual act aimed at an NPC is unchanged
- **WHEN** a player casts a resistible sexual act at a co-located NPC from exploration
- **THEN** it routes through `settle_out_of_combat_cast()`, its out-of-combat coercion scan runs, and
  command time is charged exactly as before this change

#### Scenario: A non-damaging utility skill on the actor is unchanged
- **WHEN** a player casts a self-targeted or no-target non-damaging skill from exploration
- **THEN** it routes through `settle_out_of_combat_cast()` with behaviour identical to before this
  change

### Requirement: The skill's out-of-combat availability is checked explicitly, before anything else
`initiate_field_combat()` SHALL reject a skill whose `SkillDef.usable_out_of_combat` is `False` with
`RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT`, and SHALL perform this check before constructing the
candidate battlefield and before any other validation it owns. This check SHALL be explicit rather
than delegated, because the deliberate use of a battlefield-backed context for validation means
`world/rules/action.py`'s own `usable_out_of_combat` gate would pass.

#### Scenario: A skill not permitted outside combat is refused
- **WHEN** `initiate_field_combat()` is called for a skill declaring `usable_out_of_combat=False`,
  aimed at a valid room monster
- **THEN** the result is a rejection carrying `RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT`, no
  session is persisted, and nothing is spent

#### Scenario: flee cannot open a fight
- **WHEN** `initiate_field_combat()` is called with the reserved flee skill key
- **THEN** it is rejected for not being usable outside combat, and no session is persisted

#### Scenario: The availability check precedes candidate construction
- **WHEN** `initiate_field_combat()`'s implementation is inspected
- **THEN** the `usable_out_of_combat` check appears before the candidate battlefield is built, so its
  answer cannot be masked by a later validation

### Requirement: Validation runs against a candidate battlefield that is never persisted, under a combat context
`initiate_field_combat()` SHALL build a candidate `Battlefield` by passing an unpersisted
`CombatSessionRecord` to `reconstruct_battlefield()`, and SHALL validate the submission against it
using a `BattlefieldActionContext` through `world/rules/action_preview.revalidate_submission()` and
`ActionResolver.preflight()`. It SHALL NOT validate under a `RoomActionContext`, which reports every
co-located non-self entity as `Relation.ALLY` and would therefore evaluate faction and range against
a false world view. A rejection at this stage SHALL return before `engage_group()` is called, so no
session is persisted, no resource is spent, and no world time passes.

#### Scenario: A preflight rejection persists no session
- **WHEN** the candidate validation rejects — insufficient resources, an action-blocking buff, a
  lineage-ineligible skill, or a target-shape violation
- **THEN** the result carries that rejection's stable reason, no `CombatSessionRecord` is persisted,
  no battlefield is registered with skip safety, no resource is deducted, and the world clock is
  unchanged

#### Scenario: The candidate battlefield matches the session that would be created
- **WHEN** a candidate battlefield is built for a set of targets and `engage_group()` is then called
  for the identical targets
- **THEN** the candidate's roster keys and team membership equal those of the reconstructed session's
  battlefield

#### Scenario: Enemy relations are correct during validation
- **WHEN** the candidate validation evaluates a skill whose `faction_constraint` distinguishes
  enemies from allies against a room monster
- **THEN** the monster is reported as an enemy, not an ally, because the validation context is
  battlefield-backed

### Requirement: A SINGLE skill opens against the named monster and an AREA skill opens against every living hostile monster in the room
`initiate_field_combat()` SHALL select the session's enemy line-up from the skill's `TargetSpec`: a
`SINGLE` skill SHALL open against the named monster alone, and an `AREA` skill SHALL open against
every living `Monster` in the actor's room, resolved into an explicit list of concrete targets in
deterministic order. It SHALL NOT pass an AREA shorthand, because
`overwhelm.commanded_damage_reaches_enemy()` reads concrete roster keys.

#### Scenario: An AREA opening engages the whole room
- **WHEN** `initiate_field_combat()` is called with an `AREA` skill and one of three living monsters
  in the room
- **THEN** the persisted session's `enemy_ids` contains all three, and the overwhelm verdict is
  computed against the whole opposing team

#### Scenario: A SINGLE opening engages one monster
- **WHEN** `initiate_field_combat()` is called with a `SINGLE` skill in a room holding three living
  monsters
- **THEN** the persisted session's `enemy_ids` contains only the named monster

#### Scenario: An AREA opening in a single-monster room is not special-cased
- **WHEN** `initiate_field_combat()` is called with an `AREA` skill in a room holding one monster
- **THEN** the session opens against that monster with no distinct code path

### Requirement: Session creation and the opening action share one failure boundary
`initiate_field_combat()` SHALL run `engage_group()` and `submit_opening_action()` inside one
`transaction.atomic()` it owns, so a failure in the opening action rolls back the session's creation
rather than stranding the actor in a fight that never started. The
nested `transaction.atomic()` inside the shared submission body SHALL degrade to a savepoint, and
every `transaction.on_commit` callback staged inside it — the round boundary event and the terminal
settlement's post-commit work — SHALL fire on this outer commit, as that body's contract already
states.

A database rollback alone SHALL NOT be relied on to undo engagement, because engagement leaves two
kinds of state the rollback cannot reach:

1. **Process-memory registration.** The skip-safety registration performed during engagement SHALL
   be explicitly reversed on the failure path by unregistering the same participant identities the
   engagement registered.
2. **Evennia attribute caches.** Engagement writes `actor.db.active_combat` and clears
   `actor.db.dialogue_session`. The Evennia idmapper cache is not transaction-aware, so a rolled-back
   transaction leaves both readable at their post-engagement values in process.
   `initiate_field_combat()` SHALL therefore snapshot those attribute surfaces **before**
   `engage_group()` runs and restore them on the failure path, following the established precedent of
   `world/rules/cast_settlement.py::_restore_settlement_state` and
   `world/rules/combat_session.py::_restore_round_touched`. The shared submission body's own
   `_snapshot_round_touched()` SHALL NOT be relied on for this: it snapshots at its own entry, which
   in this flow is already after engagement wrote those values, so its restoration would reinstate
   the engaged session rather than the pre-engagement absence.

#### Scenario: A raising opening action leaves no trace
- **WHEN** `submit_opening_action()` raises after `engage_group()` persisted the session
- **THEN** no `CombatSessionRecord` remains persisted, no battlefield remains registered with skip
  safety, no entity surface reflects the opening action, the world clock is unchanged, and no
  boundary event is logged

#### Scenario: A rolled-back initiation leaves no session readable in process
- **WHEN** `submit_opening_action()` raises after engagement, and `read_session(actor)` is then
  called in the same process without any reload
- **THEN** it returns `None` — `actor.db.active_combat` reads as its pre-engagement value, not the
  engaged record the rolled-back transaction wrote

#### Scenario: A rolled-back initiation does not retire a dialogue session
- **WHEN** the actor holds a dialogue session, `initiate_field_combat()` engages and then its opening
  action raises
- **THEN** `actor.db.dialogue_session` reads in process as the session the actor held before the
  attempt, not as cleared

#### Scenario: A committed initiation does retire the dialogue session
- **WHEN** the actor holds a dialogue session and `initiate_field_combat()` commits
- **THEN** the dialogue session is retired exactly as ordinary engagement retires it

#### Scenario: A field initiation that ends the fight still settles exactly once
- **WHEN** a field initiation resolves a compressed encounter that ends the fight
- **THEN** the terminal settlement's effects commit, its post-commit work runs once on the outer
  commit, and its observability events are each logged exactly once

### Requirement: The opening cast charges combat time, never command time
A field-combat initiation SHALL NOT charge `AdvanceSource.COMMAND` world time for the opening cast.
The action's time cost SHALL be accumulated by the session and charged once as combat time by the
terminal settlement, because the cast is the fight's first round and charging both sources would
double-bill it.

#### Scenario: An opening cast advances no command time
- **WHEN** a field initiation resolves one opening round without ending the fight
- **THEN** no `AdvanceSource.COMMAND` advance occurs for that cast, and the session's accumulated
  round time is unsettled until the terminal outcome

#### Scenario: Combat time settles once at the terminal outcome
- **WHEN** a field initiation's fight concludes
- **THEN** the world clock advances exactly once for the accumulated combat time, with no separate
  command-time charge attributable to the opening cast

### Requirement: A committed field initiation emits one boundary event
`initiate_field_combat()` SHALL emit one `field_combat_initiated` info event through the
`world.observability` facade, with `char`, `room`, `tick`, `skill`, `enemy_count`, and `opening`
(`"round"` or `"overwhelm"`) in its context. It SHALL be emitted via `transaction.on_commit` on the
outer transaction, so a rolled-back initiation leaves no record, and the callback SHALL perform no
computation of its own.

#### Scenario: A committed initiation logs exactly one event
- **WHEN** a field initiation commits
- **THEN** exactly one `field_combat_initiated` event is logged, its `opening` value matches the
  dispatch actually taken, and its `enemy_count` matches the session's engaged monster count

#### Scenario: A rejected initiation logs nothing
- **WHEN** a field initiation is rejected at the availability check, the target check, or the
  candidate validation
- **THEN** no `field_combat_initiated` event is logged

### Requirement: The command routes an exploration cast by target, and its documentation says so
`commands/action.py`'s out-of-combat cast path SHALL consult `field_combat_target()` before choosing
a route: a living co-located `Monster` SHALL route to `initiate_field_combat()` and render through
`world/rules/combat_result.settle_to_messages()`, and anything else SHALL keep the existing
`settle_out_of_combat_cast()` route. `docs/game/commands.md` and
`docs/game/command-reference.md` SHALL be updated in this change to describe `cast`'s behaviour in
exploration: aiming at a room monster starts combat with that skill as the opening action, a damaging
skill cannot be aimed at anything else, and a non-damaging skill aimed elsewhere behaves as before.

#### Scenario: The command routes a monster-targeted cast into combat
- **WHEN** a player runs the cast command from exploration naming a living co-located monster
- **THEN** the command routes through `initiate_field_combat()` and renders the combat result lines

#### Scenario: The command keeps the existing route for everything else
- **WHEN** a player runs the cast command from exploration with a non-monster target, a self target,
  or no target, using a non-damaging skill
- **THEN** the command routes through `settle_out_of_combat_cast()` and renders exactly as before

#### Scenario: The command documentation describes both routes
- **WHEN** `docs/game/commands.md` and `docs/game/command-reference.md` are inspected
- **THEN** each describes the monster-target route, the damaging-skill restriction, and the unchanged
  non-damaging route, and the command documentation contract test passes
