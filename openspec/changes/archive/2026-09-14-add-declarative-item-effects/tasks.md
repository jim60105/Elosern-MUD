# Tasks: add-declarative-item-effects

Depends on `extract-shared-effect-appliers` being implemented first — tasks in group 4 bind to the
entry points it publishes. Design decisions referenced below live in `design.md` (D1–D7).

## 1. Pin current behavior before changing it

- [x] 1.1 Add a regression test fixing the current observable behavior of all four shipped usable
  items: restored amounts (40/120/40), the `hp_full`/`mp_full`/`no_debuffs` reason codes, consumption
  counts, and the six-second out-of-combat advance. Verify it passes against the unmodified tree — it
  is the contract the rewrite must reproduce (design Risks).

## 2. Vocabulary, dataclasses, and loader

- [x] 2.1 Create `world/rules/item_effects.py` with `ItemStat` (hp/mp/sp/pleasure), `ItemTargetScope`
  (self/single/all-allies/all-enemies/all), and the three frozen effect dataclasses plus
  `ItemEffectProfile` (D1). Verify each dataclass rejects a malformed construction in a unit test.
- [x] 2.2 Implement the verb-discriminated entry parser: exactly one of `stat`, `apply_status`,
  `remove_status` (D2). Verify the two-verb and verbless entries both fail — the
  `item-effect-rulebook` delta's first two scenarios.
- [x] 2.3 Implement stat-adjustment validation: closed stat vocabulary, non-zero integer amount,
  `abs(amount) <= MAX_EFFECT_AMOUNT` (D6). Verify all four failure scenarios in the delta (negative
  accepted, zero rejected, out-of-bound rejected, unknown stat rejected).
- [x] 2.4 Implement status validation: `apply_status` accepts only a concrete `BUFF_DEFINITIONS` key
  and rejects selectors; `remove_status` accepts a concrete key or `all`/`positive`/`negative`; an
  unknown key fails in either position. Verify the delta's four scenarios.
- [x] 2.5 Implement two-way registry alignment: the rulebook's item-key set equals exactly the usable
  registry keys, and every entry declares at least one effect. Verify the orphan, missing, and empty
  scenarios all fail startup.
- [x] 2.6 Reject any scope other than the acting entity, with a message naming
  `add-item-effect-targeting` (D5). Verify the delta's two scope scenarios.
- [x] 2.7 Reject an item declaring two stat adjustments to the same stat (D3). Verify with a test
  asserting the load failure and its message.

## 3. Registry and rulebook migration

- [x] 3.1 Delete `ItemEffectKey` from `world/lore/items.py` and slim `ItemUseMechanics` to
  `{consumable, combat_allowed}`, updating its `__post_init__` validation. Verify
  `grep -rn "ItemEffectKey"` returns zero hits outside archived openspec changes.
- [x] 3.2 Re-key `world/rules/rulebook/item_effects.yaml` to `items:` by item key, migrating the four
  shipped items at identical magnitudes (`hp +40`, `hp +120`, `mp +40`, `remove_status: negative`),
  keeping `item_use_seconds: 6`. Verify the loader accepts it and every magnitude matches task 1.1's
  pinned values.
- [x] 3.3 Update `world/lore/tests/test_items.py` and `world/tests/synthetic_data.py` for the slimmed
  mechanics. Verify both suites pass.
- [x] 3.4 Rewrite `world/rules/tests/test_equipment_combat_wiring.py`: its `ItemUseMechanics(
  effect_key=...)` construction at `:188`, its `_HEAL_AMOUNT` derivation from
  `ITEM_EFFECT_RULES[ItemEffectKey.SELF_HEAL].amount` at `:191`, and its `preflight.plan.amount` /
  `preflight.plan.gauge_restored` assertions at `:693-694` all reference shapes this change removes.
  Verify the rewritten assertions read the equivalent values off the new `ItemEffectStep` list.

## 4. Settlement rewrite

- [x] 4.1 Replace `ItemUsePlan`'s single-effect fields with `steps: tuple[ItemEffectStep, ...]`, each
  carrying its effect, its target, and the magnitude actually applicable (D3). Verify the dataclass is
  frozen and fully computed before any write.
- [x] 4.2 Rewrite `preflight_item_use` to resolve the profile, compute one step per effect, and reject
  only when no step is effective. Verify per-family effectiveness against current state — the
  `item-use-resolution` delta's ADDED requirement.
- [x] 4.3 Implement the reason-code fallback: the shared code when every ineffective step agrees, else
  `no_effect` (D4). Verify both new preflight scenarios plus the three pinned single-effect reason
  codes from task 1.1.
- [x] 4.4 Add `SP_FULL`, `PLEASURE_FULL`, `NO_EFFECT`, `STATUS_BLOCKED`, and `NOTHING_TO_REMOVE` to
  `ItemUseReason` and their Traditional Chinese messages to `world/rules/service_messages.py` (D5c).
  Keep `NO_DEBUFFS` as the reason for an ineffective `negative` selector so 受洗聖水's shipped
  scenario survives verbatim. Verify every `ItemUseReason` member renders a message (a completeness
  test over the enum).
- [x] 4.5 Rewrite `_apply_plan` to walk the ordered steps, dispatching each verb to its shared entry
  point: `_write_gauge` for hp/mp/sp, `apply_pleasure_gain` for pleasure, `apply_buff` for
  `apply_status`, `remove_by_selector` for `remove_status`. Verify `world/rules/items.py` contains no
  branch keyed to an individual item or effect identity — the delta's "Holy water has no dedicated
  branch" scenario.
- [x] 4.6 Delete `_EFFECT_GAUGES`, `_FULL_REASON_BY_GAUGE`, `_GAUGE_NOUN_ZH`, and the
  `BLESSED_CLEANSE` branches. Verify the module no longer imports `ItemEffectKey`.
- [x] 4.7 Add the sexual-state surface to `ItemTouchedJournal` so a pleasure write can be rolled back
  (D7), leaving the journal single-entity. Verify with a fault-injection test that a failure after a
  pleasure write restores pleasure, arousal, wetness, and climax phase together.

## 5. Event log

- [x] 5.1 Emit one `item_used` entry per effective step, dropping `effect_key` and carrying
  `{item_key, consumable, stat, amount}` or `{item_key, consumable, status_keys, count}`. Verify the
  delta's three EventLog scenarios, including that a two-effect use emits two entries in declaration
  order.
- [x] 5.2 Build each entry's Traditional Chinese text from the stat or status involved, with no
  per-effect lookup table. Verify the rendered text for an HP restore and a cleanse matches the shipped
  wording from task 1.1.

## 6. Negative and status effects

- [x] 6.1 Add tests for a negative stat adjustment clamping at zero and reporting the actual drop —
  the delta's "A negative stat adjustment stops at zero" scenario.
- [x] 6.2 Add tests for a negative pleasure adjustment: it clamps at zero and the arousal, wetness,
  and climax cascade does not fire on a reduction (design Risks).
- [x] 6.3 Add tests for `apply_status` reaching `apply_buff`, including that an equipment-immunized
  debuff is refused, counts as ineffective, and reports `STATUS_BLOCKED` when it is the item's only
  effect.
- [x] 6.4 Implement the source-qualified instance key for `apply_status` (D5b): pass
  `source_key=f"item:{item_key}"` always, plus `instance_key=f"{status}:item:{item_key}"` when the
  definition declares `stacking: unique_per_source`. Verify that two different items granting one
  `unique_per_source` status produce two live instances, while re-using one item refreshes its own —
  the claim `docs/superpowers/specs/2026-09-14-item-effect-model-design.md` §5.6 makes, which
  `_add_buff`'s `instance_key or definition_key` keying does not give for free.
- [x] 6.5 Add tests for `remove_status` selectors reporting `NOTHING_TO_REMOVE` when they match
  nothing, and for the `negative` selector still reporting `no_debuffs` (D5c).

## 7. Documentation and validation

- [x] 7.1 Rewrite 第六層 of `docs/lore/items.md` for the new field model, and update the pending-effect
  notes in 藥劑 and 性玩具 to state which of them the new model now covers without an enumeration
  extension. Verify no remaining reference to `ItemEffectKey` or `effect_key` in that file.
- [x] 7.2 Update `docs/development/adding-items.md`: the §1 data-location table, §2 question 4, and the
  §5 "new effect needs a spec change" section — adding an effect for an existing verb is now a YAML
  edit. Verify the worked example loads.
- [x] 7.3 Run the full deterministic suite plus task 1.1's regression test, and verify all four shipped
  items reproduce their pinned behavior exactly.
- [x] 7.4 Run `openspec validate add-declarative-item-effects` and the repository's lint/observability
  gate; verify both pass.
