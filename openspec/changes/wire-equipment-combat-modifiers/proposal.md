# Proposal: wire-equipment-combat-modifiers

## Why

P1 shipped the equipment-effect rulebook and roster, but nothing reads it:
equipping 騎士全套板甲 still changes no number. This is P2 of the
equipment-effects design
(`docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md`):
the read-time wiring that makes worn equipment land in every deterministic
combat surface through the existing single evaluation bundle.

## What Changes

- New pure accessor `equipment_adjustments(entity)` in
  `world/rules/equipment_effects.py`: reads the fail-closed
  `normalized_equipment()` mapping, folds each worn item's combat-relevant
  rulebook values (`atk_phys`, `defense`, `agility`, `magic_level`,
  `mp_cost`, `sp_cost`, `heal_gain`) into one bundle; malformed equipment
  storage yields an empty bundle (combat proceeds on base stats; mutation
  stays blocked by the existing preflight).
- `evaluate_combat_modifiers()` and `evaluate_combat_modifiers_no_create()`
  append the equipment bundle after rule-table matching, so every existing
  consumer — to-hit, adjusted attack/defense, overwhelm/estimation surfaces,
  action preview, MP/SP cost deduction, the sexual-resist score, and the
  flee contest — reads one identical effective bundle with no second formula.
  Module-level imports stay acyclic via the repo's established function-local
  import idiom; only runtime call edges cross the equipment/rulebook pair.
- New shared adjusted-agility floor: the effective agility used by every
  consumer (to-hit, overwhelm estimation, resist, flee) clamps at ≥ 0, so
  heavy gear can never invert a contest inequality. Initiative keeps its
  documented raw-agility exception.
- Equipment gauge ceilings (`gauge_caps`, positive-only) become live gauge
  maxima via a recompute (never accumulate) of each gauge trait's
  non-literal `mod` inside `toggle_equipment()`'s transaction — Evennia's
  `GaugeTrait` max is an alias of base, so `mod` is the sanctioned headroom.
  Because Evennia clamps gauge current only at read time, the sync also
  settles current down to a lowered ceiling in the same transaction:
  unequipping a capped item costs the excess HP/MP/SP deterministically
  (amends the parent design §6 gauge-ceiling mechanism).
- Skill heal magnitude scales by the merged `heal_gain` percent at the one
  `_heal_magnitude()` funnel. Consumable item-use heals keep their flat
  rulebook amounts (guaranteed baseline, deliberately unscaled).
- Panel/status gauge reporting reads `(base + mod)` maxima.

No new player commands. No backward compatibility or migration work.

## Capabilities

### New Capabilities

(None — this change wires consumers into existing capabilities plus the
`equipment-effects` capability introduced by P1.)

### Modified Capabilities

- `combat-modifier-table`: ADDS two requirements — (1) equipment adjustments
  merge into the merged bundle of both evaluation paths as a pure read with
  the malformed-storage empty-bundle policy, and (2) adjusted agility never
  resolves negative on any consumer path.
- `equipment-effects`: ADDS the single-accessor contract (one pure
  equipment-bundle accessor; every consumer reads it through the
  evaluation paths; no parallel equipment math).
- `equipment-inventory`: ADDS "gauge ceilings stay synced with worn
  equipment" — every successful toggle recomputes gauge `mod` from the
  current worn set inside the same transaction, and a failed toggle restores
  both surfaces.
- `combat-resolution`: ADDS the heal-magnitude `heal_gain` scaling
  requirement.

## Impact

- `world/rules/equipment_effects.py`: `equipment_adjustments()`.
- `world/rules/combat_modifiers.py`: bundle merge (both entry points) and
  the shared adjusted-agility helper used by `combat._to_hit`,
  `overwhelm._adjusted_agility`, `sexual_resist` scoring, and `disengage`'s
  flee contest.
- `world/rules/combat.py`: use the agility helper; `_heal_magnitude()` gains
  the `heal_gain` percent.
- `world/rules/equipment.py`: gauge-limit sync inside `toggle_equipment`
  (same transaction, snapshot/restore for trait storage, current settled to
  lowered ceilings).
- Presentation: gauge maxima readers already compute `(base + mod)`; P2 adds
  regression tests only (no payload schema change — P6/P7 own presentation).
- Tests: fixed-RNG to-hit/damage/heal behavior with worn gear, equip/unequip
  gauge sync incl. exam full-restore interaction, resist-score pickup,
  cost-check agreement across preview/resolve, malformed-storage inertness,
  agility floor. `combat-modifier-table`'s per-rule test correspondence is
  untouched (equipment is data, not rules).
- Not affected: buffs.yaml, sexual act resolution (P4), `equipment_worn`
  condition (P5), panel schema versions (P6/P7), command docs.
