## Context

The approved brainstorming design for this work is
`docs/superpowers/specs/2026-09-10-field-combat-initiation-design.md`; this
change implements its §4 flow, its §5 `combat_initiation.py` module, and §§6-9.

Current state:

- `commands/action.py::CmdCast.func()` checks for an active session and routes
  to `_cast_in_session()` or `_cast_out_of_combat()`. The latter builds a
  `RoomActionContext` (or reuses `caller.ndb.action_context`) and calls
  `world/rules/cast_settlement.py::settle_out_of_combat_cast()`, which charges
  `AdvanceSource.COMMAND` time on success.
- `RoomActionContext` reports every co-located non-self entity as
  `Relation.ALLY`. Out of combat there is no way to express hostility.
- `engage()` / `engage_group()` build the record, reconstruct the battlefield,
  `_persist()`, register skip safety, and clear any dialogue session.
  `reconstruct_battlefield()` takes a record and does not require it to be
  persisted — `engage()` is literally "reconstruct, then persist".
- `submit_opening_action()` reads the session, revalidates, and dispatches
  either one round or compression, always granting the player first strike.
- `_submit_request()` opens its own `transaction.atomic()` and its
  `transaction.on_commit()` comment states it waits for "the OUTERMOST
  transaction".
- `world/rules/combat_session.py` is 1697 lines / 66KB.

## Goals / Non-Goals

**Goals:**

- One exploration cast at a co-located hostile monster becomes that fight's
  first action, with the player acting first.
- A rejection costs nothing: no session, no resources, no world time.
- Session creation and the opening action share one failure boundary.
- Keep the non-damaging / sexual-skill-on-NPC path bit-for-bit unchanged.

**Non-Goals:**

- The webclient exploration cast surface. There is no `explore.cast` action
  code and `SkillBook.vue` is a read-only codex; the UI entry is a follow-up
  change and this one is verified through the `cast` command.
- Opening combat against NPCs. It would touch quests, dialogue, schedules, and
  town order.
- Item use from exploration.
- Any change to `classify_overwhelm()`, `resolve_overwhelm()`,
  `submit_opening_action()`, or `engage_group()` — all consumed, none edited.
- Any change to `settle_out_of_combat_cast()`'s own logic.

## Decisions

**D-1. The first discriminator is the target, not the skill.** A skill used in
exploration against a living, co-located hostile `Monster` always initiates
combat. `DamageEffect` presence decides only whether the encounter is settled
by `resolve_overwhelm()` or played as ordinary rounds — a decision that already
lives inside `submit_opening_action()`.

Two independent questions, each with one job:

| Question | Decides |
| --- | --- |
| Is the target a co-located hostile monster? | Whether combat starts |
| Does the skill damage an enemy, and does the verdict hold? | One-shot or rounds |

Alternative rejected: gating combat initiation on the skill being damaging.
Rejected in brainstorming — it produces the incoherent case where a debuff or a
sexual act aimed at a hostile monster resolves harmlessly in the open world
while the monster does not react.

The direct consequence, accepted explicitly: aiming a heal at a monster starts
a fight and plays the heal as the opening action. No special case.

**D-2. A new module, not a new section of `combat_session.py`.**
`combat_initiation.py` depends on `combat_session`, `overwhelm`, and
`action_preview`; nothing depends on it in reverse and `combat_session` does not
know it exists. Its whole job is one routing decision plus one validation pass,
which is small enough to hold in view — the opposite of adding a fourth
responsibility to a 1697-line module.

**D-3. Validate under a `BattlefieldActionContext` against a candidate
battlefield that is never persisted.** The candidate is built by handing
`reconstruct_battlefield()` an unwritten `CombatSessionRecord`, stopping short
of `_persist()`. `revalidate_submission()` and `ActionResolver.preflight()` then
answer the question that will actually be asked a moment later, with correct
enemy relations.

Alternatives rejected:

- *Validate under `RoomActionContext`, then engage.* Rejected: the context
  reports monsters as allies, so `FactionConstraint` and range would be
  evaluated against a false world view, and any faction-sensitive skill would
  give the wrong answer.
- *Engage first, then validate, then clear the session on rejection.*
  Rejected: a rejected cast must not persist a session at all, and unwinding one
  is strictly worse than not creating it.
- *Change `RoomActionContext` to report monsters as enemies.* Rejected: it
  would silently change faction outcomes for every existing out-of-combat cast,
  including the whole sexual-act catalog.

**D-4. `usable_out_of_combat` is checked explicitly, before the candidate
battlefield exists.** Because validation deliberately supplies a battlefield,
`world/rules/action.py`'s own `usable_out_of_combat` gate would pass. Checking
it at the entry — reporting the existing `SKILL_NOT_USABLE_OUT_OF_COMBAT` — is
what keeps `skill-field-availability`'s audit meaningful rather than cosmetic.
It runs first, so its answer is not masked by anything downstream.

**D-5. AREA opens against the whole room; SINGLE opens against the named
monster.** `classify_overwhelm()` is a team-versus-team verdict, so an AoE
opening that engaged only one of three monsters would compute a verdict against
the wrong roster and then fight the other two separately. The room's living
hostile monsters are resolved into concrete targets and passed as an explicit
list, which is the form `AREA` already accepts; no shorthand is used, because
`commanded_damage_reaches_enemy()` takes concrete keys.

**D-6. A damaging skill aimed at a non-monster is refused, not resolved.**
`RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET` (defined by
`out-of-combat-damage-gate`) fires at the entry, before any resource or clock
access. Defence in depth: the resolver gate would refuse it anyway once it
reached `settle_out_of_combat_cast()`, but rejecting at the router means the
message names the actual mistake rather than surfacing from two layers down.

**D-7. One transaction spans session creation and the opening action.**
`engage_group()` persists the session before the opening action runs, so a
raising opening action would otherwise leave the player in a fight that never
started. `initiate_field_combat()` wraps both in one
`transaction.atomic()`.

This nesting is safe and matches existing intent: `_submit_request()`'s
`transaction.on_commit()` comment already states it waits for the outermost
transaction, so the round-boundary event and `settle_session()`'s post-commit
work simply defer to the outer commit, while `_submit_request()`'s own
`atomic()` degrades to a savepoint.

A database rollback is not sufficient on its own, because engagement leaves two
kinds of state outside the transaction's reach.

*Process-memory registration.* `engage_group()` calls
`register_active_battlefield()`; the failure path must
`unregister_participants()` for the same identities.

*Evennia attribute caches.* `engage_group()` writes
`actor.db.active_combat` (through `_persist()`, `world/rules/combat_session.py:571`)
and clears `actor.db.dialogue_session` (through `clear_dialogue_session()`). The
idmapper cache is not transaction-aware — the reason
`cast_settlement.py::_restore_settlement_state` and
`combat_session.py::_restore_round_touched` exist at all. So a rolled-back
initiation would leave `read_session(actor)` returning the engaged record in
process, stranding the player in a fight the database no longer holds, and would
leave a dialogue session retired that was never really retired.

The submission body's own `_snapshot_round_touched()` does snapshot
`active_combat` in its `extra` dict, but it cannot help here: it snapshots at
its own entry, which in this flow is *after* engagement already wrote the value,
so restoring from it would reinstate the engaged session rather than the
pre-engagement absence. `initiate_field_combat()` therefore takes its own
snapshot of both attributes **before** `engage_group()` runs and restores them
on the failure path, reusing `world/rules/action.py`'s `_attribute_snapshot` /
`_restore_attribute` helpers.

**D-8. World time transfers from command to combat.** The opening cast does not
charge `AdvanceSource.COMMAND`; it is folded into the session and charged once
as combat time by `settle_session()`. Charging both would double-bill an action
that is now the fight's first round.

**D-9. The boundary event rides the outer commit.** `field_combat_initiated`
carries `char`, `room`, `tick`, `skill`, `enemy_count`, and `opening`
(`"round"` or `"overwhelm"`), emitted through the `world.observability` facade
via `transaction.on_commit`, so a rolled-back initiation leaves no record and
the callback itself does no computation.

## Risks / Trade-offs

- **[Building a candidate battlefield duplicates part of `engage_group()`'s
  work, and the two could drift.]** → Both call the same
  `reconstruct_battlefield()` against the same record shape, and the candidate
  record is constructed by the same helper path. A test asserts the candidate's
  roster and teams match those of the session `engage_group()` then persists for
  the identical targets.
- **[Aiming a heal or a sexual act at a monster starting a fight may surprise a
  player.]** → Accepted as the direct consequence of D-1; it is the rule the
  owner approved, and it is stated in the player-facing command documentation
  updated by this change.
- **[A sexual act aimed at a monster changes which coercion scan runs.]** →
  Stated in the proposal and asserted in a test, so the change is recorded
  rather than discovered. Aimed at an NPC, nothing changes.
- **[Engagement leaves state a database rollback cannot undo — process-memory
  registration and non-transaction-aware Evennia attribute caches — so a failed
  opening action could strand the player in a session the database no longer
  holds.]** → Per D-7: the rollback path unregisters the participants and
  restores the `active_combat` and `dialogue_session` snapshots taken before
  engagement. Covered by tests that force the opening action to raise and then
  assert, in the same process with no reload, that `read_session(actor)` returns
  `None` and the dialogue session is intact.
- **[Wrapping `_submit_request()` in an outer transaction defers
  `settle_session()`'s post-commit work.]** → That is the documented intent of
  the existing `on_commit` comment; a test asserts a field initiation that ends
  the fight still produces its settlement effects and its boundary events
  exactly once.
- **[A room with many monsters makes one AoE opening a large first round.]** →
  Bounded by the room's occupancy, which the wilderness population and spawn
  systems already bound; no new limit is invented here.
- **[The module could accrete the webclient adapter later and stop being
  small.]** → `initiate_field_combat()` returns the `submit_player_action()`
  shape precisely so the future adapter is a thin translation in the webclient
  action layer rather than more logic here.
