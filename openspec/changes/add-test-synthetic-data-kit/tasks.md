## 1. Python kit

- [ ] 1.1 Create `world/tests/synthetic_data.py`: `t_`-prefixed catalog dicts built from
  the real definition dataclasses (items, skills, subraces/races, presets, npc/monster
  tiers, anchors, regions, city gates, archetypes, shops/economy, quests/issuance,
  titles, dialogue, buffs, acts), with invented zh-TW display prose
- [ ] 1.2 Add the `REGISTRY_TARGETS` table (including the `world/lore/sync.py`
  `_ALL_REGISTRIES` capture) and the `synthetic_registries(...)`
  context-manager/decorator with exact patch/restore (`patch.dict` for mutable
  catalogs, `patch.object` swaps for `MappingProxyType` catalogs) plus the AST
  discovery pass that finds every consumer module binding which name-imported a target
  attribute (cached, patched for the scope — no hand-maintained binding list)
- [ ] 1.2b Add the idempotent `install_synthetic_catalogs()` process bootstrap (D2b):
  under its opt-in environment flag, `web/tests/browser/browser_settings.py` installs
  the synthetic catalogs in the seed/server processes before any startup mirroring;
  default-off leaves shipped behavior identical
- [ ] 1.3 Add the `make_item` / `make_skill` / `make_region` / ... factory helpers with
  local-registration support (`extra=`)

## 2. JavaScript mirrors

- [ ] 2.1 Create `web/webclient-app/tests/support/synthetic-data.mjs` and
  `web/static/webclient/js/tests/support/synthetic-data.js` exporting the shared `t_`
  payload objects outside the `*.test.js` collection glob
- [ ] 2.2 Add a Node-gate mirror self-test (e.g.
  `web/static/webclient/js/tests/synthetic_data.test.js`) asserting the mirrored
  literals; register nothing new in the Node glob beyond the file itself

## 3. Kit self-tests

- [ ] 3.1 Create `world/tests/test_synthetic_data.py` with
  `@covers_requirement("test-data-independence::the-synthetic-test-data-kit-provides-registry-compatible-catalogs")`
  on the shape/collision/gate-clean tests (run the lint scanner API over the kit and the
  JS mirrors; compare kit keys/labels against the shipped token universe),
  `@covers_requirement("test-data-independence::the-kit-patches-and-restores-registries-exactly")`
  on the patch/restore tests (mutable + frozen catalog targets; the discovery pass's
  full binding inventory compared against the AST-scanned set of name-imports of target
  attributes, each discovered binding exercised through its real consumer path; exact
  restoration after scope), and
  `@covers_requirement("test-data-independence::the-kit-installs-process-wide-for-separate-test-processes")`
  on the install bootstrap's idempotency/self-resolution test, and
  `@covers_requirement("test-data-independence::javascript-test-corpora-share-an-equivalent-synthetic-mirror")`
  on the literal-agreement test between Python kit and the JS mirrors. Note: these
  annotation ids live in this change's delta and are unknown to
  `spec_traceability check` until the delta syncs into `openspec/specs/` at archive;
  the annotation step belongs to the archive/sync commit, not this branch
- [ ] 3.2 Register `world/tests/test_synthetic_data.py` in exactly one shard of
  `.github/evennia-shards.json` and keep
  `tests.test_evennia_test_optimization_contract` green
- [ ] 3.3 Run the focused label and
  `uv run --locked python -m tools.spec_traceability check`

## 4. Documentation

- [ ] 4.1 Add the kit section to `docs/development/evennia-testing-guide.md` (when to
  use shared catalogs vs `make_*` local fixtures; the frozen-catalog seam; JS mirror
  rule)
- [ ] 4.2 Run `openspec validate add-test-synthetic-data-kit --strict` and
  `git diff --check`
