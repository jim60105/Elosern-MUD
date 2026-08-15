## Why

The forthcoming sexual act catalog needs eleven cumulative, lifetime, per-entity behaviour counters
to gate act unlocks and to record the growth-curve progression the whole
[sexual act system](../../../docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md)
is built around (露出次數, 自慰次數, 高潮次數, and eight others). Today `SexualState` has exactly one
counter, `climax_today`, and it resets daily by design — it cannot answer "how many times has this
character ever masturbated." Nothing else tracks lifetime behaviour at all.

This is proposal `B2` in the
[Sexual Pleasure Model](../../../docs/superpowers/specs/2026-08-15-sexual-pleasure-model-design.md)
§2, depending on `pleasure-gauge` (`B1`) landing first (both edit `world/rules/sexual_state.py`).

## What Changes

- Add eleven new counter fields to `SexualState`, each an unbounded (`min=0`, no `max`), lifetime
  counter stored in the same `sexual_traits` `TraitHandler` `climax_today` already uses, and each
  with **exactly one** sanctioned mutator method — following `record_climax()`'s existing precedent
  exactly. No rule, no effect handler, and no future proposal's code may reach
  `SexualState._traits` directly to increment any of them; every increment goes through its named
  mutator.
- None of the eleven is reset by `reset_daily_counters()` — that function is `climax_today`'s alone,
  unmodified by this proposal.
- This proposal adds **no trigger wiring**: no `sexual.yaml` rule, no effect handler, no upkeep call.
  It builds the counter surface only. Three of the eleven (`climax_count`, `climax_extension_count`,
  `restraint_count`) will be driven by the later `climax-settlement` proposal (`B3`, which already
  owns `combat.py`/`clock.py`); the other eight will be driven by act-resolution effect handlers in
  the later `sexual-act-effects` proposal (`B5`). Building the surface first, ahead of either
  consumer, lets both land against a stable, already-tested API.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `sexual-state-handler`: `ADDED` — one new requirement covering all eleven counters (grouped by
  shared shape rather than one requirement per counter, to avoid eleven near-identical requirement
  blocks). No existing requirement's text changes.

## Impact

- `world/rules/sexual_state.py` — eleven counter fields, eleven mutators, eleven read properties,
  construction wiring (each always starts at `0`; no baseline field feeds any of them).
- No change to `world/rules/rulebook/sexual.yaml`, `world/rules/sexual_transitions.py`,
  `world/rules/combat.py`, or `world/rules/clock.py`. Those are `B3`'s and `B5`'s territory.
- Depends on `pleasure-gauge` (`B1`) landing first (sequential edits to the same file, not a
  functional dependency — none of the eleven counters reads or writes `pleasure`).
