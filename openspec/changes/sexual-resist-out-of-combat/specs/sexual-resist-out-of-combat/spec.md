## ADDED Requirements

### Requirement: An out-of-combat forced sexual act applies the same affinity penalty as an in-combat one
`world/rules/cast_settlement.py` SHALL provide `_scan_out_of_combat_sexual_coercion(actor, targets,
event_log) -> tuple[str, ...]`, scanning one resolved out-of-combat cast's `EventLog.entries` for
`EventEntry` records with `kind == "sexual_resist"`. For every such entry whose `data` is a mapping with
`data["resisted"] is False` and `data["auto_comply"] is False` — a forced outcome — and whose `target`
key resolves against the cast's own `targets` list to an `NPC`, it SHALL apply `-sexual_forced_penalty`
through `world.rules.affinity.apply_affinity_change(target, actor, AffinitySource.SEXUAL_FORCED, ...)`,
the same sole writer, source, and rulebook-configured penalty magnitude `sexual-resist-turn-cost`'s
in-combat `_scan_sexual_coercion` already uses. An entry recording compliance (`resisted is False,
auto_comply is True`, rolled or automatic) or a successful resistance (`resisted is True`) SHALL apply
no penalty.

#### Scenario: A forced out-of-combat act applies exactly one penalty
- **WHEN** an out-of-combat cast's resolved `EventLog` contains one `kind == "sexual_resist"` entry with
  `data = {"resisted": False, "auto_comply": False, "roll": <int>}` targeting an `NPC` present in the
  cast's target list
- **THEN** `_scan_out_of_combat_sexual_coercion` applies exactly one `-sexual_forced_penalty` delta
  through `apply_affinity_change` with `AffinitySource.SEXUAL_FORCED`

#### Scenario: A complied-with out-of-combat act applies no penalty
- **WHEN** the resolved `EventLog` contains one `kind == "sexual_resist"` entry with
  `data = {"resisted": False, "auto_comply": True, "roll": None}`
- **THEN** `_scan_out_of_combat_sexual_coercion` applies no affinity penalty for that entry

#### Scenario: A successfully resisted out-of-combat act applies no penalty
- **WHEN** the resolved `EventLog` contains one `kind == "sexual_resist"` entry with
  `data = {"resisted": True, "auto_comply": False, "roll": <int>}`
- **THEN** `_scan_out_of_combat_sexual_coercion` applies no affinity penalty for that entry

#### Scenario: The penalty magnitude and source match the in-combat consequence exactly
- **WHEN** the same forced outcome is produced once in combat (through `_scan_sexual_coercion`) and once
  out of combat (through `_scan_out_of_combat_sexual_coercion`) against an equivalent `NPC` target
- **THEN** both calls apply the identical `-sexual_forced_penalty` delta read from `get_config()` through
  `AffinitySource.SEXUAL_FORCED`, with no separate out-of-combat magnitude or source

### Requirement: The scan resolves forced targets against the cast's own target list, with one independent penalty per target
`_scan_out_of_combat_sexual_coercion` SHALL resolve each qualifying entry's `target` key against the
`targets` list supplied to it (the same explicit list `ActionRequest.targets` carried into
`ActionResolver.resolve`), not against any `Battlefield` roster. A cast whose resolved targets include
more than one forced `NPC` (an `AREA`-target resistible act cast out of combat with an explicit
multi-target list) SHALL apply one independent penalty per forced target.

#### Scenario: A multi-target out-of-combat cast penalizes each forced NPC independently
- **WHEN** an out-of-combat `AREA`-target resistible cast's resolved `EventLog` contains two
  `kind == "sexual_resist"` entries, both forced, targeting two different `NPC`s present in the cast's
  target list
- **THEN** `_scan_out_of_combat_sexual_coercion` applies two separate `-sexual_forced_penalty` deltas,
  one per target

#### Scenario: A forced entry targeting a non-NPC applies no penalty
- **WHEN** a `kind == "sexual_resist"` entry's `target` key resolves, against the cast's target list, to
  a `PlayerCharacter` or a `Monster` rather than an `NPC`
- **THEN** `_scan_out_of_combat_sexual_coercion` applies no penalty for that entry and does not call
  `apply_affinity_change` for it

#### Scenario: A target key absent from the cast's target list applies no penalty
- **WHEN** a `kind == "sexual_resist"` entry's `target` key does not match any entity in the `targets`
  list supplied to the scan
- **THEN** `_scan_out_of_combat_sexual_coercion` applies no penalty for that entry and does not raise

### Requirement: The coercion scan runs inside the out-of-combat settlement's outer transaction and rolls back on failure
`world/rules/cast_settlement.py::settle_out_of_combat_cast` SHALL call
`_scan_out_of_combat_sexual_coercion(request.actor, request.targets, result.event_log)` inside the same
outer `transaction.atomic()` that wraps `ActionResolver.resolve` and the clock advance, immediately after
a successful resolution and before the clock advance. A rejected resolution SHALL never invoke the scan.
Before applying any penalty, the scan SHALL snapshot the touched `NPC` targets' `relations_data` and the
actor's party-membership surfaces; if applying a penalty or its resulting auto-leave raises, the scan
SHALL restore those snapshotted surfaces (through `world.rules.affinity.restore_relations_surfaces` and
`world.rules.party.restore_membership_surfaces`) before re-raising, so the failure propagates to
`settle_out_of_combat_cast`'s own outer rollback with no in-process cache left holding a rolled-back
value.

#### Scenario: A successful out-of-combat forced cast commits the penalty with the rest of the settlement
- **WHEN** a player casts a resistible sexual act on a present `NPC` out of combat and the target's
  resist roll fails (a forced outcome), and the settlement succeeds
- **THEN** after `settle_out_of_combat_cast` returns, the target's affinity toward the actor has
  decreased by `sexual_forced_penalty`, durably persisted alongside the cast's other committed effects

#### Scenario: A rejected out-of-combat cast never invokes the scan
- **WHEN** `ActionResolver.resolve` rejects the out-of-combat cast request
- **THEN** `_scan_out_of_combat_sexual_coercion` is never called and no affinity change occurs

#### Scenario: A penalty-application failure restores the pre-cast relations and party state
- **WHEN** `apply_affinity_change` or the auto-leave it triggers raises inside the scan's own nested
  transaction, after at least one forced target was already penalized
- **THEN** every touched `NPC`'s `relations_data` and the actor's party-membership surfaces are restored
  to their pre-cast, in-process values before the exception propagates, and the outer
  `settle_out_of_combat_cast` transaction rolls back the entire cast (no partial resolution, practice
  award, or clock advance persists)

### Requirement: An out-of-combat forced act's party auto-leave notification reaches the player
When a penalty applied by `_scan_out_of_combat_sexual_coercion` drops a companion `NPC`'s affinity below
the party invite threshold, the resulting auto-leave notification line SHALL be returned from
`settle_out_of_combat_cast` (as `CastSettlement.notifications`) and SHALL be sent to the casting player
by `commands/action.py::CmdCast._cast_out_of_combat` after a successful cast, in addition to the cast's
own rendered `EventLog`.

#### Scenario: An out-of-combat forced act that triggers auto-leave notifies the player
- **WHEN** a forced out-of-combat sexual act on a companion `NPC` drops that companion's affinity below
  the invite threshold, ending the party
- **THEN** the casting player receives the auto-leave notification line in addition to the cast's
  rendered `EventLog`, and the companion's `db.party_member` state reflects the party having ended

#### Scenario: A forced act that does not trigger auto-leave sends no extra notification
- **WHEN** a forced out-of-combat sexual act penalizes an `NPC` whose resulting affinity stays at or
  above the invite threshold (or who is not a party companion at all)
- **THEN** the player receives only the cast's rendered `EventLog`, with no auto-leave notification line

### Requirement: A malformed or foreign sexual-resist entry never penalizes and never raises
`_scan_out_of_combat_sexual_coercion` SHALL ignore, without penalizing and without raising, any
`kind == "sexual_resist"` entry whose `data` is not a mapping, and SHALL ignore any entry whose
`event_log.actor` does not equal the scanning actor's own key.

#### Scenario: A malformed non-mapping data payload is ignored without raising
- **WHEN** a `kind == "sexual_resist"` entry's `data` is not a mapping (for example a string or a list)
- **THEN** `_scan_out_of_combat_sexual_coercion` applies no penalty for that entry, does not call
  `apply_affinity_change` for it, and does not raise

#### Scenario: A non-player-actor resist entry is ignored
- **WHEN** the scanned `EventLog`'s `actor` does not match the scanning actor's own key
- **THEN** `_scan_out_of_combat_sexual_coercion` applies no penalty for any entry in that log and does
  not call `apply_affinity_change`

#### Scenario: A non-sexual-resist entry is ignored
- **WHEN** the resolved `EventLog`'s entries include kinds other than `"sexual_resist"` (for example
  `"skill_practice"`)
- **THEN** `_scan_out_of_combat_sexual_coercion` applies no penalty attributable to those entries
