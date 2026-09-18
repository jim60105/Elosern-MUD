## 0. Ground rules (apply to every task)

- This is the single-writer zone: settle nothing differently. Handler registry wiring
  (`register_effect_handler("...", _handle_...)` block) is read-only for this change.
- Event tags (`buff_applied|...`, `self_buff_applied|...`, `equipment_immune|...`,
  `sexual_transition|...`, `divine_*|...`), `frozenset()`/`frozenset({"buffs"})`, and
  `RejectedAction` reasons/messages stay byte-identical.
- No command key/alias/syntax change → `docs/game/commands.md`, `docs/game/command-reference.md`,
  `tests/test_command_docs.py` untouched and green by construction.
- Evennia tests: `MUD_TEST_SETTINGS=1` via the Bash tool's `env` input, e.g.
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb <label>`.

## 1. Buff handler pair

- [x] 1.1 In `world/rules/action.py`, add file-local helpers per design D1/D2:
  `parse_effect_key`, `resolve_source_tier` (keeps the
  `# observability: ignore R2: nonspell or out-of-tier skill safely falls back to apprentice rung`
  comment verbatim at the moved `except Exception`),
  `source_attribution_kwargs`, `recovery_snapshot_kwargs(..., id_fallback: bool)`,
  `stage_buff_pending(..., effect_set)`. Keep the deferred imports
  (`world.skills.cost_tiers.spell_tier_for`, `world.rules.combat_modifiers.evaluate_combat_modifiers`,
  `world.rules.stored_sexual_reads.stored_sexual_level`) deferred inside the helpers.
- [x] 1.2 Rewrite `_handle_buff_apply` (669-787) as the helper sequence with
  `id_fallback=True`, target iteration + per-target equipment-immunity via
  `stage_buff_pending(target, key, kwargs, definition, frozenset())`. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_buffs` and
  `... world.rules.tests.test_effect_handlers`.
- [x] 1.3 Rewrite `_handle_self_buff_apply` (790-901) with `id_fallback=False`,
  `stage_buff_pending(actor, key, kwargs, definition, frozenset({"buffs"}))`, and the
  `self_buff_applied|` tag. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_sexual_event_self_arming`
  (self-arming exercises the self-buff route),
  `... world.rules.tests.test_cmd_cast`, `... world.rules.tests.test_stateful_spells`.
- [x] 1.4 Review checkpoint: `git diff` shows the ONLY behavioral differences between the two
  handlers are (a) kwargs seeding — buff passes `source_kwargs=context.get("buff_kwargs", {})`
  while self-buff seeds empty and must NEVER read `buff_kwargs` (design D2 item 1; the
  attribution-spoofing tests `test_effect_handlers.py::test_caller_supplied_source_pk_cannot_override_attribution`
  and `test_erosion_leech.py` are the proof), (b) `id_fallback`, (c) `effect_set`, plus the tag
  prefix. Any diff beyond those four is a defect.

## 2. Sexual event family

- [x] 2.1 Add `_stage_apply_event(recipients, event_name, context)` per design D3 (lambda
  capture `r=r`; ImportError → `RejectedAction(EFFECT_RESOLUTION_FAILED,
  "sexual-transition rules are unavailable (change 7b)")` text byte-identical).
- [x] 2.2 Rewrite `_handle_sexual_event` (979-1025), `_handle_actor_sexual_event`
  (1028-1079, observer gate stays BEFORE the staging call), `_handle_target_sexual_event`
  (1082-1137, recipients `targets` minus actor), `_handle_act_pair_event` (1141+ ,
  pair resolution + `None` short-circuit stay). Each keeps its own event-name parse and
  rejection message. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_sexual_act_effects`,
  `... world.rules.tests.test_sexual_transitions`, `... world.rules.tests.test_sexual_resist`,
  `... world.rules.tests.test_sexual_resist_cast_wiring`.

## 3. Divine four-member family

- [x] 3.1 Add `_stage_non_actor_targets(targets, actor, tag, apply_for)`; rewrite
  `_handle_divine_pleasure_max` (1311-1350, two-call lambda + `|100` tag),
  `_handle_saturate_sensitivity` (1508-1537), `_handle_mark_submission` (1587-1619,
  `str(actor.id)` NOT `_entity_key(actor)`), `_handle_restore_purity` (1622-1650) as
  one-liner lambdas through it. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_divine_veil_cast` (covers divine routes),
  `... world.rules.tests.test_sexual_act_effects`, `... world.rules.tests.test_effect_handlers`.
  If any divine-mutator test lives only in `test_sexual_unlock.py` /
  `test_sexual_event_self_arming.py`, run those too (grep
  `divine_pleasure_max|saturate_sensitivity|mark_submission|restore_purity` in
  `world/rules/tests/` first and run every hit).

## 4. Economy buy/sell

- [ ] 4.1 In `commands/economy.py`, add `_ShopCommandBase._parse_trade_args(verb)` and
  `_trade_error_message(error, table, verb)` per design D5; move the two message dicts to
  module constants `BUY_ERROR_MESSAGES` / `SELL_ERROR_MESSAGES` byte-identical to the current
  literals; rewrite `CmdBuy.func`/`CmdSell.func` bodies. Do NOT touch `key`, `aliases`,
  `locks`, `help_category`, or docstrings. Verify:
  `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb commands.tests.test_command_branch_behaviour` and
  `... commands.tests.test_guild_economy_commands` and
  `... tests.test_command_docs`.
- [ ] 4.2 Confirm the command surface is textually untouched:
  `git diff -- docs/game/` is empty.

## 5. Wave close-out verification

- [ ] 5.1 `uv run --locked python -m tools.spec_traceability check` unchanged-passes (no
  annotation moved off a renamed method — none are renamed).
- [ ] 5.2 `uv run --locked python -m tools.observability_lint check` passes; the moved R2
  exemption comments survived the cut — the duplicated tier-block pair merges into the
  single `resolve_source_tier` helper `except`, so the `observability: ignore R2` count in
  `world/rules/action.py` is 6 (pre-change 7: the tier-block comments at 713/844 collapse
  into one; 2226, 3002, 3100, 3190, 3200 unchanged).
- [ ] 5.3 Pipeline smoke: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_action_pipeline_rejections`
  and `... world.rules.tests.test_action_preview` green.
- [ ] 5.4 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract`
  green with no manifest edit; `git diff --check` clean.
