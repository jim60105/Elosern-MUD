# Design: wire-equipment-combat-modifiers

## Context

Parent design: `docs/superpowers/specs/2026-08-29-equipment-combat-effects-design.md`
§6/§11 (P2 of seven; P1 landed the rulebook and roster). The shipped
consumer chain is: `entity.skills.effective_value(stat)` applies skill
multipliers; `evaluate_combat_modifiers(entity)` merges rule-table adjustment
bundles; `combat._to_hit`, `combat._adjusted_attack/_adjusted_defense`,
`overwhelm`, `action_preview`, cost deduction via `apply_cost_modifier`, and
`sexual_resist.resist_verdict` read that bundle. Gauges are Evennia
`GaugeTrait`s whose `max` is an alias of `(base + mod) * mult`.

## Goals / Non-Goals

**Goals:**

- One pure equipment bundle reaches every consumer through the existing
  evaluation paths (single formula discipline, parent design §6).
- Gauge ceilings from worn equipment become live maxima.
- Heals scale by `heal_gain`; adjusted agility floors at 0.

**Non-Goals:**

- Immunity/attached buffs (P3), sexual fields and exposure (P4),
  `equipment_worn` rules (P5), breakdown payloads (P6/P7), item-use heal
  scaling, command docs.

## Decisions

### D1 — Gauge headroom via `mod` recompute owned by `toggle_equipment`

`GaugeTrait.max` aliases `(base + mod) * mult`, so the only sanctioned
non-literal headroom is `mod`. `world/rules/equipment.py` gains
`sync_equipment_gauge_limits(entity)` (internal): for each of `hp/mp/sp` it
recomputes `mod = Σ gauge_caps(worn)` from scratch (never accumulating),
leaving `base` literal, and — because Evennia clamps gauge `current` only at
read time (a stored current above a lowered ceiling would corrupt the strict
status read model) — writes `current = min(current, new ceiling)` whenever a
recompute lowers a ceiling, all inside `toggle_equipment`'s existing
`transaction.atomic()` with trait storage snapshotted/restored on failure.
Equipping therefore raises the headroom, and unequipping settles any excess
as an immediate, deterministic resource cost at the single writer. Rationale:
recompute-from-scratch is idempotent, so no drift state can accumulate;
fail-closed storage already rejects every toggle, so a stale `mod` can only
coexist with storage that is already mutation-blocked. Alternative —
read-time-only maxima — rejected: Evennia clamps `current` WRITES to the
stored max (heal/recovery could never reach a raised display maximum), and
its read-only clamp leaves stored values stale above lowered ceilings.
Alternative — parallel cap attribute — rejected as derived duplicate state
with no engine benefit. Parent design §6 is amended accordingly.

### D2 — Merge position, and the import graph

`equipment_adjustments(entity)` lives in
`world/rules/equipment_effects.py` and reaches the normalizer via a
function-local import of `normalized_equipment` from `world/rules/equipment.py`
(an established repo idiom — `equipment.py` itself local-imports
`world.skills.equipment` and `EquipmentSlot` inside functions).
`equipment.py`'s gauge sync likewise function-local-imports the rulebook
accessor. Module-level imports therefore stay acyclic
(`equipment_effects` → lore/rulebook only; `combat_modifiers` →
`equipment_effects`), which is what P1's inertness import-allowlist test
asserts; only runtime call edges cross the pair. P2 expands that allowlist
with its authorized consumers.
`equipment_adjustments()` folds only combat-relevant fields (immune/
attached/exposure/pleasure are P3–P5's). Both
`evaluate_combat_modifiers()` and `evaluate_combat_modifiers_no_create()`
apply `_merge_adjustments(result, equipment_bundle)` after rule-table
matching. Order-insensitive by construction (numeric fields add; percents
add), but "after rules" keeps rule IDs' per-rule breakdown (P6's
condition layers) cleanly separated from the equipment layer.

### D3 — One shared adjusted-agility floor

Four sites today derive modifier-adjusted agility independently
(`combat._to_hit`, `overwhelm._adjusted_agility`, `sexual_resist` scoring,
and `disengage`'s flee contest). P2 introduces
`combat_modifiers.adjusted_agility(entity, modifiers=None)` =
`max(0, _apply_percent_mod(effective_value("agility"), modifiers.agility))`
and all four call it. The ≥ 0 floor is the one new numeric invariant
(heavy armor must slow you, never reverse a to-hit or flee inequality).
Initiative (`combat.roll_initiative`) deliberately keeps RAW
`effective_value("agility")` — an existing documented exception the modifier
bundle never touched (buffs like `wind_haste` already skip initiative), and
this change does not alter it.

### D4 — `heal_gain` scales skill heals only

One formula, normative: `base_amount = max(round(magic × heal.multiplier),
heal.floor)` (unchanged), then `final = max(floor(base_amount ×
(1 + heal_gain_pct/100)), heal.floor)`. Consumable item-use heals
(`item_effects.yaml` amounts) stay unscaled: they are the offline-friendly
guaranteed baseline, and scaling them would couple two rulebooks
mid-resolution. A test pair distinguishes floor from Python's banker
rounding (e.g. base 3 × +20% → 3, not 4). Documented in the delta
requirement.

### D5 — Gauge readers already honor `(base + mod)`

The strict status read model validates `mod`/`mult` and computes
`round((base + mod) × mult)` for gauge maxima today; with D1's clamp,
`current > maximum` cannot persist, so no presentation code changes. P2
only adds regression tests pinning effective-maxima reporting (status panel,
character panel, exam full-restore).

## Risks / Trade-offs

- [Exam/defeat full-restore (`restore_gauges_to_full`) now restores to
  effective maximum] → Desired semantics (exams start/end fully equipped);
  regression test pins it.
- [Monster/NPC entities never toggle equipment, so their `mod` stays 0] →
  Equipment is players-only by design; resist/to-hit paths simply see empty
  equipment bundles.
- [A future item grants `gauge_caps` on a trait the entity lacks] → Sync
  skips absent gauge traits silently only when the trait key is unknown to
  the entity's trait set; loader already bounds caps to `hp/mp/sp`.
- [Fixed-seed golden combat tests could shift values as equipment enters] →
  Existing goldens use unequipped fixtures; new behavior lands in new tests,
  keeping goldens green.

## Migration Plan

Single implementation commit (data already live from P1); rollback = revert.
No stored-data migration: `mod` recompute happens on the next toggle, and
pre-change characters have `mod == 0` by construction.

## Open Questions

None.
