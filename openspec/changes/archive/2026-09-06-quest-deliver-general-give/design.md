# Design: quest-deliver-general-give

Context: change 5 (`quest-deliver-objective`) wired the delivery observer into
`world/rules/npc_intents.py::_transfer_items` only. Change 6 (`quest-deliver-action`) added the
quest-scoped `交付` / `explore.deliver` surfaces. The general give (`CmdGive`) moves registry keys
through its own inventory plans without the observer — the gap recorded in the quest-issuer design
§13 "Follow-up notes from implementation". This change closes it.

## D1: One advance seam, two callers

`_transfer_items`'s advance block is exactly:

```
giver_records_before = {r.quest_id: r for r in read_records(giver)}
delivery = compute_deliver_replacement(giver, receiver, item_key, qty)
if delivery is not None:
    new_records, pin_ops = delivery
    for room, _, _ in pin_ops:
        if room not in pin_snapshots:
            pin_snapshots[room] = snapshot_pin_reasons(room)
    apply_quest_log_delta(giver, list(new_records), pin_ops)
    schedule_delivery_events(giver, giver_records_before, new_records)
```

It is extracted verbatim into a public seam in the same module:

```python
def advance_deliveries_for_transfer(
    giver: Any, receiver: Any, item_key: str, qty: int, pin_snapshots: dict[Any, Any]
) -> None:
```

The seam mutates the caller-owned `pin_snapshots` dict lazily (one snapshot per touched pin room,
captured before the room's first write) and does everything else the block does today.
`_transfer_items` refactors onto it with zero behavior change — the existing
`world.quests.tests.test_deliver` suite is the regression net and must stay green untouched.

Rationale for the module placement: the seam composes inventory-transfer machinery with quest
writes, exactly like `_transfer_items` does today; `world/rules` is the project's general-purpose
deterministic engine, and the give command calling a `world.rules` seam follows the
`交付`-command-calls-`world.rules.quest_delivery` precedent. The quest-side writers it calls
(`compute_deliver_replacement`, `apply_quest_log_delta`, `schedule_delivery_events`,
`snapshot_pin_reasons`) keep their existing homes and signatures — `world/quests` stays the sole
writer of quest state.

## D2: The give advances without quest-scoped refusals

`CmdGive` calls the seam unconditionally after its plans apply. The observer does all the matching:
`compute_deliver_replacement` returns nothing unless the giver holds an active `DELIVER` stage bound
to the receiver for that item key. A give to an unbound NPC therefore transfers and advances
nothing — correct raw-transfer semantics, no new refusal branches, no new message surface.

Mid-fight advancement is accepted. The raw give has no combat contract today; adding the observer
does not add one, and a completed delivery grants no combat advantage. `交付` keeps its combat gate
as the quest-scoped surface's honesty contract. The spec is the authority here: the main
`quest-delivery` requirement already states progress advances from a committed transfer meeting the
three conditions (holder gives, receiver bound, key matches) — `給` is such a transfer.

## D3: Both branches, one transaction each

**Canonical-key branch** (`not to_give`): today the branch commits
`apply_inventory_plan` × 2 inside `transaction.atomic()` and re-raises on failure after
`target.contents_cache.init()`. The branch gains:

1. Before the transaction: `giver_surfaces = _surface_snapshots(caller)`,
   `receiver_surfaces = _surface_snapshots(target)`,
   `pin_snapshots = _pin_snapshots(receiver_plan)` — the same discipline `_transfer_items` uses:
   both parties' inventory, quest log, and traits surfaces, plus the receiver plan's ACQUIRE pin
   rooms captured up front (the addition plan can carry its own pin operations, and the advance
   adds DELIVER rooms to the same dict lazily).
2. Inside the transaction, after both plans apply:
   `advance_deliveries_for_transfer(caller, target, key, quantity, pin_snapshots)`.
3. On any exception: restore all three snapshot groups, then report the safe line
   `物品交接失敗，什麼都沒有發生。` instead of re-raising — matching `_transfer_items`' refusal
   behavior for the same failure class. The existing `target.contents_cache.init()` reconciliation
   is retained before the message: the materialized mirrors created inside the transaction must not
   linger in an already-populated contents cache after the rollback.

**Materialized-object branch**: `_transfer_with_plan` opens its own `transaction.atomic()`. The
branch wraps the call in an outer atomic (nested atomics become savepoints; the outermost governs
the commit), then calls the seam once per distinct registry key in the moved objects' `removals`
tuple with that key's object count. Non-registry objects never enter `removals` (already filtered
to `None`), so unregistrable items can never advance anything. On failure the outer atomic rolls
the move and the key deltas back together; the except path calls the module's existing
`_reconcile_rollback(objs, origin, destination)` for the moved instances' caches, restores the
snapshot groups, and reports the same safe line.

The branch's established refusal stays untouched: `_transfer_with_plan` returning `[]` (a refused
`move_to`) keeps rendering `你無法把物品交給 …` with no rollback machinery — only an exception
raised by the transaction or the seam takes the outer-rollback path. Snapshot groups and the pin
dict are initialized exactly as in the canonical-key branch, including
`_pin_snapshots(receiver_plan)`.

Self-give needs no new guard: both branches already return before transferring when
`target == caller`, and no transfer means no advance.

Implementation note: the numbered-command tests surfaced a pre-existing parse gap in the zh-tw
`NumberedTargetCommand` wrapper — it stripped a leading 「個」 from `self.args` but not from
`self.lhs`, so every rhs-taking command (`給`) mis-parsed `給 2 個 <物品> = <對象>` as the key
「個 <物品>」. The wrapper now strips the classifier from `lhs` too; the numbered give tests pin
the corrected parse.

## D4: Quantity and multi-record semantics are the observer's, unchanged

The give advances by the transferred quantity per key — one invocation per distinct key. The
observer applies its existing rules: every active record bound to the receiver for that key
advances by `min(transferred, its own remaining)`; surplus does not carry. A player giving 2 of a
quantity-2 item completes the stage in one `給`; giving 1 of a quantity-2 item leaves the stage at
progress 1 with the affordance still advertising the remaining 1 — the same semantics
`_transfer_items` and `交付` already produce, so all three movers agree.

## D5: Observability rides existing seams

- `cmd_in` / `cmd_done` bracket every `給` invocation through the repo command base class
  (`commands/command.py`), with the raw args in context — the operator already sees
  `給 治療藥水 = 灰婆婆` at the boundary.
- The two give except paths convert a previously propagating crash into a safe rollback + message,
  which would make `cmd_done` report `outcome=ok` for a fault. They therefore emit
  `log_warn("give_transfer_failed", exc=..., context={char, target, branch, item})` before
  restoring, keeping the exception chain visible at the command boundary.
- The seam schedules the observer's `delivery_progress` events per advanced quest on durable
  commit, identical to `_transfer_items`.
- No `delivery_handover` from the give path: that event is `world.rules.quest_delivery`'s
  quest-scoped boundary (change 6), and the honesty split keeps `給` outside that contract.
  Distinguishing a give-driven advance from an intent-driven one is available from the paired
  `cmd_in`/`cmd_done` and the dialogue-intent traces.

## D6: Tests

Two homes, both already shard-registered:

- `world/quests/tests/test_deliver.py` — the seam's own contract: advance on a matching transfer,
  no-op on an unbound receiver, multi-record `min(qty, remaining)` advance, rollback restores both
  parties byte-for-byte on a `compute_deliver_replacement`/`apply_quest_log_delta` fault, and the
  `_transfer_items` refactor's regression coverage (untouched suite).
- `commands/tests/test_localized.py` — the command integration: registry-key give advances a bound
  delivery (partial via `self.number` and completing), materialized-object give advances including
  a mixed multi-key selection (one advance per distinct key), NPC bound receiver in both branches,
  unbound give transfers without advancing, a mid-combat qualifying give advances (pinning the
  combat decision), a failed advance rolls the give back with the safe message while the receiver's
  ACQUIRE pin state and the materialized mirrors' contents cache are verified restored, and the
  established `EquippedRemovalError` and refused-move outcomes survive; `covers_requirement`
  annotations against the added requirement.

## Risks / Trade-offs

- **`_transfer_items` refactor touches a hot primitive** → mitigated by verbatim extraction and the
  untouched `test_deliver` suite; any behavioral drift fails there first.
- **Branch B's outer atomic nests around `_transfer_with_plan`'s own atomic** → Django nested
  atomics are savepoints; the outermost commit governs. The reconciliation helpers the file already
  uses cover the in-process caches on rollback.
- **Rollback integrity is the completion gate.** The nominal extraction is small; the real work is
  two transaction shapes plus acquisition-pin and contents-cache rollback coverage. The rollback
  regressions gate completion — no landing with them shortcut.
- **Mid-fight advancement via `給`** → accepted deliberately (D2); revisiting means adding a gate
  to a raw verb, which is a product decision outside this change.
- **Possible overlap with `quest-auto-settlement`** (active change) → that change owns
  `world/quests/transitions.py` write paths and completion settlement; this change owns
  `world/rules/npc_intents.py` and `commands/localized/general.py`. Different files; if both land
  in the same window, land this one after, since the seam calls `apply_quest_log_delta` whose
  settlement behavior that change extends.
