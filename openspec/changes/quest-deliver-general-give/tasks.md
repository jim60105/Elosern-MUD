# Tasks: quest-deliver-general-give

## 1. The shared advance seam

- [ ] 1.1 Extract `_transfer_items`'s delivery-advance block verbatim into
  `world/rules/npc_intents.py::advance_deliveries_for_transfer(giver, receiver, item_key, qty,
  pin_snapshots)` and refactor `_transfer_items` to call it. `world.quests.tests.test_deliver` stays
  green untouched.
- [ ] 1.2 Seam-level tests in `world/quests/tests/test_deliver.py`: advance on a matching transfer,
  no-op on an unbound receiver, multi-record `min(qty, remaining)` advance, and a fault-injected
  rollback that restores both parties byte-for-byte.

## 2. The give command advances

- [ ] 2.1 Canonical-key branch: snapshot both parties' surfaces and the pin rooms before the
  transaction — `pin_snapshots` initialized from the receiver plan's ACQUIRE pin rooms — call the
  seam inside the transaction after both plans apply, and on any exception restore the snapshots,
  re-run `target.contents_cache.init()`, and report `物品交接失敗，什麼都沒有發生。` instead of
  re-raising.
- [ ] 2.2 Materialized-object branch: wrap `_transfer_with_plan` in an outer transaction, call the
  seam once per distinct registry key with its moved count after the move, and on failure reconcile
  the moved objects (`_reconcile_rollback`), restore the snapshots, and report the same safe line.
  The established refused-move outcome (`你無法把物品交給 …` for `_transfer_with_plan` returning
  `[]`) stays untouched.
- [ ] 2.3 Command integration tests in `commands/tests/test_localized.py`: registry-key give
  completes a quantity-2 delivery; a partial `self.number` give leaves the stage advertising the
  remainder; a materialized object give advances, including a mixed multi-key selection (one
  advance per distinct key); an NPC bound receiver in both branches; an unbound-recipient give
  transfers without any quest change; a mid-combat qualifying give advances; a fault-injected
  advance rolls the give back with the safe message while the receiver's ACQUIRE pin state and the
  materialized mirrors' contents cache are verified restored; the established
  `EquippedRemovalError` and refused-move outcomes survive; `covers_requirement` annotated against
  the added requirement.

## 3. Documentation

- [ ] 3.1 `docs/game/commands.md`'s `給` row states that handing a quest item to its bound
  recipient advances the delivery and that `交付` is the quest-scoped verb.
- [ ] 3.2 `docs/game/command-reference.md`'s `給` canonical entry's 說明 states the same; the drift
  contract test (`tests.test_command_docs`) stays green.

## 4. Verification

- [ ] 4.1 Focused batch:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  world.quests.tests.test_deliver commands.tests.test_localized tests.test_command_docs
  commands.tests.test_command_branch_behaviour tests.test_evennia_test_optimization_contract`.
- [ ] 4.2 `uv run --locked python -m tools.observability_lint check`,
  `uv run --locked python -m tools.spec_traceability check`, and
  `uv run --locked openspec validate quest-deliver-general-give --strict`.
- [ ] 4.3 `uv run --locked python -m compileall -q world typeclasses commands` and
  `git diff --check`.
