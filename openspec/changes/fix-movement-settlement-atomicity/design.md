## Context

Verified failure trace (security-audit run-3, finding index 2):

- Evennia persists relocation before any post-traverse hook: `ObjectDB.__location_set` assigns `self.db_location = location; self.save(update_fields=["db_location"])` and updates both rooms' contents caches (`.venv/.../evennia/objects/models.py:339-356`); `DefaultExit.at_traverse` calls `at_post_traverse` only from its successful `move_to` branch (`.venv/.../evennia/objects/objects.py:3733-3735`).
- `typeclasses/exits.py:143-150`: `MovementCostMixin.at_post_traverse` runs `after_successful_movement`.
- `typeclasses/exits.py:21-59`: the helper charges the clock first (`charge_movement`), then records arrival, follows companions, and observes room entry. `charge_movement` (`world/rules/movement.py:12-38`) calls `WorldClock.advance` and can raise; `record_arrival`, `follow_companions`, and `observe_room_entry` are each exception-isolated or player-gated, so the charge is the realistic raiser — but a later step or a commit failure must also be compensable.
- `web/webclient/actions/exploration_actions.py:345-348`: `_move_adapter` catches the traversal exception and returns `move_failed` without checking location.
- Telnet `ExitCommand.func` and `commands/scene.py:108` call `at_traverse` directly; neither Evennia's command handler nor the WebClient action dispatch opens an outer transaction (confirmed: `CmdCast` analysis in the archived `fix-time-skip-atomicity` change and inspection of the dispatch path).
- Evennia in-process caches survive Django rollback: the shared idmapper instances keep `db_location`, `ContentsHandler` dicts (`models.py:281-282`, `models.py:339-356`), and the per-object attribute backend cache (`evennia/typeclasses/attributes.py:528-614`, `_cache` dict) mutated. This is the same class of problem `fix-clock-rollback-cache-sync` addresses for clock callback-owned surfaces.

House patterns this design reuses: the shared snapshot/restore dispatch in `world/rules/surfaces.py` (`attribute_snapshot` / `restore_attribute_best_effort` — restores the value and refreshes Evennia's attribute cache, degrading to `reset_cache()`), and `WorldClock.advance`'s own transaction-plus-restore structure (`world/rules/clock.py:316-339`).

## Goals / Non-Goals

**Goals:**
- Movement settles all-or-nothing: location, clock cost, map knowledge, companion following, and onboarding either commit together or the player is back at the source room with every cache coherent.
- One deterministic enforcement point inside `at_traverse` so Telnet `ExitCommand`, the WebClient `_move_adapter`, and the scene-door command all inherit the guarantee without per-path changes.
- Every exit lineage is covered: stock `Exit`/`CostedXYZExit` via the mixin, `WildernessGateExit` entry, `WildernessReturnExit` return and ordinary wilderness step.
- Compensation is deterministic and testable, including commit-time rollback (cache reconciliation without an exception inside the settlement steps).

**Non-Goals:**
- Changing the settlement order or charging semantics inside `after_successful_movement`.
- Compensating the Evennia `move_to` hook quirk on the **mixin lineage**: when a hook (`at_object_receive` etc.) raises after relocation, `move_to` returns `False` without an exception and `DefaultExit.at_traverse` returns `None` on both branches, so the plain-exit boundary cannot detect it. The wilderness lineages return real booleans and ARE compensated via the falsy-return trigger (D1). The mixin-lineage residual is pre-existing Evennia behavior on a different surface.
- Extending the clock's snapshot surface set (callback-owned surfaces such as `quest_log` deadline writes): owned by `fix-clock-rollback-cache-sync`; this change consumes that change's registry seam through a forward declaration.
- Designing `fix-cast-clock-settlement` (out-of-combat cast) internals; that change composes the same snapshot/restore idioms on its own command surface.

## Decisions

**D1 — The boundary is a deterministic `world/rules` module, one entry per traversal.**
New `world/rules/movement_settlement.py` exposes `settle_movement(traversing_object, source_location, *, traverse, wilderness_coordinates, wilderness_source_coordinates)` where `traverse` is the exit's own traversal body. Shape:

```python
snapshot = _snapshot_movement_state(...)          # pre-move state, see D2
try:
    with transaction.atomic():
        result = traverse()
except Exception:
    _compensate(snapshot)                          # runs after the rollback
    raise
if not result and traversing_object.location is not source_location:
    _compensate(snapshot)                          # falsy-return trigger (wilderness lineages)
    return result
return result
```

The `except` sits outside the `with`, so compensation never writes inside a broken transaction (Django forbids writes after rollback inside `atomic`). Compensation also triggers without an exception when `traverse()` returns a falsy value **and** the traverser relocated anyway: the wilderness lineages (`WildernessGateExit`, `WildernessReturnExit`) return real booleans, and a `move_to` hook that raises after relocation makes them return `False` with the location already changed — the same partial-move bug class. The mixin lineage cannot see this case (`DefaultExit.at_traverse` returns `None` on both branches) and keeps "no return-value inspection"; that residual is documented in Non-Goals. On compensation, the WebClient/Telnet callers keep their existing error handling; the boundary re-raises the original exception (or surfaces the falsy-return failure) so `move_failed` still fires — now truthfully. The module lives in `world/rules` because it is canonical game-state machinery; `typeclasses/exits.py` remains the presentation seam that delegates to it (same split as `charge_movement`). *Alternative considered: compensating inline in `after_successful_movement` — rejected because relocation already happened before that hook, so no transaction can cover the move itself.*

**D2 — Snapshot scope: locations, wilderness bookkeeping, every surface the settlement can write, and the clock seam.**
Before the transaction, `_snapshot_movement_state` records:
- The traverser's pre-move location and wilderness registration (`ndb.wilderness` script identity and its `itemcoordinates` entry), when involved.
- Every co-located companion candidate, using exactly `follow_companions`' co-location predicate (`world/rules/party.py:341-359`: room match or wilderness registration match) — the same set the follow step will move. Candidate discovery replicates `follow_companions`' per-NPC exception isolation (`party.py:265-272`): a stale or corrupt companion is skipped, never allowed to abort the settlement before it starts.
- The involved wilderness script's full bookkeeping — `itemcoordinates`, `rooms`, and `unused_rooms` (all `AttributeProperty`s). These are object-keyed dicts: snapshots are **shallow** copies (shared object references, never `deepcopy`), and the restore writes the shallow copy back, because the shared `restore_attribute_best_effort` deepcopies and would choke on live Evennia objects. For the gate entry the traverser is not yet registered, so the script is resolved by lookup (`search_script(WILDERNESS_NAME)`); for steps it is the traverser's `ndb.wilderness`.
- The traverser's attribute surfaces the settlement may write: `map_knowledge`, the onboarding attrs `guide_progress`/`onboarding_beat`/`first_arrival_seen` (`typeclasses/characters.py:17-20`), and the quest-observation surfaces that the wrapped relocation itself can write — the traverser's `quest_log` and the pin/state surfaces of the destination room (`pin_reasons`, and `interacted` on `InstanceRoom`), because `QuestObservableRoomMixin.at_object_receive` → `observe_room_entry` (`world/quests/room_observation.py:143-148`) and `InstanceRoom.at_object_receive` (`typeclasses/rooms.py:125-133`) fire inside `move_to`'s hook 8, before the charge. These reuse the quest module's own helpers (`snapshot_quest_log`/`restore_quest_log`/`snapshot_pin_reasons`/`restore_pin_reasons`, `world/quests/transitions.py:83-98`) to avoid drift. `follow_companions`' trailing `_reobserve_quest_arrival` can trigger the same writes, which is why the snapshot must precede the whole traversal.
- The clock's advance surfaces through the seam the parallel `fix-clock-rollback-cache-sync` change settles: `build_advance_snapshot_registry(...)` merged with the clock-tick snapshot (`_snapshot_clock_tick`/`_restore_clock_tick`), built before the outer transaction opens (that change's D6 mandates exactly this composition). Until that change lands, the movement boundary falls back to the existing `_ADVANCE_ENTITY_SURFACES` declaration and keeps a guarded integration test; the seam is forward-declared, never faked.

For non-`PlayerCharacter` traversers the surface part reduces to nothing (charge/record/follow/observe are internal no-ops); only locations and wilderness bookkeeping are snapshotted. *Alternatives considered: relying on Django rollback alone — rejected: rollback reverts rows but not idmapper/attribute-cache state (verified in Context), which is the exact cache divergence this change must eliminate; and leaving quest-observation surfaces to the clock change — rejected: room observation is triggered by the traversal itself, not by a clock stage, so the clock change's registry cannot cover it.*

**D3 — Compensation: real relocations through Evennia's own machinery, with a direct-cache fallback.**
`_compensate` runs in a fixed, deterministic order and is best-effort with `log_warn` per step (a failure degrades to the next step, never silently leaves the primary relocation undone, and never masks the original failure):
1. **Traverser**: if still at the post-move location, move it back to `source_location` with `move_to(..., quiet=True, move_hooks=False)` — the same hook-free relocation `follow_companions` uses leaving the wilderness. When the traverser entered the wilderness, first return it to the grid room with that quiet `move_to`, then call the wilderness script's `at_post_object_leave` to deregister `itemcoordinates` (mirrors `world/rules/party.py:283-286`). When the move was an ordinary wilderness step, restore the registration with `wilderness.move_obj(traverser, wilderness_source_coordinates)` (the contrib recycles and recreates rooms; node IDs are coordinate-derived, so knowledge semantics are preserved). When the move was the wilderness grid-return branch (wilderness → grid), the same `move_obj(traverser, wilderness_source_coordinates)` re-registers the traverser in the wilderness bookkeeping at the source coordinates — a plain `move_to` back cannot do this because the source wilderness room may already be recycled.
2. **Companions**: every companion whose post-failure location or wilderness registration differs from its snapshot is moved back with the same primitives (grid: quiet `move_to`; wilderness: `move_obj` or quiet `move_to` plus `at_post_object_leave`).
3. **Wilderness bookkeeping**: restore the script's `itemcoordinates`, `rooms`, and `unused_rooms` from the shallow snapshots. This is mandatory, not optional: the rollback deletes freshly created room/exits rows, but the in-memory bookkeeping keeps them, and step 1's `at_post_object_leave` → `_destroy_room` would append the rolled-back zombie room to `unused_rooms`, poisoning the next `_create_room` pop.
4. **Fallback**: if any relocation above fails or raises, force-reconcile the Evennia cache surfaces directly: assign the instance's `db_location` through the `location` property, save, and re-initialize the source and destination `contents_cache.init()`; the property setter is preferred because it performs the same contents add/remove as `move_to` (`models.py:349-356`), and `init()` is the belt-and-braces refresh the finding calls for.
5. **Attributes**: restore every snapshotted surface — advance/registry surfaces, `map_knowledge`, onboarding attrs, quest surfaces — with `restore_attribute_best_effort` (surfaces.py) and the quest module's `restore_*` helpers, which both write the durable value and refresh the attribute backend cache.

*Alternatives considered: pure Django rollback plus `attributes.reset_cache()` and `contents_cache.init()` only — rejected: resetting caches loses no data but hides divergence; the house pattern (snapshot/restore) is what `clock.py`, `action.py`, and `party.py` already use, keeps values exact, and matches the finding's remediation wording.*

**D4 — Nested transaction semantics are the recovery order.**
The boundary's `transaction.atomic()` is the outer transaction; `WorldClock.advance`'s own `atomic` degrades to a savepoint. On advance failure: the savepoint rolls back, the clock runs its own restore (which refreshes the caller-supplied entity caches — the traverser is in that set), the boundary's outer rollback reverts the relocation row, and `_compensate` reconciles everything else (locations, contents caches, wilderness bookkeeping, and the boundary's own surface snapshots). On outer-commit failure (the `with`-block exit raises): the clock restore never ran, so the boundary's D2 snapshots — including the merged `build_advance_snapshot_registry` and clock-tick surfaces, per D6 of the parallel change — are the sole recovery for advance-touched surfaces. This is why the movement boundary snapshots them rather than delegating entirely to the clock.

**D5 — One enforcement point inside `at_traverse`, all lineages, no per-path client changes.**
- `MovementCostMixin.at_traverse` (new override, `typeclasses/exits.py`) opens the boundary around `super().at_traverse(...)`, covering `Exit` and `CostedXYZExit` (neither `DefaultExit` nor `XYZExit` overrides `at_traverse`; MRO reaches the mixin). `at_post_traverse` is untouched, so `after_successful_movement` ordering and the existing source-inspection test stay valid.
- `WildernessGateExit.at_traverse` (already fully overridden) wraps its body — `at_pre_move` veto, `enter_wilderness`, messaging, `after_successful_movement`.
- `WildernessReturnExit.at_traverse` wraps both branches: the special-cased grid return and the `super().at_traverse()` ordinary-step fallback.
The WebClient adapter, `ExitCommand`, and the scene-door command need no production changes: they call `at_traverse`, which is the boundary. *Alternative considered: wrapping in `_move_adapter` and `ExitCommand` separately — rejected: two enforcement points, and the Telnet/scene paths would remain broken.*

**D6 — Truthful failure reporting.**
The boundary re-raises after compensation. The WebClient `_move_adapter` `except` path therefore reports `move_failed` only after the player is back at the source; the `actor.location is source_location` success check and the `in_combat` re-check are untouched. No adapter logic change; a test asserts the compensated state through the real adapter.

## Risks / Trade-offs

- **Per-move snapshot cost** → Bounded and small: one player, at most four companion candidates, a few attribute dicts, two room-surface dicts, and three wilderness bookkeeping dicts; attribute surfaces use the house `deepcopy` snapshot, wilderness bookkeeping uses shallow copies. `clock.py` already pays the same cost for every advance.
- **Wilderness room recycling during compensation** → The contrib's `_destroy_room` may recycle the entry room after `at_post_object_leave`; the grid room is never recycled (it is the source), and recreation yields a coordinate-equivalent room. Node IDs derive from coordinates (`map_knowledge._derive_node_id`), so knowledge semantics are unaffected. The rolled-back-room zombie risk (`_destroy_room` appending a row-deleted room to in-memory `unused_rooms`) is neutralized by restoring all three bookkeeping dicts from shallow snapshots (D3 step 3).
- **Commit-failure is not reproducible inside `EvenniaTest`** → Django `TestCase` wraps every test in its own `transaction.atomic()`, so the boundary's block is always a nested savepoint there; `set_rollback(True)` rolls back the savepoint silently without raising (Django's own `TestCase._rollback_atomics` uses the same pattern), so it can never exercise the boundary's `except`. The post-follow failure test therefore uses a genuine raise from a settlement step, and the commit-failure cache-reconciliation scenario is verified by a direct unit call to the compensation function against a manually constructed divergent in-process state.
- **Clock callback-owned surfaces (e.g. `quest_log` deadline writes, NPC schedule state) written during the move's advance** → Covered through the `build_advance_snapshot_registry` seam mandated by the parallel change's D6; until that change lands, the movement boundary restores the existing declared surface set and the registry seam is forward-declared with a guarded test (no overlap: the parallel change owns the registry's completeness).
- **Out-of-band art generation** → `ensure_scene_asset` (art-queue) fires inside `at_object_receive`; a rolled-back movement cannot retract an already-queued generation job. Accepted residual (fire-and-forget, cosmetic-only surface).
- **Existing tests asserting "mixin SHALL NOT override `at_traverse`"** → That contract is a main-spec requirement being explicitly MODIFIED by this change; the delta spec carries the full updated requirement and its scenarios so the traceability ID stays stable.
- **`move_to` hook exceptions that relocate-then-return-`False`** → Compensated on the wilderness lineages (D1's falsy-return trigger); not detectable on the mixin lineage because `DefaultExit.at_traverse` returns `None` on both branches (Non-Goals).

## Migration Plan

Unreleased project with no users; no data migration. The compensation runs only on the failure path; successful moves take the same transaction-shaped path with the same observable effects. Rollback strategy: revert the change — no persisted schema or state format changes.

## Open Questions

- None outstanding: the `fix-clock-rollback-cache-sync` design (D6) has settled the advance-surface seam (`build_advance_snapshot_registry` plus clock-tick snapshot/restore), which this change consumes; integration verifies the merged registry covers the movement case once that change lands.
