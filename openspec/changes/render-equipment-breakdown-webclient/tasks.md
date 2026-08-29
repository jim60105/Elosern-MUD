# Tasks: render-equipment-breakdown-webclient

Depends on P6 (v5 payload + P3 adjustment text on the wire).

## 1. Components

- [ ] 1.1 `CharacterStatusDrawer.vue`: render ALL payload-ordered layer
      chips (source-tinted design tokens, verbatim names, kind-formatted
      signed amounts: mult ×N.N trailing zeros stripped, flat ±N, pct ±N%;
      text-bearing, never color-alone; wrapping, NO truncation/`+n`
      concept) with gauge rows attaching chips to the maximum and keeping
      the existing value text; layer-free rows render no chip container or
      wrapper at all.
- [ ] 1.2 `EquipmentDoll.vue`: print the character payload's `adjustment`
      string verbatim; empty renders nothing.
- [ ] 1.3 `InventoryPanel.vue`: equipment rows source the same
      server-generated string by joining the store's character equipment
      rows on `item_key`; bag-only items render none; no client-side
      synthesis.
- [ ] 1.4 Direct-render defense: unknown `source`/`kind` props render a
      neutral 其他 chip with an untouched value line (wire validators stay
      strict — do NOT relax any payload validation for this).

## 2. v5-only migration

- [ ] 2.1 Update `stories/fixtures.js` character fixture to schema_version
      5: mirror the Python panel contract test's serialized sample;
      include a worn bias-bearing item with stored-base ≠ effective
      exposure, an adjustment-bearing item, and a 16-layer-bound row.
- [ ] 2.2 Vue store/validator path: accept ONLY schema version 5; delete
      the v4 branch and v4 fixture usages.
- [ ] 2.3 Legacy `protocol.js`: v5-only gate; rewrite the P6 v4/5
      tolerance Node-gate tests to v5-accept / v4-reject; run
      `node --test web/static/webclient/js/tests/*.test.js`.

## 3. Stories, tests, evidence

- [ ] 3.1 Stories: drawer (all three sources + gauge max + 16-layer-bound
      row), doll (adjustment-bearing slot), inventory (joined + bag-only
      rows) — `component-manifest.json` byte-unchanged.
- [ ] 3.2 Vitest: chip order/name/kind formatting; all-layers-rendered at
      the 16 bound; no-layers equivalence (no breakdown elements);
      adjustment verbatim + join + bag-only + empty; exposure pin asserts
      effective present AND stored-base absent; direct-render unknown-enum
      defense; v4 rejected on every wire path.
- [ ] 3.3 `npm test`, `npm run build-storybook`,
      `npm run showcase-coverage` green.
- [ ] 3.4 Python evidence tests in `web/webclient/tests/` (extend the
      data-evidence pattern): `run_npm` Vitest-family + Storybook build +
      coverage evidence, annotated with canonical IDs from
      `uv run --locked python -m tools.spec_traceability list` after spec
      sync for BOTH new requirements; `tools.spec_traceability check`
      green.

## 4. Regression and handoff

- [ ] 4.1 `tests/test_command_docs.py` green (no command-surface change);
      non-browser suite once with `--parallel 16 --noinput --keepdb`
      (regression-only — no Python behavior change expected).
- [ ] 4.2 Record deviations (or none) from the parent design here; run
      `openspec validate render-equipment-breakdown-webclient --strict`.
