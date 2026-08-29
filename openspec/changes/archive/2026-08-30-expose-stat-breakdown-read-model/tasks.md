# Tasks: expose-stat-breakdown-read-model

Depends on P2 (bundle + gauge sync + agility floor), P3 (adjustment
formatter), P4 (effective exposure value), P5 (condition layers incl.
grace rules).

## 1. Pure breakdown builder

- [x] 1.1 In `world/rules/status_query.py`, build the layer-first
      breakdown: per panel stat assemble accounting-complete layers
      (skill mults from `owned_keys()` × registry `StatMultiplyEffect`s;
      condition layers from the merged NO-CREATE bundle with
      `STATUS_DISPLAY` names; equipment layers per worn item, gauge caps as
      flat layers on the max) with fixed identity/sort tuples
      (skill key; (buff|rule, key); (slot order, item key)).
- [x] 1.2 Compose `effective` FROM the layers per the D1 authoritative
      table (attack/defense: merged flat/pct + skill mults, single final
      rounding; agility: same + ≥ 0 floor display; magic_level: the shipped
      skill effective-value rounding form reproduced from primitives;
      gauge max: the shipped gauge-reader form) — never a parallel
      recompute.
- [x] 1.3 Fail-closed accounting: unresolvable layer label or > 16 layers
      on a stat → read model raises → character panel serves the common
      unavailable form; empty sources contribute nothing; bounds ≤ 32 rows.
- [x] 1.4 Purity: builder takes validated stored snapshots + no-create
      bundle only (no `entity.traits`/`SkillHandler`/handler property
      access); `status_query` assembles once per read; compact presenter
      serializes totals from the same result.

## 2. Surfaces

- [x] 2.1 `web/webclient/presentation/character.py`:
      `CHARACTER_SCHEMA_VERSION = 5`, rows
      `{key, label, base, current, max, effective, layers}` (`current` =
      total-display on every row; statics equal `effective`), equipment
      rows gain the P3 `adjustment` string; other sections byte-identical.
- [x] 2.2 Python panel validator: version-dispatched exact shapes (v4
      retained only for legacy fixtures; v5 production exact).
- [x] 2.3 Text client: status/inventory print
      `label value（來源…）` lines and adjustment summaries from the same
      builder; compact in-combat status totals-only; confirm no command
      keys/aliases/syntax changes.
- [x] 2.4 `web/static/webclient/js/elosern/protocol.js`: version-dispatched
      exact-shape validators for 4 and 5; totals rendering unchanged
      (statics included).

## 3. Tests

- [x] 3.1 Builder: per-stat layer composition and order;
      accounting-completeness fail-closed (unresolvable label; synthetic
      17-layer actor → unavailable, never truncation); empty-source rows;
      gauge max decomposition incl. P2 sync and P5 grace rules.
- [x] 3.2 Purity: never-materialized entity → persisted attributes
      byte-identical after panel build; no handler instantiation.
- [x] 3.3 Parity per the D1 mapping table: attack/defense/agility (floored,
      initiative excluded), magic rounding form, gauge ceiling equals the
      heal-clamp max — each pinned against its named computation on
      identical fixtures.
- [x] 3.4 Panel contract: v5 exact-shape validator tests; v4-fixture branch
      still validates; adjustment strings; intimate effective exposure;
      read-only byte-for-byte test updated.
- [x] 3.5 Text-client snapshot tests for layer lines and summaries;
      compact shows no segments and equals panel effective values;
      `tests/test_command_docs.py` green.
- [x] 3.6 Legacy client: v5 payload renders same `current`/`max` as
      equivalent v4 (statics included), layers ignored, no console error;
      v5-with-unknown-field and v4-at-version-5 rejected; `npm test`
      green.
- [x] 3.7 After spec sync, obtain canonical IDs via
      `uv run --locked python -m tools.spec_traceability list` and annotate
      the covering tests (one per new requirement + the modified panel
      requirement), keeping `tools.spec_traceability check` green.

## 4. Regression and handoff

- [x] 4.1 Focused suites: `world.rules` (status), `web.webclient`
      presentation tests, Node/Vitest legacy suites; then the non-browser
      suite once with `--parallel 16 --noinput --keepdb`.
- [x] 4.2 Record deviations (or none) from the parent design here; run
      `openspec validate expose-stat-breakdown-read-model --strict`.

### Deviations recorded at implementation

- Malformed worn gear takes the shipped fold's zero contribution
  (`normalized_equipment` → "nothing worn"), producing zero layers and an
  unmodified effective — byte-parity with the combat bundle rather than a
  panel-only failure.
- The 32-row / 16-layer bounds are enforced by the wire validators on both
  sides and by `_validated_row` in the builder; a builder-side breach is
  unreachable through the closed 8-key stat vocabulary and the
  accessory-stack normalization, so the synthetic 17-layer actor cannot
  exist through validated storage. Tests pin the validator branches plus
  the builder's bound check.
- Self-look/inventory text degradation catches ANY read-model exception
  (not only `StatusQueryError`) and falls back to the unchanged five-row
  block / no header, because appearance output must never be fatal.
- Per-item rulebook reads go through the new
  `equipment_effects.equipment_modifier_layers` accessor, keeping the P3
  single-source structural guard green; the builder no longer touches
  `EQUIPMENT_EFFECT_RULES` directly.
