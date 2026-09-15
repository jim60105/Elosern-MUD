## Batch order (water wave — integration contract in ./design.md)

0. Predecessors (ALL must be merged before this change starts; this change authors data only over their shipped vocabulary):
   1. `water-mp-depletion-reaction`
   2. `water-mana-transfer`
   3. `water-damage-redirect-shield`

## 1. Registry swap (data only)

- [x] 1.1 Confirm every predecessor contract in design.md D3 is merged and inspect current source/exported references (codegraph/LSP) for the water registry block and every dev-era key before editing; if any mechanic from the D1 coverage table is missing, STOP and fix it in its owning behavior change — do not bolt code onto the catalog.
- [x] 1.2 Author the 14-node tree exactly per design.md D1 (keys/labels/targets/MP costs/prerequisites/coefficient+policies/audience bindings), deleting the five HP-heal keys and re-homing the rest wholesale without aliases; verify the n-ary capstone (枯海之印 Lv.10 + 深淵巨潮 Lv.10) validates at registry load through the existing lineage validator and tip caps derive unchanged.
- [x] 1.3 Confirm the buff-key census: `water_film`, 潮退 tier keys, `mp_regen_lock`, `mana_reflux`, `water_bind` (re-homed bind) all exist with the shipped shapes; delete any leftover dev-era `water_shield` buff reference; verify no dangling `buff_apply:`/`self_buff_apply:` target.

## 2. Echo-test retirement and docs hygiene

- [x] 2.1 Remove `WATER_SPELL_CATALOG` and `WaterSpellCatalogTests` from `world/skills/tests/test_spell_catalogs.py` and the water rows from the tier-correspondence table in the cost-tier test, in-file; adjust a `tools/test_data_lint.json` per-file entry only where its file stops naming shipped content as that linter's output decides; verify remaining suites' substantive coverage is untouched (no waivers).
- [x] 2.2 Docs check under the node-data authority rule: `docs/lore/skill-trees/water.md` untouched; `docs/lore/magic-system.md` §3 water row edited ONLY if a real contradiction surfaces (none found at authoring — record the check); `tests/test_command_docs.py` untouched (no command surface changes); the 2026-08-12 design doc is frozen history — at most a superseded-pointer note if the light precedent row pattern applies, never a table rewrite.

## 3. Behavioral evidence and integration

- [x] 3.1 Disposable offline engine scenario exercising each distinct D1 composition through real casts (drain+share; DoT ladder to zero → suffocation lock via the cast gate; divert exhaust; regen-lock window; max-zero redirect; 束縛 lock; composite take-and-give capstone; branch/convergence gates): observe MP/HP/buffs/locks/practice and delete only after full proof.
- [x] 3.2 Synthetic behavior tests for settlement paths not pinned by the sibling suites (mixed-audience water composite settlement; capstone two-parent gate on water-shaped synthetic data). No catalog-row equality, key-set, cost/tier table or skill-tree-table echo assertions anywhere (ratified NON-GOAL).
- [x] 3.3 Finalize `.github/evennia-shards.json` (this change owns the wave's last manifest edit): register new non-browser modules in exactly one shard; verify the ownership optimization contract test.
- [x] 3.4 Run the focused labels below after editing stops; `tools.observability_lint check` in the same batch; `tools.test_data_lint check`; `tools.spec_traceability check`; `openspec validate water-spell-catalog --strict`. Canonical IDs via `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-sync; annotate exactly the tests establishing them (the removed 水-element ID leaves the ledger with its requirement).

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests.test_spell_catalogs world.skills.tests.test_cost_tiers world.rules.tests.test_skill_lineage world.rules.tests.test_water_mana_tide
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
openspec validate water-spell-catalog --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. `world.rules.tests.test_water_mana_tide` is the intended synthetic settlement module owned by this change, not an existing-test claim. No full local suite/browser/aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn.
