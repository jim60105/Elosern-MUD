## Context

`world/rules/action.py::_step4b_sexual_resist_gate` runs inside `ActionResolver.resolve`, the single
state-writing gateway both combat and out-of-combat casts share. It resolves one `resist_verdict()`
contest per non-actor target of a `resistible=True` sexual act and stages a
`PendingEffect` that becomes an `EventEntry(kind="sexual_resist", actor=<caster key>,
target=<resister key>, data={"resisted": bool, "auto_comply": bool, "roll": int | None}, ...)` in the
resolved `EventLog`, regardless of caller. Every sexual act in `SEXUAL_ACT_REGISTRY` is declared
`usable_out_of_combat=True` (`world/skills/sexual_acts/_builder.py`), so a player can cast a resistible
act on any NPC present in their room through `cast <act>=<target>` outside combat, exactly as freely as
inside it.

`world/rules/combat_session.py::_scan_sexual_coercion` already turns a forced outcome
(`resisted is False and auto_comply is False`) into a `-sexual_forced_penalty` affinity hit via the sole
writer `apply_affinity_change(target, actor, AffinitySource.SEXUAL_FORCED, ...)`, wired into
`submit_player_action` beside the pre-existing `_scan_friendly_fire`. That wiring only fires for the
in-combat round path. `world/rules/cast_settlement.py::settle_out_of_combat_cast` — the equivalent outer
settlement boundary for out-of-combat casts — has no such scan, so today a forced act performed out of
combat produces the identical `sexual_resist` `EventEntry` but costs the target nothing. This was a
named, deliberate deferral (`sexual-resist-turn-cost`'s design.md, Decision 5), not an oversight:
`_scan_sexual_coercion` and its `EventEntry` contract needed to exist and prove out first. Both now
have (`sexual-resist-turn-cost` and `sexual-resist-cast-wiring` are archived and shipped).

## Goals / Non-Goals

**Goals:**
- Every forced resistible sexual act pays the same `-sexual_forced_penalty` affinity cost against the
  same `NPC` target, whether cast in combat or out of combat.
- Reuse the shipped in-combat mechanism's constants, sole writer, and rollback-safety pattern exactly —
  no new balance number, no second penalty source, no parallel affinity-writing path.
- A failure applying the penalty (or the auto-leave it can trigger) rolls back the entire out-of-combat
  cast, symmetric with how a coercion-scan failure rolls back the entire in-combat round.
- A companion NPC that auto-leaves the party from an out-of-combat forced act notifies the player,
  exactly as the in-combat case already does.

**Non-Goals:**
- **No change to `resist_verdict()`, `_step4b_sexual_resist_gate`, or the `sexual_resist` `EventEntry`
  contract.** This proposal is purely a consumer of the already-shipped contract, structurally identical
  to how `sexual-resist-turn-cost` consumed it for combat.
- **No new `AffinitySource` or rulebook field.** `SEXUAL_FORCED` and `sexual_forced_penalty` already
  exist and are reused unchanged.
- **No change to `cast-settlement-atomicity`'s existing snapshot/restore machinery**
  (`_snapshot_settlement_state`, `_restore_settlement_state`, `_ENTITY_SURFACES`). See Decision 1 — the
  new scan owns a self-contained snapshot/restore of just the surfaces it touches, mirroring
  `_scan_sexual_coercion`'s own independent nested-transaction pattern in `combat_session.py` rather than
  widening shared, every-cast infrastructure.
- **No roster-widening question.** Combat's `_scan_sexual_coercion` had to decide how far past a
  player's declared companions its snapshot should reach, because `entry.target` resolves against the
  whole `battlefield.roster` (Decision 3 of `sexual-resist-turn-cost`'s design). Out of combat there is
  no roster: `_step3_targeting` resolves `entry.target` only against `request.targets`, the cast's own
  explicit target list, so the correct scope is simply "every `NPC` in `request.targets`" — settled by
  construction, not a design choice this proposal has to make.

## Decisions

### Decision 1 — A self-contained scan with its own snapshot/restore, not a widened `_ENTITY_SURFACES`

`cast_settlement.py`'s existing `_ENTITY_SURFACES` tuple and `_snapshot_settlement_state` /
`_restore_settlement_state` cover **every** out-of-combat cast, not only sexual acts — they are shared,
already-audited infrastructure whose existing spec (`cast-settlement-atomicity`) enumerates the exact
surface list it restores. Adding `relations_data` to that shared list to cover this proposal's narrower
need would touch every cast's snapshot cost and would require modifying an already-shipped, already-
verified capability's spec text for a concern that only sexual acts have.

Instead, the new `_scan_out_of_combat_sexual_coercion(actor, targets, event_log)` function owns its own
before-the-fact snapshot of exactly the `NPC` targets it is about to penalize (never the full
`request.targets` list — only the ones the forced-outcome filter actually selects, matching
`_scan_sexual_coercion`'s own `forced` list scope) and its own on-failure restore, called from inside
`settle_out_of_combat_cast`'s existing outer `transaction.atomic()`:

```python
def _scan_out_of_combat_sexual_coercion(
    actor: Any, targets: list[Any], event_log: EventLog
) -> tuple[str, ...]:
    if event_log.actor != str(actor.key):
        return ()
    by_key = {str(target.key): target for target in targets}
    forced: list[Any] = []
    for entry in event_log.entries:
        if entry.kind != "sexual_resist":
            continue
        if not isinstance(entry.data, dict):
            continue
        if entry.data.get("resisted") is not False:
            continue
        if entry.data.get("auto_comply") is not False:
            continue
        target = by_key.get(entry.target)
        if target is None or not isinstance(target, NPC):
            continue
        forced.append(target)
    if not forced:
        return ()
    penalty = get_config().sexual_forced_penalty
    notifications: list[str] = []
    party_before = list(actor.db.party or ())
    members_before = {int(t.pk): t.db.party_member for t in forced}
    relations_before = {int(t.pk): t.db.relations_data for t in forced}
    try:
        with transaction.atomic():
            for target in forced:
                outcome = apply_affinity_change(
                    target, actor, AffinitySource.SEXUAL_FORCED, -penalty
                )
                if outcome.auto_leave_notification is not None:
                    notifications.append(outcome.auto_leave_notification)
    except Exception:
        restore_membership_surfaces(actor, party_before, members_before)
        restore_relations_surfaces(relations_before)
        raise
    return tuple(notifications)
```

This is deliberately near-identical to `_scan_sexual_coercion`, differing only in: a single `event_log`
instead of `logs: list[EventLog]` (one cast produces exactly one log, never a round's worth), and
`by_key.get(entry.target)` instead of `battlefield.roster.get(entry.target)` (no battlefield exists
out of combat). Keeping the two scans structurally separate — rather than extracting a shared helper
parameterized over "how do I resolve a target key" — mirrors this codebase's own precedent:
`_scan_friendly_fire` and `_scan_sexual_coercion` are themselves two independently written,
structurally-mirrored functions rather than one shared abstraction, because their target-resolution
shapes (roster vs. companion set) already differ. Extracting a shared core now would touch
`combat_session.py` — already-shipped, already-tested, and outside this proposal's minimal footprint —
for a three-line difference.

**Alternative considered:** widen `_ENTITY_SURFACES` with `("relations_data", None)` and let the generic
snapshot/restore cover it for every cast. Rejected: it charges every out-of-combat cast (buffs, disguise,
non-sexual skills) one extra attribute snapshot for a surface only sexual acts ever touch, and it turns
this proposal into a `cast-settlement-atomicity`-modifying change for no behavioral gain over the
self-contained alternative.

**Alternative considered:** extract a shared `_scan_forced_sexual_acts(actor, forced_entries) ->
tuple[str, ...]` core called by both `combat_session.py` and `cast_settlement.py`, with each caller doing
only its own target-resolution and log-iteration. Rejected for this proposal's scope: it requires editing
`combat_session.py`, a file this proposal does not otherwise need to touch, to extract a three-line
difference into a parameter — a refactor with its own regression surface across a shipped, heavily-tested
module, better left to a dedicated cleanup proposal if the duplication ever grows past these two call
sites.

### Decision 2 — Wire the scan immediately after a successful `ActionResolver.resolve`, inside the outer transaction

`settle_out_of_combat_cast` already runs `ActionResolver.resolve(request)` as the first operation inside
its outer `transaction.atomic()` and returns immediately on rejection. The new scan is inserted
immediately after the success check and before the clock-advance step:

```python
with transaction.atomic():
    result = ActionResolver.resolve(request)
    if result.outcome != "success":
        return CastSettlement(result, (), ())
    notifications = _scan_out_of_combat_sexual_coercion(
        request.actor, request.targets, result.event_log
    )
    if not supplied and getattr(clock, "_script", None) is None:
        clock = get_world_clock()
    events = tuple(
        clock.advance(result.time_cost_seconds, AdvanceSource.COMMAND, (request.actor,))
    )
return CastSettlement(result, events, notifications)
```

Running it before the clock advance (rather than after) mirrors the in-combat ordering, where the
coercion scan runs immediately after the round's `EventLog`s are produced and before the round record is
persisted. It also means a coercion-scan failure never leaves a clock advance half-applied — the clock
callback never runs if the scan already raised.

**Alternative considered:** run the scan after the clock advance. Rejected — no ordering requirement
favors it, and running it first keeps the "resolve, then apply resolution consequences, then advance
time" sequencing consistent with the in-combat precedent.

### Decision 3 — `CastSettlement` gains a `notifications` field; the command layer delivers it

`CastSettlement` today carries only `result` and `events`. The scan's auto-leave notification lines have
nowhere to go without a third field. `notifications: tuple[str, ...] = ()` is added with a default so
every other existing construction site (`CastSettlement(result, ())` on rejection, and any test that
constructs one directly) keeps compiling unchanged; the two call sites this proposal touches are updated
to pass the real tuple.

`commands/action.py::CmdCast._cast_out_of_combat` already renders `settlement.result.event_log` on
success; it is extended to send each notification line after that render. The exact ordering (rendered
log first, notification after) is the reverse of `_cast_in_session`'s `lines`-before-`message` order —
that inversion is harmless and not worth matching exactly, since both call sites already deliver both
pieces of information to the same player in the same command turn; what actually matters, and is what
this decision is really about, is that the notification reaches the player at all. Without this, an
auto-leave triggered out of combat would silently change `actor.db.party` with no message ever reaching
the player — a regression relative to the in-combat behavior this proposal is supposed to match.

**Alternative considered:** thread notifications through `result.event_log` as an extra `EventEntry`
instead of a new `CastSettlement` field. Rejected — the auto-leave notification is a caller-facing
side effect of the *scan*, not part of the deterministic, replayable action record `ActionResolver`
produces; combat's own precedent keeps it out of the `EventLog` too (`submit_player_action` returns
notifications in its own outcome dict, separate from `EventLog`).

## Risks / Trade-offs

- **[Risk]** Duplicating `_scan_sexual_coercion`'s structure rather than sharing code means a future
  change to the forced-outcome filter (the `resisted is False and auto_comply is False` check) or the
  affinity-write pattern must be applied in both places.
  → **Mitigation:** the delta spec pins both functions' exact filter semantics with mirrored scenario
  text, and this design doc's Decision 1 records the extraction alternative as available if a third
  call site ever appears. Two call sites sharing one contract with independent, test-covered
  implementations is the same trade-off `_scan_friendly_fire`/`_scan_sexual_coercion` already made and
  shipped with.
- **[Risk]** If a future change to `_step4b_sexual_resist_gate` or `SEXUAL_ACT_REGISTRY` allows a
  resistible act to target something other than an `NPC` or a `PlayerCharacter` out of combat, the
  `isinstance(target, NPC)` guard silently declines to penalize rather than raising.
  → **Mitigation:** this exactly mirrors `_scan_sexual_coercion`'s own precedent (a non-`NPC` forced
  target applies no penalty, mirroring `apply_affinity_change`'s own owner rejection) and
  `apply_affinity_change` itself rejects a non-`NPC` owner unconditionally, so no penalty could ever be
  misapplied even if this guard were absent — the guard only avoids an unnecessary call.
- **[Defensive, not currently reachable]** `world/rules/action.py`'s `ActionRequest.targets` type and
  `settle_out_of_combat_cast` itself both allow more than one target, and the scan applies one
  independent penalty per forced target rather than stopping at the first — but today's only production
  caller, `commands/action.py::CmdCast._cast_out_of_combat`, builds `targets` from a single
  `self._resolve_target(target_key)` call (0 or 1 target; unlike `_cast_in_session`'s
  `parse_session_targets`, there is no comma-separated or shorthand parsing for the out-of-combat path).
  So no player can drive this scan with more than one target today. This is forward-looking coverage —
  cheap to keep correct now, in case a future out-of-combat entry point ever supports a multi-target
  cast — not a currently-exploitable gap.
  → **Coverage:** mirrored directly from `_scan_sexual_coercion`'s own `test_area_act_rolls_one_
  independent_contest_per_target`-style test; the delta spec's scenario is written as forward-looking
  regression coverage, not as closing an active production hole.
- **[Defensive, not currently reachable]** The scan ignores any entry whose `event_log.actor` does not
  match the scanning actor's own key — mirroring `_scan_sexual_coercion`'s filter, which is load-bearing
  there because one round's `logs` genuinely spans multiple combatants' own `EventLog`s (NPCs and
  monsters act too). Out of combat, `settle_out_of_combat_cast` always calls the scan with the single
  `result.event_log` that `_step7_build_event_log` built from that same `request.actor`
  (`EventLog.actor = _entity_key(request.actor)`), so the mismatch branch cannot currently trigger
  through the shipped call site — it is symmetry with the in-combat scan, not an active guard.
  → **Coverage:** kept for structural parity and because it costs nothing; the delta spec's scenario is
  exercised only via a synthetically-constructed `EventLog` in tests, exactly as
  `_scan_sexual_coercion`'s own equivalent test does.
- **[Risk]** A malformed `EventEntry.data` payload (already guarded for the in-combat scan) must not
  raise here either.
  → **Mitigation:** the `isinstance(entry.data, dict)` guard is copied verbatim from
  `_scan_sexual_coercion`, with a mirrored delta-spec scenario.

## Migration Plan

Additive only — no data migration, no schema change, no existing behavior altered. Deploys as an
ordinary code change; the new scan has no effect until a resistible act is actually forced out of
combat, at which point it applies the same, already-tuned `sexual_forced_penalty`. No rollback
concerns beyond reverting the commit.

## Open Questions

None. The mechanism, penalty magnitude, and affinity source are all already decided and shipped by
`sexual-resist-turn-cost`; this proposal only extends their reach to a second, already-identified call
site.
