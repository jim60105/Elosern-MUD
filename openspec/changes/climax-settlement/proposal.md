## Why

`world/rules/sexual_state.py`'s `climax_phase` cycle has a dead end. The only rule that leaves
`進行中` (`climax_phase_ends_to_afterglow`) is conditioned on the `climax_ends` event, and no
production code path emits it. `DECAY_CONFIG["climax_phase"]` declares `only_from: 餘韻`, so passive
decay cannot rescue an entity stuck in `進行中` either. Combined with the existing
`climax_in_progress_locks_actions` combat modifier (`actions_per_turn: 0`), any entity that reaches
`進行中` is currently locked out of acting **permanently**. The bug is unreachable today only because
nothing in the shipped codebase raises `arousal` (soon `pleasure`) to `極限` — the approved sexual-act
system design set (`docs/superpowers/specs/2026-08-15-*.md`) adds 69 acts that will make it reachable
immediately, so this fix must land ahead of them rather than be discovered as a regression.

Fixing the dead end also unlocks the design's climax-extension mechanic: `sexual.yaml` ships an
`experience_lesbian_added` row with no male counterpart, an asymmetry the approved D-12 same-sex
branch (`docs/superpowers/specs/2026-08-15-sexual-act-catalog-design.md` §4.1) would otherwise make
visible by silently dropping male-male experience recording.

## What Changes

- Emit `climax_ends` from both existing decay call sites (`world/rules/combat.py`'s per-round upkeep
  and `world/rules/clock.py`'s out-of-combat settlement), closing the `進行中 → 餘韻` loop that today
  has no emitter.
- Add a climax-extension mechanic: an entity in `進行中` with a staged extension (set by a future
  act-effect proposal, not this one) remains in `進行中` for another settlement point instead of
  resolving, at half the ordinary SP cost, via a new `climax_extended` event and its
  `sp_cost_on_climax_extension` rule. Extension is deliberately unbounded by this proposal — no cap is
  introduced; a resist counterplay is explicitly out of scope and reserved for a later proposal
  (`sexual-resist-contest`).
- Add `SexualState.climax_turns` (read-only) and `SexualState.stage_climax_extension()` (the sole
  mutator for a new `pending_climax_extension` counter) as the public surface a later act-effect
  proposal stages an extension through.
- Fix `world/rules/clock.py::_has_settlement_work` so an entity with `climax_phase == 進行中` always
  counts as needing further settlement, even when every `DECAY_CONFIG`-tracked field has already
  reached its floor — otherwise the quanta early-exit could strand such an entity mid-climax
  indefinitely during a long time-skip.
- Add `sexual.yaml` rule `experience_gay_added` (`penetrative_sex_with_male` → `男男性愛`), mirroring
  the shipped `experience_lesbian_added` row so the same-sex path is symmetric. Neither same-sex rule
  touches `virgin`; that stays exclusive to `virginity_once`/`first_vaginal_penetration`, unchanged.

## Capabilities

### New Capabilities
- `climax-settlement`: the climax-extension mechanic (staging, consumption, half-cost SP, unbounded
  duration), the `進行中` dead-end fix, and the two lifetime counters (`高潮次數`, `連續高潮次數`)
  incrementing on `climax_ends`/`climax_extended`.

### Modified Capabilities
- `combat-resolution`: "Per-round upkeep ticks buffs and advances sexual decay by the round duration"
  gains a scenario — upkeep now also settles climax phase (emitting `climax_ends` or
  `climax_extended`) immediately after `decay_tick`, for every living roster member, every round.
- `settlement-stage-order`: "Long jumps settle in quanta... with an early exit once nothing remains to
  settle" gains a scenario — the early-exit condition now also treats `climax_phase == 進行中` as
  settlement work in its own right, independent of whether any `DECAY_CONFIG` field is off its floor.

## Impact

- `world/rules/sexual_state.py`: new `climax_settlement_action()`, `SexualState.climax_turns`,
  `SexualState.pending_climax_extension`, `SexualState.stage_climax_extension()` (validated additive
  staging).
- `world/rules/rulebook/sexual.yaml`: two new rows (`sp_cost_on_climax_extension`,
  `experience_gay_added`).
- `world/rules/combat.py`: `_end_of_round_upkeep` calls the new settlement decision and emits the
  corresponding event.
- `world/rules/clock.py`: `_settle_buffs_and_decay`'s two `decay_tick` call sites gain the same call;
  `_has_settlement_work` gains the `進行中` disjunct.
- `world/rules/clock.py` and `world/rules/action.py`: the explicit snapshot/rollback enumerations
  (`_ADVANCE_ENTITY_SURFACES`, `_snapshot_entity_state`/`_restore_entity_state`) gain the two new
  attributes, so a failed-and-rolled-back advance, action commit, or combat-session round restores
  them alongside the existing sexual surfaces.
- No web, command, or presentation surface changes. No new resource or scheduler. This proposal does
  not add any actor-facing act or effect handler that stages an extension — `stage_climax_extension()`
  is dead code from a production caller's perspective until a later proposal (`sexual-act-effects`)
  calls it; it is fully testable and specified on its own.
