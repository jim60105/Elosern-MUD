# Proposal: add-equipment-sexual-effects

## Why

P1 authored `pleasure_gain` and `exposure_bias` values (誘蠱蕾絲內衣,
迷情絲頸環, 修女聖袍, 光輝聖徽, 圣女聖袍 …) that nothing consumes yet. This
is P4 of the equipment-effects design
(`docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md` §8):
revealing or alluring equipment finally changes how the sexual system
feels and how combat reacts to it, without ever touching stored sexual
identity — the invariant that sensitivity, shame, virginity, and lifetime
counters are equipment-immune.

## What Changes

- New read-time overlay `effective_exposure(entity)`: clamped ordinal
  `EXPOSURE_LEVELS` index `stored + Σ worn exposure_bias`. Stored exposure
  traits, act transitions, and snapshots operate on the stored value only;
  every player-facing read surface (status read model exposure row included)
  renders the effective value (layer breakdown arrives in P6/P7).
- Both combat-modifier condition contexts (`_build_context` and
  `build_no_create_condition_context`) match rules against the EFFECTIVE
  exposure as one shared immutable level view (identical `gte`/`lte`/
  equality parity), so revealing gear makes the shipped 露出 ≥ 高 →
  defense −15 rule fire with nothing on — the Church doctrine loop (以坦露為聖:
  修女聖袍 raises exposure, grace rules in P5 reward it). Stored-exposure
  reads move to one shared stored-state reader module that both
  `combat_modifiers` and `equipment_effects` import (no reverse import edge,
  no cycle, no-create path unchanged).
- `compute_pleasure_gain()` folds the EQUIPMENT-ONLY `pleasure_gain`
  (pure accessor over worn items — the combat evaluator's field scope is
  deliberately NOT extended, so resist/overwhelm bundle consumers are
  untouched) with a normative formula:
  `max(round(base × ratio × sensitivity × shame × crowd × (1 + pct/100)), 0)`.
  Sensitivity/shame ladders, virginity, and the eleven lifetime counters are
  untouched.
- Resist scoring, overwhelm estimation, and action preview pick the exposure
  shift up for free through the shared context (no second formula).

No backward compatibility or migration work.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `equipment-effects`: ADDED `effective_exposure` accessor contract (pure,
  clamped, malformed storage → stored value unchanged).
- `combat-modifier-table`: ADDED requirement — condition contexts match on
  effective exposure in BOTH the creating and no-create builders.
- `sexual-act-effects`: ADDED pleasure-funnel requirement with the
  normative merged-`pleasure_gain` formula and the ≥ 0 clamp.
- `sexual-state-handler`: ADDED overlay discipline — bias never writes
  stored exposure; transitions, snapshots, and persistence stay stored-only;
  player read surfaces render the effective value.

## Impact

- `world/rules/equipment_effects.py`: `effective_exposure(entity)` (reuses
  the P2 fold structure for the bias sum).
- `world/rules/combat_modifiers.py`: both context builders read effective
  exposure; `_StoredLevel`/stored-level reader move OUT to the shared
  module (re-import at old site only if needed for existing test imports).
- New `world/rules/stored_sexual_reads.py` (or equivalent neutral module):
  hosts the handler-free stored sexual-level reader + `_StoredLevel` view;
  imported by `combat_modifiers` and `equipment_effects`, imports lore only.
- `world/rules/sexual_act_effects.py`: `compute_pleasure_gain()` gains
  `pleasure_percent` (equipment-only source, evaluated by the caller).
- `world/rules/status_query.py`: exposure row renders the effective value.
- Tests: accessor clamping/purity, both-context rule firing (露出≥高 with a
  修女聖袍 at stored 中等) + equip/unequip round-trip + gte/lte/equality view
  parity, pleasure formula pairs (40×+15%→46, +25%→50, negative floor to 0,
  pct-0 golden equality), combat-evaluator key-set lock (resist/overwhelm
  consumers see no new keys), transitions-stay-stored incl. no
  `field_changed` from bias (EvenniaTest), status-row vs web-payload
  effective agreement, existing sexual suites green.
- Not affected: stored trait schema, transition rulebook, sensitivity/shame
  registries, P6/P7 payloads, command surface (docs untouched,
  `tests/test_command_docs.py` green).
