## Why

`world/rules/action.py` — the deterministic settlement surface and the single writer — carries
its largest duplication cluster:

- `_handle_buff_apply:669` (119 lines) and `_handle_self_buff_apply:790` (112 lines) are ~80%
  identical: effect-id parse, source-tier resolution (`spell_tier_for` with the try/except
  學徒 fallback), damaging-gauge-rate source attribution, divert `source_skill` defaulting,
  recovery-policy snapshot kwargs, and the equipment-immunity neutralization staging. One
  documented difference exists (the recovery block's `actor.id` source_pk fallback — buff has
  it, self-buff does not) and must be preserved as a parameter, not silently unified.
- `_handle_sexual_event:979`, `_handle_actor_sexual_event:1028`, `_handle_target_sexual_event:1082`,
  and `_handle_act_pair_event:1141` share the event-name parse, the deferred
  `sexual_transitions.apply_event` import seam, the sexual-context copy, and the
  `sexual_transition|<key>|<event>` PendingEffect staging — four copies of the same import
  fallback error text.
- The divine family `_handle_divine_pleasure_max:1311`, `_handle_saturate_sensitivity:1508`,
  `_handle_mark_submission:1587`, `_handle_restore_purity:1622` are the same
  per-non-actor-target staging loop with a different apply lambda and tag.
- `commands/economy.py`: `CmdBuy.func:88` and `CmdSell.func:134` duplicate arg parsing
  (item key + optional quantity with the identical 數量必須是正整數。 rejection) and the
  TradeReason→message table shape.

Every one of these is settlement-critical: a fix (attribution spoofing, resist-gate
interaction, tier fallback) applied to one copy and missed in its twin is a rules divergence
on the single-writer boundary.

## What Changes

- Extract file-local helpers in `world/rules/action.py` (no new module — the helpers are
  handler-private):
  `parse_effect_key(effect_id)`, `resolve_source_tier(context)`,
  `source_attribution_kwargs(definition, key, actor, source_skill)`,
  `recovery_snapshot_kwargs(definition, key, actor, context, *, id_fallback: bool)`,
  `stage_buff_pending(target, key, kwargs, definition)`,
  `stage_sexual_events(recipients, event_name, context)`,
  `stage_per_non_actor_target(targets, actor, tag_for, apply_for)`.
  Handler names, signatures, registry wiring (`register_effect_handler` calls), event tags,
  `frozenset()`/`frozenset({"buffs"})` sets, and rejection reasons stay byte-identical.
- Extract `_ShopCommandBase` helpers in `commands/economy.py`:
  `parse_trade_args(verb)` and `trade_error_message(error, table, verb)`. Keys, aliases,
  help text, and every 中文 message string stay byte-identical — the command surface gate
  (`docs/game/commands.md`, `docs/game/command-reference.md`, `tests/test_command_docs.py`)
  is untouched by construction.
- Zero behavior change; no new log event ids; no test file renamed.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
None — `skip_specs: true`. The governed behaviors are already in `buff-handler-integration`,
`action-resolution-pipeline`, `combat-resolution`, the sexual-effect capabilities, and the
shop-economy capabilities; requirements stay exactly as shipped, and the existing
`covers_requirement` annotations stay attached to the existing handler/economy tests
(`world/rules/tests/test_effect_handlers.py`, `test_buffs.py`, `test_sexual_act_effects.py`,
`commands/tests/test_command_branch_behaviour.py`, `test_guild_economy_commands.py`).

## Impact

`world/rules/action.py` (bodies delegate to file-local helpers; registry section untouched),
`commands/economy.py` (`_ShopCommandBase` gains two helpers; `CmdBuy.func`/`CmdSell.func`
shrink). No command-surface change; `.github/evennia-shards.json` untouched; no payload,
event, or docs change.

## Batch

- depends-on: (none) — but lands AFTER the wave-A `rules-wallet-rollback-helpers` if both
  are queued concurrently only for supervisor tidiness; they are file-disjoint.
- **Single-writer zone warning (checked against `openspec list --json`):** the three active
  changes were inspected for file overlap —
  - `elementless-damage-effect`: its proposal explicitly lists `world/rules/action.py` as
    untouched; it edits `world/skills/{effects,registry}.py` and a `world/rules/progression.py`
    docstring. **No textual conflict** with this change.
  - `martial-arts-catalog`: its design names `world/rules/action.py` only to declare a
    settlement change *out of scope*; it appends rulebook YAML rows (`buffs.yaml`,
    `combat_modifiers.yaml`, `status_display.yaml`) — data this change's handlers read, not
    edit. **No textual conflict.**
  - `divine-mystery-catalog`: edits `world/skills/registry.py`, `world/rules/tests/test_divine_mystery_gate.py`,
    a new `world/rules/tests/test_divine_mystery_progression.py`, and
    `.github/evennia-shards.json` (append-only manifest) — its divine nodes reuse *already
    shipped* handlers ("the engine work has landed"); **it does not edit `action.py` or
    `economy.py`**. Its manifest append conflicts with *any* concurrent manifest edit;
    this change never edits the manifest, so order-free.
- If any of the three ever gains an `action.py` task during apply, rebase whichever merges
  second — the helper functions this change adds are new names, so conflicts stay textual.

## Non-goals

- The `_handle_*_sexual_event` family keeps four public handlers (recipient scope is the
  contract); only their shared mechanics are extracted.
- `_handle_pleasure_peak` / `_handle_clamp_shame` / `_handle_confer_growth_rate` have shapes
  distinct enough from the four-member family to stay file-local.
- `world/rules/economy.py` (the rules-side writer) is untouched; this change only de-dupes
  the `commands/economy.py` presentation layer.
