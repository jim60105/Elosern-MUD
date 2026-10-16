# Spec Delta

## MODIFIED Requirements

### Requirement: A skill aimed at a co-located hostile monster from exploration always initiates combat
`world/rules/combat_initiation.py` SHALL provide `field_combat_target(actor, target)`, returning
`target` when it is a living `Monster` in the actor's own room and `None` otherwise. It SHALL also
provide `initiate_field_combat(actor, skill_key, target, scale=1.0)`, which SHALL open one combat
session and seed the named skill as the actor's opening draft entry, **whatever that skill does**.

#### Scenario: A damaging skill aimed at a room monster opens combat
- **WHEN** `initiate_field_combat()` is called for a damage-carrying skill and a living `Monster` in
  the actor's room
- **THEN** a hostile session is persisted and the skill is saved as the actor's opening selection

#### Scenario: A non-damaging skill aimed at a room monster also opens combat
- **WHEN** `initiate_field_combat()` is called for a buff, a heal, a cleanse, a debuff-only skill, or
  a sexual act, aimed at a living `Monster` in the actor's room
- **THEN** a hostile session is persisted, the skill is saved as the actor's opening selection, and
  exactly one ordinary round runs only once all required actors confirm; the encounter never compresses

#### Scenario: Aiming a heal at a monster starts a fight, by design
- **WHEN** `initiate_field_combat()` is called for a healing skill aimed at a room monster
- **THEN** combat starts, the selected heal waits for a complete draft, then the monster is healed by the opening action and the round proceeds — this
  is the accepted consequence of the target being the discriminator, not a special case

#### Scenario: A non-monster target is not a field-combat target
- **WHEN** `field_combat_target()` is called with an NPC, a companion, the actor itself, an object, a
  monster in another room, or a monster at zero hp
- **THEN** it returns `None`

#### Scenario: Hostility is the Monster type check, not a second notion
- **WHEN** `field_combat_target()` decides whether a target is hostile
- **THEN** hostility is expressed exactly as `engage()` already expresses it — being a `Monster`
  instance — so no second notion of hostility is introduced

#### Scenario: Damage presence settles the encounter, never gates combat
- **WHEN** whether the opening skill carries a `DamageEffect` is considered
- **THEN** its presence or absence decides neither whether combat starts nor any compression; the opening selection seeds the same interactive draft

#### Scenario: The initiation returns the shared submission result shape
- **WHEN** `initiate_field_combat()` returns
- **THEN** the result has the same shape as `submit_player_action()`'s — a rejection, pending-draft progress, an ordinary
  round, or a terminal outcome — so callers share `world/rules/combat_result.py`'s rendering

### Requirement: A SINGLE skill opens against the named monster and an AREA skill opens against every living hostile monster in the room
`initiate_field_combat()` SHALL select the session's enemy line-up from the skill's `TargetSpec`: a
`SINGLE` skill SHALL open against the named monster alone, and an `AREA` skill SHALL open against
every living `Monster` in the actor's room, resolved into an explicit list of concrete targets in
deterministic order. It SHALL NOT pass an AREA shorthand, because the engagement persists exactly
that list as the session's `enemy_ids` and the opening's own seed path takes concrete participants.

#### Scenario: An AREA opening engages the whole room
- **WHEN** `initiate_field_combat()` is called with an `AREA` skill and one of three living monsters
  in the room
- **THEN** the persisted session's `enemy_ids` contains all three

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
rather than stranding the actor in a fight that never started. A database rollback alone SHALL NOT
be relied on to undo engagement, because engagement leaves state the rollback cannot reach.

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
- **WHEN** a field initiation completes a valid solo draft whose ordinary opening round ends the fight
- **THEN** the terminal settlement's effects commit, its post-commit work runs once on the outer
  commit, and its observability events are each logged exactly once

#### Scenario: The nested transaction degrades to a savepoint
- **WHEN** the shared submission body runs inside `initiate_field_combat()`'s outer
  `transaction.atomic()`
- **THEN** the nested `transaction.atomic()` inside that body degrades to a savepoint, and every
  `transaction.on_commit` callback staged inside it — the round boundary event and the terminal
  settlement's post-commit work — fires on this outer commit, as that body's contract already states

#### Scenario: The failure path reverses skip-safety registration explicitly
- **WHEN** the opening action fails after engagement registered participants with skip safety
- **THEN** the process-memory registration performed during engagement is explicitly reversed on the
  failure path by unregistering the same participant identities the engagement registered

#### Scenario: Engagement's attribute-cache writes are snapshot and restored
- **WHEN** engagement writes `actor.db.active_combat` and clears `actor.db.dialogue_session` and the
  Evennia idmapper cache is not transaction-aware, so a rolled-back transaction leaves both readable
  at their post-engagement values in process
- **THEN** `initiate_field_combat()` snapshots those attribute surfaces **before** `engage_group()`
  runs and restores them on the failure path, following the established precedent of
  `world/rules/cast_settlement.py::_restore_settlement_state` and
  `world/rules/combat_session.py::_restore_round_touched`

#### Scenario: The submission body's own snapshot is not relied on
- **WHEN** deciding what restores the attribute surfaces after a rolled-back initiation
- **THEN** the shared submission body's own `_snapshot_round_touched()` is not relied on: it snapshots
  at its own entry, which in this flow is already after engagement wrote those values, so its
  restoration would reinstate the engaged session rather than the pre-engagement absence

#### Scenario: Multi-actor opening commits its draft without actions
- **WHEN** engagement and the initiating entry commit while companions still need commands
- **THEN** the session and seed persist together, no action effects or round time have run, and later round failures preserve this committed draft

### Requirement: A committed field initiation emits one boundary event
`initiate_field_combat()` SHALL emit one `field_combat_initiated` info event through the
`world.observability` facade, with `char`, `room`, `tick`, `skill`, `enemy_count`, and `opening`
(`"draft"` for a waiting seed, or `"round"` when a complete solo draft resolves) in its context. It SHALL be emitted via `transaction.on_commit` on the
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

