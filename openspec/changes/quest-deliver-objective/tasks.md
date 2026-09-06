# Tasks: quest-deliver-objective

## 1. Definition vocabulary

- [ ] 1.1 Add `DELIVER = "deliver"` to `ObjectiveKind` in `world/quests/definitions.py`.
- [ ] 1.2 Add the validation branch: require a registered `item_key`, a positive `quantity`, and
  `requires_bound_targets` true; reject a supplied destination and a supplied monster tier. Each
  rejection names the offending field through the existing `_reject` helper.
- [ ] 1.3 Confirm the closed-vocabulary exhaustiveness checks elsewhere (describe, planner,
  transitions) fail loudly rather than silently skipping the new kind — fix each site the compiler or
  a test surfaces.

## 2. Prose

- [ ] 2.1 `describe_objective` renders the delivery line from `ITEM_REGISTRY[item_key].display_name_zh`
  and the quantity; an unregistered key raises `QuestDescribeError`.
- [ ] 2.2 Confirm `describe_quest_detail` needs no change — it composes the objective line.

## 3. Delivery observer

- [ ] 3.1 New `world/quests/deliver.py` mirroring `world/quests/acquire.py`'s structure: a pure
  `compute_deliver_replacement(giver, receiver, item_key, quantity)` returning
  `(new_records, pin_operations)` or `None`.
- [ ] 3.2 Match rules: the record is `IN_PROGRESS`, its current stage objective is `DELIVER`, the
  objective's `item_key` equals the transferred key, and the receiver's identity is in the record's
  `objective_target_ids`. Advance by the transferred quantity capped at the objective quantity; no
  surplus carry-over; use `fulfill_record_for` and `release_stage_binding` exactly as the acquisition
  observer does.
- [ ] 3.3 Expose no progress-assertion entry point — the computation is reachable only from a
  committed transfer.

## 4. Transfer wiring

- [ ] 4.1 `_transfer_items` in `world/rules/npc_intents.py` calls the observer for the GIVER side
  inside its existing transaction, applying the returned replacement with `apply_quest_log_delta`
  (no nested transaction). The receiver side keeps its existing acquisition pin handling.
- [ ] 4.2 Extend the existing giver-side surface snapshots so a delivery advance rolls back with the
  transfer.
- [ ] 4.3 Emit the delivery progress boundary event through the observability facade with `char`,
  `quest`, and `step` context.

## 5. Tests

- [ ] 5.1 Definition validation tests: valid delivery registers; unregistered item, non-positive
  quantity, unbound targets, supplied destination, and supplied monster tier each reject by name.
- [ ] 5.2 Binding tests: only the bound recipient satisfies the delivery; a same-named unbound
  character does not.
- [ ] 5.3 Progress tests: giver-side transfer advances; wrong item advances nothing; receiving rather
  than giving advances nothing; one oversized transfer advances exactly once with progress capped and
  no surplus carry-over; a terminal record ignores a later matching transfer.
- [ ] 5.4 Purity and atomicity tests: the observer writes nothing on its own; a fault-injected
  transfer restores the quest log, both inventories, and their in-process caches.
- [ ] 5.5 Prose tests: the rendered line carries the registry display name; an unregistered item
  raises.
- [ ] 5.6 Annotate with `covers_requirement` against the new `quest-delivery` and modified
  `quest-progress-tracking` requirement IDs; update `.github/evennia-shards.json` for the new
  integration module.
- [ ] 5.7 Run the observability lint plus the focused quest definition, describe, deliver, and
  npc-intent test modules in the same batch.

## 6. Interim state

- [ ] 6.1 Record in the change that no player-facing delivery verb exists yet: until
  `quest-deliver-action` lands, `DELIVER` advances only through the dialogue-driven transfer. This is
  a deliberate intermediate state, not a shipped feature, and no content should author a delivery
  quest before that change lands.
