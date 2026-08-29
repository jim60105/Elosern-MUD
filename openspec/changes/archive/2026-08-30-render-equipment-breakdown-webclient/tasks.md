# Tasks: render-equipment-breakdown-webclient

Depends on P6 (v5 payload + P3 adjustment text on the wire).

## 1. Components

- [x] 1.1 `CharacterStatusDrawer.vue`: render ALL payload-ordered layer
      chips (source-tinted design tokens, verbatim names, kind-formatted
      signed amounts: mult ×N.N trailing zeros stripped, flat ±N, pct ±N%;
      text-bearing, never color-alone; wrapping, NO truncation/`+n`
      concept) with gauge rows attaching chips to the maximum and keeping
      the existing value text; layer-free rows render no chip container or
      wrapper at all. Gauge pairing is cross-payload-guarded (rubber-duck
      run 1): a vitals row attaches the character trait's layers ONLY when
      the character panel is available, the matching trait row carries a
      non-null `max`, and `trait.max === status.resources[key].maximum`;
      otherwise the row keeps its existing value text with no breakdown
      element. No chip site on the 公會 rows (`guild_merit` layers are
      empty by construction — unobservable).
- [x] 1.2 `EquipmentDoll.vue`: print the character payload's `adjustment`
      string verbatim; empty renders nothing.
- [x] 1.3 `InventoryPanel.vue`: equipment rows source the same
      server-generated string by joining the store's character equipment
      rows on `item_key`; bag-only items render none; no client-side
      synthesis.
- [x] 1.4 Direct-render defense: unknown `source`/`kind` props render a
      neutral 其他 chip with an untouched value line (wire validators stay
      strict — do NOT relax any payload validation for this).

## 2. v5-only migration

- [x] 2.1 Update `stories/fixtures.js` character fixture to schema_version
      5: mirror the Python panel contract test's serialized sample;
      include a worn bias-bearing item with stored-base ≠ effective
      exposure, an adjustment-bearing item, and a 16-layer-bound row.
- [x] 2.2 Delete EVERY v4 wire branch: Vue acceptance goes through the
      shared `protocol.js` gate (v5-only there covers the store path);
      Python `web/webclient/presentation/character.py` loses
      `CHARACTER_LEGACY_SCHEMA_VERSION`, `_validate_trait_row_v4`, the v4
      equipment-row validator and the 4|5 dispatch; the Python contract
      test's `_valid_panel_v4`/`test_legacy_v4_panel_still_validates_exactly`
      are deleted; `web/tests/browser/browser_helpers.py
      valid_character_panel` migrates to the exact v5 form; delete all v4
      fixture usages.
- [x] 2.3 Legacy `protocol.js`: v5-only gate (keep the
      `payload.schema_version !== 5` literals the schema-version parity
      contract extracts); rewrite the P6 v4/5 tolerance Node-gate tests in
      `protocol.test.js` to v5-accept / v4-reject, and rewrite
      `character_menu.test.js` to an exact-v5 fixture with a single-version
      totals test (layers ignored, no console errors) — the v4≡v5
      equivalence test retires with the requirement; run
      `node --test web/static/webclient/js/tests/*.test.js`.

## 3. Stories, tests, evidence

- [x] 3.1 Stories: drawer (all three sources + gauge max + 16-layer-bound
      row), doll (adjustment-bearing slot), inventory (joined + bag-only
      rows) — `component-manifest.json` byte-unchanged.
- [x] 3.2 Vitest: chip order/name/kind formatting; all-layers-rendered at
      the 16 bound; no-layers equivalence (no breakdown elements);
      adjustment verbatim + join + bag-only + empty; exposure pin asserts
      effective present AND stored-base absent WITHIN THE EXPOSURE ROW
      (scoped selector, not whole-drawer); direct-render unknown-enum
      defense; v4 rejected on every wire path; gauge-chip guard negatives
      (character unavailable / mismatched maxima render no chips).
- [x] 3.3 `npm test`, `npm run build-storybook`,
      `npm run showcase-coverage` green.
- [x] 3.4 Python evidence tests in `web/webclient/tests/` (extend the
      data-evidence pattern): `run_npm` Vitest-family + Storybook build +
      coverage evidence, annotated with canonical IDs from
      `uv run --locked python -m tools.spec_traceability list` after spec
      sync for BOTH new requirements; `tools.spec_traceability check`
      green. No `.github/evennia-shards.json` edit — shard 5's
      `web.webclient` package label already owns new modules; verify with
      `tests.test_evennia_test_optimization_contract`.

## 4. Regression and handoff

- [x] 4.1 `tests/test_command_docs.py` green (no command-surface change);
      non-browser suite once with `--parallel 16 --noinput --keepdb`
      (the only Python behavior change is the v4 acceptance deletion).
- [x] 4.2 Record deviations (or none) from the parent design here; run
      `openspec validate render-equipment-breakdown-webclient --strict`.
- [x] 4.3 Sync the deltas into `openspec/specs/`: ADD both new requirements
      and REMOVE 「The legacy client tolerates the version-5 character
      payload」 from `webclient-exploration-menu`; annotate the evidence
      tests with the canonical IDs; `openspec validate --all --strict`
      and `tools.spec_traceability check` green.

## Deviations from the parent design

- None from the parent design's §11 Vue paragraph. Two implementation-time
  decisions were made inside the change's own scope: (1) the gauge-row chip
  attachment is cross-payload-guarded — layers render on a 生命量 row only
  when the character trait's `max` equals `status.resources[key].maximum`
  (the vitals text is `status` v1 and the layers are `character` v5, so a
  stale pair must not decompose a maximum the two panels disagree on); and
  (2) the transitional v4 deletion reaches the Python presenter as
  authorized by this change's REMOVED delta for
  「The legacy client tolerates the version-5 character payload」, closing
  the tolerance window on every wire at once (design.md D3).

## Rubber-Duck run 2 adjudication (post-implementation)

- BLOCKING 1 accepted: `mult` amounts render as SIGNED factors
  (`×−1.2` with the U+2212 minus) — both wire validators accept negative
  non-zero factors and `world/rules/status_text.py` keeps the sign, so an
  absolute-value render corrupted a valid payload explanation. Component
  test extended with a negative-factor case.
- BLOCKING 2 accepted: the neutral 「其他」 classification keys on
  `source` AND `kind` — a layer with an unrecognised `kind` (even under a
  known source) renders the neutral class and label suffix, matching D1;
  the direct-render test previously asserted the contrary and now requires
  the neutral chip for both unknown enums.
- Observation 1 accepted: the rendering evidence test now executes BOTH
  `breakdown_rendering.test.js` and `character_status_drawer.test.js` so
  the effective-exposure pin runs inside the evidence boundary.
- Observation 2 accepted: a duplicate-`item_key` inventory test pins the
  first-row-wins join policy.
- Observation 3 declined (out of scope): the showcase spec's pre-existing
  「status, character, and skill surfaces」 requirement still narrates v3/v4
  character fixtures; that prose belongs to its own requirement's next
  maintenance delta, not to this change's sync.
