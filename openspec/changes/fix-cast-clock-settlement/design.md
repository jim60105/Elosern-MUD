## Context

Verified failure trace (security-audit run-3, finding index 6):

- `commands/action.py:93-133` `_cast_out_of_combat` builds an `ActionRequest` (with a `dict(self.caller.db.disguised_stats or {})` context payload for `status_disguise`, :106-113), calls `ActionResolver.resolve` (:119-126), and only on success calls `get_world_clock().advance(result.time_cost_seconds, AdvanceSource.COMMAND, [self.caller])` (:127-132) before rendering (:133).
- `world/rules/action.py:1068-1098` `_commit` snapshots every pending-effect entity's declared surfaces (:1076-1090), applies all effects — skill effect, practice award, planner effects — inside one `transaction.atomic()` (:1091-1098), and exits before `resolve` returns; `resolve` (:1141-1175) returns success only after that commit.
- `world/rules/clock.py:316-337` `advance` snapshots `_ADVANCE_ENTITY_SURFACES` (clock.py:228-238) on the caller-supplied entities, then runs all stages, the tick increment, and the tick persist inside its own `transaction.atomic()`; on failure it restores only those caller surfaces (clock.py:333-336) plus the tick.
- Neither project code nor Evennia's command handler wraps `CmdCast.func` in an outer transaction, so: a clock callback or final-persist failure rolls back only the advance's post-action snapshot; a process stop between the two transactions leaves the action durable without the tick. Reproduced by the audit with `db.disguised_stats` materialized as `{}` and `db.skill_proficiency["status_disguise"]` increased by 10.0 (elf race multiplier) while the tick stayed unchanged.
- Catalog: seven ACTIVE `usable_out_of_combat=True` skills, all with empty cost dicts — `status_disguise` (world/skills/registry.py:624-632), `dominion_art` (:642-650, needs battlefield context in the stock path), `divine_sexual_arts` (:748-757), and the four unmechanized divine mysteries `divine_time_dilation` (:758-767), `divine_space_distortion` (:768-777), `divine_matter_transmutation` (:778-787), `divine_life_extension` (:788-797). `DEFAULT_CAST_SECONDS = 6` (world/rules/action.py:151).

House patterns reused: the shared snapshot/restore dispatch in `world/rules/surfaces.py` (`attribute_snapshot` / `restore_attribute_best_effort`), the action module's entity surface declaration (`_snapshot_entity_state`, world/rules/action.py:927-946; `_snapshot_touched`'s battlefield branch, :999-1015), the clock module's tick snapshot/restore (world/rules/clock.py:254-272) and entity-cache refresh (:289-303), and the quest module's `snapshot_quest_log`/`restore_quest_log` helpers (world/quests/transitions.py:83-90).

## Goals / Non-Goals

**Goals:**
- An out-of-combat cast settles all-or-nothing: skill effect, practice award, planner writes, and the command-time charge either commit together or the actor, targets, battlefield, callback-owned surfaces, and clock tick are all restored to their pre-action state in cache and storage.
- One deterministic enforcement point: `CmdCast._cast_out_of_combat` delegates to the settlement API, so the Telnet command path inherits the guarantee without per-skill branches.
- Success is presented (EventLog rendered) only after the outer transaction commits; failures propagate only after compensation.
- The settlement covers the real catalog path exactly: `status_disguise` (disguise + practice), `dominion_art` (target `skill_grants`), `divine_sexual_arts` (target sexual state), the four divine mysteries (no mechanical effect), plus any buff-applying out-of-combat spell.

**Non-Goals:**
- Changing `ActionResolver.resolve` or `WorldClock.advance` semantics; both keep their own inner transactions (degrading to savepoints) and their own inner snapshot/restore.
- Wrapping the in-combat session cast path (`_cast_in_session`, combat-session orchestration) — explicitly untouched.
- Extending the clock's snapshot surface set or the advance registry: owned by `fix-clock-rollback-cache-sync`, whose D6 mandates the seam consumed here.
- Designing `fix-movement-settlement-atomicity` internals; that change owns the movement post-traverse outer boundary.
- Auditing planner-owned quest writes on objects outside the declared superset (see Risks: the seven-skill catalog never produces defeated targets, so the quest planner never fires on this path).

## Decisions

**D1 — The settlement is a deterministic `world/rules` module with one entry per cast.** New `world/rules/cast_settlement.py`:

```python
@dataclass(frozen=True)
class CastSettlement:
    result: ActionResult
    events: tuple[ScheduledEvent, ...]

def settle_out_of_combat_cast(request: ActionRequest, *, clock=None) -> CastSettlement:
    clock = clock or get_world_clock()
    snapshot = _snapshot_settlement_state(request, clock)   # before the outer transaction
    try:
        with transaction.atomic():
            result = ActionResolver.resolve(request)
            if result.outcome != "success":
                return CastSettlement(result, ())
            events = tuple(clock.advance(result.time_cost_seconds, AdvanceSource.COMMAND, (request.actor,)))
    except Exception:
        _restore_settlement_state(snapshot)                 # after rollback, before re-raise
        raise
    return CastSettlement(result, events)
```

The module lives in `world/rules` because it is canonical game-state machinery; `commands/action.py` remains the presentation seam that builds the request (including the `status_disguise` context payload) and renders the returned result — the same split as `charge_movement` and the parallel change's `settle_movement`. *Alternatives considered: wrapping the two calls in `transaction.atomic()` inside the command — rejected: Django rollback does not reconcile Evennia in-process caches, and `advance`'s own snapshots are post-action (see D2/D3), so the outer owner must snapshot pre-action itself; and adding the boundary inside `resolve` — rejected: `resolve` is also called by combat orchestration, which owns its own settlement.*

**D2 — Pre-resolution snapshot superset, merged by object identity, built before the outer transaction.** `_snapshot_settlement_state` records, in one mapping keyed by `id(obj)`:

1. **The merged advance registry** — `build_advance_snapshot_registry(clock, MAX_ADVANCE_SECONDS, AdvanceSource.COMMAND, (request.actor,))`, per `fix-clock-rollback-cache-sync` D6 built **before** the outer transaction opens, covering the actor's advance surfaces plus every callback-owned surface (quest logs and room pins, merchant stock, NPC schedule state and location, instance-room state, pruned map knowledge). The window is widened to `MAX_ADVANCE_SECONDS` (the one-day advance bound, world/rules/clock.py:319-322) because the real `seconds` is only computed at resolve step 8 — after writes — and a widened window snapshots a strict superset of what the actual advance can write: every registered contract's discovery queries are window-independent today (the sibling's D4 declaration table), so the widened window costs nothing extra and stays correct if a future contract becomes window-dependent.
2. **The actor's and every request target's action surfaces** — the entity surface set (`traits`, `disguised_stats`, `sexual_traits`, `virgin`, `experience_types`, `buffs`, `skill_grants`, `magic_xp`, `skill_proficiency` — the shared `_ADVANCE_ENTITY_SURFACES` declaration, world/rules/clock.py:228-238) plus `quest_log`. Targets are snapshotted because `dominion_art` writes target `skill_grants` (conferral), `divine_sexual_arts` writes target sexual state, and the clock never settles targets (only the actor is passed to `advance`).
3. **The battlefield when the request context carries one** — `fled`/`knocked_out` surfaces per `_snapshot_touched`'s battlefield branch (world/rules/action.py:999-1007), covering the `FLEE_SKILL_KEY` + `BattlefieldActionContext` branch of the same command method (commands/action.py:114-118).
4. **The clock tick** — `_snapshot_clock_tick(clock)` (world/rules/clock.py:254-260).

Merging by identity is mandatory: the registry's actor entry and the settlement's actor surfaces are one entry with the union of surfaces (advance surfaces + `quest_log`), so restore visits each object exactly once with pre-action values. A contract that raises during the registry build fails the settlement before the transaction opens and before any write — fail-closed, exactly the sibling's D2 mandate for `advance()` — so no restore is needed on that path. *Alternatives considered: snapshotting only `_commit`'s effect entities — rejected: the touched set is unknowable before resolution (effects are staged at step 5); the deterministic analogue is the declared superset above. Leaving restore to `advance`'s own snapshots — rejected: they are taken post-action, so on outer-commit failure they would restore post-action (never-committed) values against rolled-back pre-action rows.*

**D3 — Outer transaction shape and restore semantics.** The settlement's `transaction.atomic()` is the outer transaction; `_commit`'s and `advance`'s blocks degrade to Django savepoints. Failure recovery order:

- **Advance failure (inner):** the savepoint rolls back, `advance` runs its own restore (clock.py:333-336, which refreshes the actor's caches to post-action values), then the settlement's `except` block — outside the `with`, after the rollback — runs `_restore_settlement_state`, bringing every surface back to the pre-action snapshot.
- **Outer-commit failure** (the `with`-block exit raises): `advance`'s restore never runs, so the settlement's pre-action snapshot is the sole recovery for every surface it covers.
- **Genuine process stop inside the window:** no in-process restore can or must run — the process (and its idmapper and attribute caches) is gone, and on restart the database shows either the fully committed pre-action rows or the fully committed post-action rows because the outer transaction is all-or-nothing. That is exactly the split the finding describes between today's two independent transactions; the commit-window compensation test (task 3.6) is the deterministic surrogate for the restart case.
- **Rejected resolution:** normal early return inside the `with` commits an empty transaction; no writes, no advance, no restore.

`_restore_settlement_state` runs in fixed order, best-effort per step with `log_warn` (a failing step degrades to the next; a restore failure never masks the original exception):
1. Clock tick via `_restore_clock_tick` (world/rules/clock.py:263-272).
2. Per-object surfaces via `restore_attribute_best_effort` (world/rules/surfaces.py:41-55), with `quest_log` surfaces via the quest module's `restore_quest_log` (world/quests/transitions.py:88-90) to avoid drift; registry entries with a recorded `location` re-fetch the target by stored primary key after the rollback and assign through the location setter so Evennia's contents caches are reconciled, exactly per the sibling's D3.
3. Per-object cache refresh: reload `traits.trait_data`, clear `traits._cache`, and drop the cached `sexual` property — the same `_refresh_advance_entity_caches` semantics (world/rules/clock.py:289-303).

**D4 — Callback-owned surface coverage through the sibling seam.** The settlement consumes `build_advance_snapshot_registry` plus `_snapshot_clock_tick`/`_restore_clock_tick` as mandated by `fix-clock-rollback-cache-sync` D6. Until that change lands, the settlement falls back to the existing `_ADVANCE_ENTITY_SURFACES` + `_snapshot_advance_entities` (world/rules/clock.py:241-251) for the actor's advance surfaces and keeps a guarded (deliberately skipped) integration test asserting callback-owned coverage once the seam exists — forward-declared, never faked. The `status_disguise` clock-callback regression test (task 3.2) is written against the fallback path and stays green either way.

**D5 — Command delegation and post-commit rendering.** `_cast_out_of_combat` keeps constructing the request (target search, `status_disguise` disguise payload, battlefield-context promotion for `FLEE_SKILL_KEY`) but replaces the `resolve` + `advance` sequence with one `settle_out_of_combat_cast(request)` call; on success it renders `settlement.result.event_log`, on rejection `rejection_message(...)`, and exceptions propagate exactly as today. Because the API returns only after the outer commit, success rendering is post-commit by construction. `_cast_in_session` is untouched. Source-inspection test: the command contains no direct `get_world_clock().advance` call after the change.

**D6 — Determinism and bounds.** The superset is bounded: one actor, the request targets (single-player scale), at most one battlefield, and the registry's discovery scans — the same queries settlement already runs. The settle path uses no randomness and no network services. `AdvanceSource.COMMAND`, the `[actor]` entity scope, and the "no advance on rejection" rule are preserved exactly (the `world-clock` requirement keeps its charge semantics; only the transaction boundary changes).

**D7 — Scope and overlap.** This change owns only the out-of-combat cast command path. The movement post-traverse outer boundary is owned by `fix-movement-settlement-atomicity`; the advance registry completeness and the `build_advance_snapshot_registry` builder are owned by `fix-clock-rollback-cache-sync`; both consume/are consumed through the same D6 seam. Neither `ActionResolver.resolve` nor `WorldClock.advance` is modified; `_commit`'s inner snapshot/restore keeps handling inner failures exactly as today.

## Risks / Trade-offs

- **Planner-owned quest writes on objects outside the superset** (a battlefield-context cast producing defeated targets routes the quest planner over `PlayerCharacter.objects.all_family()`): the seven ACTIVE out-of-combat skills stage no damage effects, so no defeated targets and no planner effects on this path; the completeness guard (task 3.7) asserts each of the seven skills' effect entities lies within `{actor, request targets}`, and the residual is documented — the in-combat path, where defeated targets occur, is owned by combat-session orchestration and untouched here.
- **The outer-commit failure cannot be reproduced inside `EvenniaTest`** (Django `TestCase` wraps every test in its own `atomic`, so the boundary is a nested savepoint and `set_rollback(True)` silently rolls it back without raising): the commit-window scenario is verified by directly invoking `_restore_settlement_state` against a deliberately constructed divergent in-process state and asserting cache/storage equivalence — the same approach the parallel movement change uses (its task 3.6).
- **`_EVENT_SOURCES` is module-global and tests leak registrations into it** (the sibling's D7 warning): fault-injection tests register a failing source only after asserting no production kind collides, and reset the registry in `tearDown`.
- **The widened registry window snapshots a superset of the actual advance** (e.g. a due-deadline player who is not due at the real window): restore is idempotent and writes exactly the pre-action values, so over-snapshotting is cost-only, and it is bounded by the one-day cap.
- **A restore step failing on an object deleted inside the rolled-back transaction**: registry semantics from the sibling's D3 — deleted objects are skipped, cached-but-deleted idmapper entries are flushed so the next access re-fetches rolled-back rows; the settlement reuses that behavior.

## Migration Plan

Unreleased project with no users; no data migration. The settlement runs on every out-of-combat cast, so successful casts take the same transaction-shaped path with the same observable effects. Rollback strategy: revert the change — no persisted schema or state-format changes.

## Open Questions

- None blocking: the `fix-clock-rollback-cache-sync` design (D6) has settled the advance-surface seam (`build_advance_snapshot_registry` plus tick snapshot/restore) this change consumes; integration verifies the merged registry covers the cast case once that change lands.
