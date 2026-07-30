## Why

Design doc §11 roadmap item #10 depends on change 9 (`dice-combat`), which built the d100 roller, the
recalibrated to-hit formula, `effective_power()`, initiative, and the per-round turn loop — but
deliberately left the overwhelm threshold, single-shot resolution, and `EventLog` compression as
Non-Goals, naming this change as the owner by number. Without this change, every combat encounter,
however lopsided, must be played out one real d100-rolled round at a time, and change 9's own D-4
finding — that its ratio-based `effective_power()` alone cannot detect a fight that is already decided
by a saturated to-hit rate — has no consumer that acts on it.

This change is also a correction of scope, not of formula. Change 9 recorded, as an explicit handoff,
that a fight can be mathematically settled two different and independent ways: a lopsided
`effective_power()` ratio (its own signal), or a saturated to-hit rate at the ±50 effective-agility
gap its own recalibrated formula produces (a second, cheaper, more direct signal it found but was not
scoped to consume). Building the overwhelm threshold on the ratio alone, as design doc §6.3's formula
sketch reads in isolation, would silently drop the second signal change 9 went out of its way to hand
over.

## What Changes

- Add `world/rules/overwhelm.py`: `classify_overwhelm()`, combining three independent signals — change
  9's `effective_power()` ratio, its to-hit formula's saturation boundary, and a new estimated-round-
  count bound — so that overwhelm means the fight is **decided and quick**, never merely decided. The
  two "decided" signals are OR-combined (with an explicit safety rule for the case where they disagree
  on direction); the round-bound signal then gates whether that decided direction is fast enough to
  compress at all, since a fight can be certain in outcome while still being an attrition grind (e.g. a
  huge-hp defender against damage floored at 1 per hit) rather than a curbstomp. Recomputed at engage
  and every round.
- Add `world/rules/rulebook/overwhelm.yaml`: `power_ratio_threshold` (100, per design doc §6.3) and
  `max_estimated_rounds` (5, this change's own calibrated placeholder), both documented as data, not a
  hardcoded Python literal, per design doc D9's split.
- Add `resolve_overwhelm()`: a single-shot combat resolver that reuses change 9's `run_round()`
  verbatim — same dice stream, same formulas, same turn order — so that its outcome is exactly, not
  approximately, consistent with driving `run_round()` one round at a time. "Single-shot" describes
  the caller's experience (one call resolves the encounter to completion) and the output's shape
  (a compressed `EventLog` set), not a shortcut around the underlying combat math.
- Add `compress_event_logs()`: an `EventLog`-shape-preserving compression that drops purely mechanical
  `"roll"`-kind entries (the raw d100 value, needed for nothing downstream) while keeping every
  `"damage"`-kind entry (who hit whom, for how much, every round) verbatim, and prepends one
  `"overwhelm_resolution"`-kind summary entry — the exact kind name change 8's own design anticipated.
  No edit to change 8's `EventLog`/`EventEntry` dataclasses.
- Golden, fixed-seed tests proving: (1) single-shot and per-round resolution reach byte-identical
  world state (HP, winner, rounds elapsed) under the same seed; (2) both overwhelm directions (a party
  overwhelming a monster, and a monster overwhelming the party — design doc §6.3's "player is
  one-shot") are covered with equal rigor; (3) a compressed `EventLog` still renders through change 8's
  `render_plain_text()` with zero LLM involvement.

## Capabilities

### New Capabilities
- `overwhelm-threshold`: the three-signal `classify_overwhelm()` (power ratio, hit-rate saturation, and
  an estimated-round-count bound), the `overwhelm.yaml` threshold data, and the round-by-round
  recomputation rule, including the documented conflict-resolution rule for when the ratio and hit-rate
  signals disagree, and the calibration proving the round bound admits genuine curbstomps while
  excluding attrition grinds.
- `single-shot-resolution`: `resolve_overwhelm()`'s reuse of change 9's `run_round()` for exact
  consistency with per-round resolution, its early-exit-on-reclassification behavior, and its
  `total_seconds` reporting (unchanged `rounds × 6` formula).
- `event-log-compression`: `compress_event_logs()`'s roll-entry-dropping / damage-entry-preserving
  rule, the new `overwhelm_resolution` summary entry, and its `render_plain_text()` compatibility.

### Modified Capabilities
- None. `openspec/specs/` is empty (no earlier change has been archived yet), and this change edits no
  file authored by any earlier change — it only imports and calls change 9's `combat.py` and change
  8's `event_log.py` as they already stand.

## Impact

- **New files**: `world/rules/overwhelm.py`, `world/rules/rulebook/overwhelm.yaml`,
  `world/rules/tests/test_overwhelm_*.py` (new test modules for this change's scope).
- **Modified files**: none. This change is purely additive against changes 8 and 9's existing public
  surfaces (`combat.effective_power()`, `combat.run_round()`, `combat.is_battle_over()`,
  `combat.COMBAT_YAML`, `event_log.EventEntry`/`EventLog`/`render_plain_text()`).
- **Depends on**: change 9 (`dice-combat`) for `effective_power()`, `run_round()`, `is_battle_over()`,
  `Battlefield`, and `COMBAT_YAML["to_hit"]["defender_constant"]`; change 8 (`action-resolver`),
  transitively, for `EventLog`/`EventEntry`/`render_plain_text()`.
- **Consumers deferred to later changes**: change 10b (`monster-behaviour`) is expected to decide what
  action a losing side takes during a compressed encounter (this change reuses whatever
  `action_provider` the caller supplies — including change 9's own placeholder — unmodified); change
  11 (`world-clock`) is expected to read `OverwhelmResult.total_seconds` and decide how to advance;
  change 18 (`narrator`) is expected to consume the compressed `EventLog`s this change produces, and
  may call `render_plain_text()` on them directly, exactly as it would on an uncompressed one.
