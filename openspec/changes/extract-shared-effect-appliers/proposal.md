# Proposal: extract-shared-effect-appliers

## Why

The approved item-effect model
(`docs/superpowers/specs/2026-09-14-item-effect-model-design.md` §5.6) requires that every effect
family have exactly one entry point, shared by skills and items, so no effect ever gains a second
increment path. Three of the four entry points it needs are currently private, and one of them is
private *to the wrong module*:

- `_apply_pleasure_gain` lives in `world/rules/action.py` — the cast pipeline — even though it is the
  canonical, order-sensitive pleasure writer that replicates two `sexual.yaml` rules by hand. The
  containment has already failed: `world/rules/defeat_aftermath.py:47` imports the private name
  across a module boundary and calls it three times. An item that raises pleasure would have to do
  the same, and a caller tempted to write `entity.sexual.pleasure.base += n` directly instead would
  silently skip the wetness and climax-phase cascade.
- `buffs._add_buff` is private, so its equipment-immunity no-write backstop and its
  `unique_per_source` source-key rule are reachable only from inside the module.
- Removing a *named* status has no API at all. `cleanse_debuffs` hard-codes the debuff-polarity
  filter, and `_remove_buff_keys` is private and takes live **instance** keys rather than definition
  keys — a distinction any new caller would get wrong on the first try.

Doing this extraction first, as its own behavior-preserving change, keeps the item work from
carrying a diff through `action.py`, `buffs.py`, and the sexual pipeline that has nothing to do with
items.

## What Changes

- Move `_apply_pleasure_gain` from `world/rules/action.py` into a new `world/rules/pleasure.py` as
  `apply_pleasure_gain()`, body unedited. `action.py` and `world/rules/defeat_aftermath.py` import it;
  every existing caller keeps its behavior, including the pre-mutation capture ordering the spec pins.
- Move `_zero_pleasure` (`world/rules/action.py:1380`) into the same module as `zero_pleasure()`. It
  is a **second** direct writer of `entity.sexual.pleasure.base` that exists today, used by the drain
  handler, and it must stay separate from the gain entry rather than be folded into it: routing a
  zeroing through `apply_pleasure_gain(entity, -current)` would trip that function's
  `was_at_critical_point` branch and push a target sitting at 接近 into 進行中 — the opposite of what
  draining someone to zero means. Co-locating both writers makes the invariant checkable as "every
  pleasure write lives in this one module".
- Publish `buffs.apply_buff(entity, definition_key, *, instance_key=None, **data)` as the single
  supported buff-application entry point, keeping the equipment-immunity backstop and the
  `unique_per_source` source-key requirement exactly as they are today.
- Add `buffs.remove_by_selector(entity, selector) -> int`, where `selector` is a concrete definition
  key or one of `all` / `positive` / `negative`. It resolves the selector against **live buff
  instances**, removes them through the existing `dispel=True` path, and returns the count removed.
  `cleanse_debuffs()` is re-expressed as `remove_by_selector(entity, "negative")` so the two callers
  can never drift.
- No caller uses the new selectors yet. They are a forward-declared seam for
  `add-declarative-item-effects`, in the sense `AGENTS.md` sanctions — the API and its tests land
  here, the consumer lands next.

No player-visible behavior changes. No rulebook, registry, or persisted data changes.

## Capabilities

### New Capabilities

None. Every change restates or extends an existing capability.

### Modified Capabilities

- `sexual-act-effects`: the pleasure-handler requirement is restated so the ordered cascade is owned
  by one named shared entry point rather than by a function private to the cast pipeline, and gains a
  requirement that every deterministic pleasure writer routes through it. The cascade's five ordered
  steps and all five existing scenarios are unchanged.
- `buff-handler-integration`: gains a requirement naming the public buff-application entry point and
  the two invariants it carries (equipment-immunity refusal, `unique_per_source` source key), so a
  caller outside `world/rules/buffs.py` can apply a buff without reaching for `BuffHandler.add()`
  directly and losing both guards.
- `cleanse-effect-handler`: the `cleanse:status` requirement is restated in terms of the shared
  selector-based removal, and a new requirement defines the selector vocabulary — concrete key,
  `negative`, `positive`, `all` — including that selectors resolve against live instances rather than
  definition keys, and that removal returns a count.

## Impact

- **Code**: new `world/rules/pleasure.py`; `world/rules/action.py` (function removed, import added —
  every internal call site updated); `world/rules/buffs.py` (`apply_buff`, `remove_by_selector`,
  `cleanse_debuffs` re-expressed).
- **Call sites**: `_apply_pleasure_gain` has six production call sites — three in `action.py`
  (`_handle_pleasure_effect` at `:964`, and the two-step climax walk in `_handle_divine_pleasure_max`
  at `:1103-1104`) and three in `world/rules/defeat_aftermath.py` (`:926`, `:928`, `:1499`), which
  already imports the private name. `_zero_pleasure` has one caller, `_handle_sexual_drain`. Nine
  further call sites live in `world/rules/tests/test_sexual_act_effects.py`.
  `_apply_climax_phase_set` is **not** moved: it lives in `world/rules/sexual_state.py:853` and is
  imported by `action.py:48` and `sexual_transitions.py:14`; `pleasure.py` imports it the same way.
- **Tests**: `world/rules/tests/test_effect_handlers.py`, `test_sexual_act_effects.py`,
  `test_climax_settlement.py`, `test_buffs.py`, `test_holy_water_cleanse.py` — import-path updates
  plus new cases for the selector vocabulary and the published `apply_buff` guards.
- **Downstream**: unblocks `add-declarative-item-effects`, which binds item effect verbs to these
  three entry points.
- **Conflict note**: touches `world/rules/action.py`, as does `refactor-target-resolution-srp`. The
  edits are logically independent, but both land in the import preamble (`action.py:48-58`), so
  landing them concurrently in the same working tree means a trivial textual rebase. Sequence them.
- **Data**: none. No migration (unreleased project, zero users).
