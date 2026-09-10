## Why

`explore.engage` is the only way to start a fight, and it deliberately performs
no action, so the first exchange is always a plain round in which the player has
already given up the initiative. Meanwhile `combat-session-opening-dispatch`
removed compression from the ordinary loop and left
`submit_opening_action()` — the one seam that can still request it — with no
production caller. Clearing a trivially weak monster is therefore currently
more tedious than it was before that change.

This change closes the sequence. Using a skill from exploration against a
living hostile monster in the same room opens combat and plays that skill as
the player's first action: settled in one shot when the matchup is a genuine
curbstomp and the skill actually damages the target, and otherwise as the
opening round of an ordinary fight the player keeps full control of.

The routing rule is deliberately two-part, because the two questions are
independent. **Who you aimed at** decides whether combat starts. **What the
skill does** decides only whether the encounter is then settled in one shot.
That is why a heal or a sexual act aimed at a monster still starts a fight, and
why a damaging skill aimed at an NPC is refused outright.

## What Changes

- New module `world/rules/combat_initiation.py`, deliberately small and
  single-purpose: turn one exploration cast into a combat's opening move.
  Exploration-side routing does not go into `world/rules/combat_session.py`,
  which is already 1697 lines.
  - `field_combat_target(actor, target)` returns the target when it is a
    living, co-located, hostile `Monster`, expressing hostility exactly as
    `engage()` already does — being a `Monster` instance — so no second notion
    of hostility is introduced.
  - `initiate_field_combat(actor, skill_key, target, scale=1.0)` returns the
    same shape as `submit_player_action()`, so the command layer and any future
    webclient adapter share `settle_to_messages()`.
- Any skill aimed at such a monster starts combat, whatever it does. A `SINGLE`
  skill opens against that monster; an `AREA` skill opens against every living
  hostile monster in the room, matching `classify_overwhelm()`'s own
  team-versus-team semantics.
- Validation happens against a **candidate battlefield built in memory and not
  persisted**, using a `BattlefieldActionContext`. This is load-bearing:
  `RoomActionContext` reports every co-located non-self entity as an **ally**
  (`world/rules/targeting.py`), so validating a hostile opening under it would
  answer the wrong question. The combat context is the correct one because this
  cast *is* the fight's first action. A rejection returns before any session is
  persisted, any resource is spent, or any clock is read.
- `usable_out_of_combat` is checked explicitly at the entry, before the
  candidate battlefield is built. It has to be: the deliberate use of a
  battlefield context means `world/rules/action.py`'s own gate would pass.
- A damaging skill aimed at anything that is not such a monster is rejected
  with `RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET`. A non-damaging skill
  aimed at a non-monster keeps its current path through
  `settle_out_of_combat_cast()` unchanged — sexual acts and other non-damaging
  skills remain usable on NPCs exactly as today.
- `engage_group()` and `submit_opening_action()` run inside one
  `transaction.atomic()` owned by `initiate_field_combat()`, so a failure in
  the opening action rolls the session creation back instead of stranding the
  player in a fight that never started. A rollback alone is not enough: the
  skip-safety registration is process memory, and `engage_group()`'s writes to
  `actor.db.active_combat` and `actor.db.dialogue_session` stay readable through
  the non-transaction-aware Evennia idmapper cache. Both attributes are
  therefore snapshotted **before** engagement and restored on the failure path,
  alongside unregistering the participants.
- The opening cast no longer charges `AdvanceSource.COMMAND` time. It is folded
  into the session and charged once as combat time by `settle_session()`;
  charging both would double-bill an action that is now literally the fight's
  first round.
- New `field_combat_initiated` observability info event, emitted via
  `transaction.on_commit` so a rolled-back initiation leaves no record.
- `commands/action.py`'s `_cast_out_of_combat()` asks `field_combat_target()`
  first and routes accordingly. `docs/game/commands.md` and
  `docs/game/command-reference.md` are updated in the same change, per the
  command-surface documentation contract.

## Capabilities

### New Capabilities

- `field-combat-initiation`: the exploration-side entry — target
  classification, the two-part routing rule, AREA room expansion, candidate
  battlefield validation under a combat context, the explicit
  `usable_out_of_combat` gate, the damaging-skill-needs-a-monster rejection,
  the single failure boundary spanning session creation and the opening
  action, the world-time ownership handoff, and the boundary event.

### Modified Capabilities

- `cast-settlement-atomicity`: its requirement that the out-of-combat cast
  command path routes **every** cast through `settle_out_of_combat_cast()`
  becomes every cast that is not a field-combat initiation; a cast aimed at a
  living hostile co-located monster is routed to `initiate_field_combat()`
  instead and charges combat time rather than command time.

## Impact

- `world/rules/combat_initiation.py` — new module.
- `commands/action.py` — `_cast_out_of_combat()` routing.
- `docs/game/commands.md`, `docs/game/command-reference.md` — `cast`'s
  availability and behaviour in exploration.
- `world/rules/tests/test_combat_initiation.py` — new module, registered in
  `.github/evennia-shards.json`'s `rules-a` shard, which already holds every
  `test_combat_session_*` module.
- Depends on `combat-session-opening-dispatch` for `engage_group()` and
  `submit_opening_action()`, on `out-of-combat-damage-gate` for the reject
  reason, and on `skill-field-availability` for damage skills actually being
  selectable from exploration.
- Behaviour change worth stating plainly: a sexual act aimed at a monster now
  starts combat, so coercion is scanned by the in-combat
  `_scan_sexual_coercion()` rather than
  `cast_settlement._scan_out_of_combat_sexual_coercion()`. Aimed at an NPC,
  nothing changes.
- Unaffected: `explore.engage` keeps its current meaning (enter combat without
  acting) and never compresses; the webclient exploration surface, which is a
  follow-up change; and item use.
