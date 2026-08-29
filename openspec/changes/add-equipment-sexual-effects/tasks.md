# Tasks: add-equipment-sexual-effects

Depends on P1 (items + `pleasure_gain`/`exposure_bias` authored) and P2
(fold pattern in place; combat evaluator output stays combat-key-only).

## 1. Shared reader and effective overlay

- [ ] 1.1 Extract `_StoredLevel` + `_stored_sexual_level` from
      `world/rules/combat_modifiers.py` into a neutral module (lore +
      attribute-storage imports only); re-point `combat_modifiers` imports;
      grep test modules importing them there and re-export if needed.
- [ ] 1.2 Add `effective_exposure(entity)` to
      `world/rules/equipment_effects.py` via the shared reader (clamped
      `EXPOSURE_LEVELS` shift by Σ worn `exposure_bias`, malformed → zero
      bias, no writes, no handler materialization).
- [ ] 1.3 Apply the overlay in BOTH `combat_modifiers` context builders
      (`_build_context`, `build_no_create_condition_context` — no-create
      path stays handler-free/write-free), filling `context["exposure"]`
      with the same immutable level view in both paths.
- [ ] 1.4 Render the effective value in the `status_query` exposure row
      (row contract unchanged; web payload derives from the read model).

## 2. Pleasure fold (equipment-only source)

- [ ] 2.1 Add pure `equipment_pleasure_gain(entity)` to
      `world/rules/equipment_effects.py` (Σ worn soft percents, malformed →
      0). Do NOT extend the combat evaluator's fold/key-set.
- [ ] 2.2 Add `pleasure_percent: int = 0` to `compute_pleasure_gain()` with
      the normative `max(round(product × (1 + pct/100)), 0)` single-rounding
      formula; pass the accessor value at the single `action.py:811` call
      site.

## 3. Overlay discipline

- [ ] 3.1 Classify every shipped consumer of stored `sexual.exposure` as
      STORED (transitions — including rule matching, snapshot, mutation,
      persistence, imports) or EFFECTIVE (both builders, status row,
      accessor) in the structural allowlist test; equipping/unequipping
      SHALL NOT raise exposure field-change events.

## 4. Tests

- [ ] 4.1 Accessor: 中等 + 聖女聖袍(+2) → 極高 with stored untouched, clamp
      at both ends, malformed → stored/0, purity (no writes, no handler
      creation), no import edge from `equipment_effects` to rules modules.
- [ ] 4.2 Contexts: 修女聖袍 at stored 中等 fires the 露出 ≥ 高 defense rule
      in BOTH paths with identical bundles; equip/unequip round-trip;
      gte/lte/equality parity on the view type; unequipped golden matching.
- [ ] 4.3 Funnel: 40 × +15% → 46; +25% → 50; −100% → 0; pct-0 golden
      equality; sensitivity/shame ladders and all eleven counters asserted
      unchanged.
- [ ] 4.4 Key-set lock: no-create combat bundle never contains
      `pleasure_gain`; resist/overwhelm consumer tests unchanged.
- [ ] 4.5 Behavior (EvenniaTest): exposure-raising act with bias +2 worn —
      stored advances as with no equipment, no field-change event from
      toggling, removal drops effective back to stored; status row and web
      payload show the same effective ordinal with unchanged schemas.
- [ ] 4.6 Structural allowlist test (3.1) green.
- [ ] 4.7 After spec sync, obtain canonical IDs via
      `uv run --locked python -m tools.spec_traceability list` and annotate
      the four covering tests (one per delta requirement, literal IDs,
      substantive assertions — including the structural-allowlist
      requirement) keeping `tools.spec_traceability check` green.

## 5. Regression and handoff

- [ ] 5.1 Focused suites: `world.rules` (combat_modifiers, sexual_*,
      action, status), `web.webclient` status payload tests; then the
      non-browser suite once with `--parallel 16 --noinput --keepdb`.
- [ ] 5.2 Record deviations (or none) from the parent design here; run
      `openspec validate add-equipment-sexual-effects --strict`.
