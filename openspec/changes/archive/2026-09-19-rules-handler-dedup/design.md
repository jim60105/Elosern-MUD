## Context

`action.py` handlers are registered by prefix via `register_effect_handler(...)` at module
bottom; each handler is `(actor, targets, effect_id, context, scale) -> list[PendingEffect]`.
Tests drive handlers through the pipeline and patch collaborators on the `world.rules.action`
module (e.g. `patch("world.rules.economy.buy")` is economy-side; action-side tests patch
`apply_buff` / `equipment_immune_buff_keys` / `apply_event` import seams on the tested
modules). Extraction must therefore keep every collaborator resolved from
`world.rules.action` module globals at call time.

## Decisions

### D1 — File-local helpers, not a new module

All five helpers live above the handlers in `world/rules/action.py`. A new
`world/rules/buff_staging.py` would move `BUFF_DEFINITIONS`, `_is_damaging_gauge_rate`,
`get_recovery_policy`, `equipment_immune_buff_keys`, and the deferred
`combat_modifiers`/`stored_sexual_reads` imports into a new import graph and break
module-global patch seams tests rely on. File-local extraction removes ~150 duplicated lines
with zero seam risk.

### D2 — The buff/self-buff difference is an explicit parameter

The two handlers differ in exactly TWO load-bearing places, both preserved as parameters,
never silently unified:

1. **kwargs seeding.** `_handle_buff_apply` seeds `kwargs = dict(context.get("buff_kwargs", {}))`
   (`action.py:684`) — the caller-supplied attribution channel, exercised by
   `test_effect_handlers.py::test_caller_supplied_source_pk_cannot_override_attribution` and
   `test_erosion_leech.py` — while `_handle_self_buff_apply` seeds `kwargs = {}`
   (`action.py:815`) and NEVER reads `context["buff_kwargs"]`. The shared helper takes a
   `source_kwargs: Mapping | None` parameter (buff passes `context.get("buff_kwargs", {})`,
   self-buff passes nothing); a naive merge that lets self-buff read `buff_kwargs` would open
   the exact attribution-spoofing seam the named tests defend.
2. **recovery-policy fallback.** `_handle_buff_apply` falls back to
   `kwargs["source_pk"] = int(actor.id)` when `pk` is not a positive int,
   `_handle_self_buff_apply` does not. `recovery_snapshot_kwargs(..., id_fallback: bool)` carries
   that choice (`True` for buff, `False` for self-buff).

An accidental unification of either is visible in one diff line instead of being silent.
Likewise the equipment-immunity staging moves to
`stage_buff_pending(target, key, kwargs, definition)` which returns the neutralized
`PendingEffect` or the real one; self-buff calls it with `actor` as target, keeping its
`frozenset({"buffs"})` tag set by a parameter too (`effect_set`).

### D3 — Sexual staging shares the import seam as a generator helper

```python
def _stage_apply_event(recipients, event_name, context):
    try:
        from world.rules.sexual_transitions import apply_event
    except ImportError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual-transition rules are unavailable (change 7b)",
        ) from error
    sexual_context = dict(context.get("sexual", {}))
    return [PendingEffect(r, f"sexual_transition|{_entity_key(r)}|{event_name}",
                          frozenset(), lambda r=r: apply_event(r, event_name, **sexual_context))
            for r in recipients]
```

Each of the four handlers keeps its own recipient expression (`participants(actor, targets)`,
`[actor]` after the observer gate, `targets` minus actor, participants-after-pair-resolution)
and its own event-name rejection message (they differ: `sexual_event requires an event name`,
`sexual_event_target requires an event name`, ...). `_handle_actor_sexual_event` keeps its
observer gate before the call.

### D4 — Divine family: one staging loop, per-handler lambdas

`_stage_non_actor_targets(targets, actor, tag: Callable[[Any], str], apply_for: Callable[[Any], Callable[[], None]])`
stages `PendingEffect(target, tag(target), frozenset(), apply_for(target))` per target where
`target is not actor`. Tags stay the exact current strings
(`divine_pleasure_max|{_entity_key(target)}|100`, `divine_saturate_sensitivity|...`,
`divine_mark_submission|...`, `divine_restore_purity|...`); lambdas stay per-handler
(two-call pleasure sequence, `saturate_sensitivity()`, `mark_submission(str(actor.id))`,
`restore_purity()`).

### D5 — Economy: verb-parameterized parse + message table lookup

```python
def _parse_trade_args(self, usage_verb: str) -> tuple[str, int] | None:
    # "" -> f"用法：{usage_verb} <item_key> [數量]"; bad int -> "數量必須是正整數。"; returns None after msg
def _trade_error_message(self, error, table, fallback_verb_zh: str) -> str:
    # .get(reason, f"{fallback_verb_zh}失敗：{error}")
```

TWO distinct verb-like arguments, never one: the usage line embeds the ENGLISH verb
(`f"用法：buy <item_key> [數量]"`, `commands/economy.py:98`; sell at :144) while the
off-table fallback message is CHINESE (`f"購買失敗：{error}"`, `:119`; sell
`f"販賣失敗：{error}"`, `:165`). A single shared `verb` parameter would ship
`"buy失敗：…"` — a player-visible text regression with NO existing test pinning the fallback
string (`test_command_branch_behaviour.py` exercises only table-covered reasons). So `CmdBuy`
passes `usage_verb="buy"`, `fallback_verb_zh="購買"`, `BUY_ERROR_MESSAGES`; `CmdSell` passes
`usage_verb="sell"`, `fallback_verb_zh="販賣"`, `SELL_ERROR_MESSAGES`. Tables are the exact
current dict literals moved to module constants. The success messages differ enough to stay
inline. `test_command_branch_behaviour.py` patches `commands.economy.buy` / `.sell` module
globals — tables/parse keep resolving from `commands.economy` globals unchanged.

Regression pin: add one assertion to the EXISTING off-table-reason path test (or one new
subTest in `test_command_branch_behaviour.py`) pinning the exact fallback bytes
`購買失敗：` / `販賣失敗：` so the extraction cannot silently recombine the verbs.

## Risks / Trade-offs

- Handler bodies shrink to helper calls, slightly raising the stack depth on rejection paths;
  irrelevant for settlement, and the `RejectedAction` chain types stay identical (helpers
  raise the same `RejectedAction`, never a wrapper).
- The `_stage_apply_event` list-comprehension lambda-capture discipline (`r=r`) must be
  preserved — the tasks call it out as a review checkpoint.
