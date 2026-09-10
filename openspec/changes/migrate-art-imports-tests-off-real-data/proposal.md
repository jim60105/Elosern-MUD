## Why

Art gallery/prompt/worker and imports tests hardcode armor, plain_sword, iron_shield, archetype keys, and CJK subject prose. Art startup-sync tests iterate shipped archetype/tier registries intentionally and move to the contract class instead.


The full game-data rework (maps, items, skills, magic, characters, quests) will break
these 23 test files even where no rule behavior changes. The
`test-data-independence` contract allows shipped-content references only in explicitly
tagged data-contract tests; art, imports, and prompts behavior tests are the remaining debt in this
area.

## What Changes

- Migrate the 23 flagged test files under world/art/, world/imports/, world/prompts/ to the synthetic test-data kit
  (`world/tests/synthetic_data.py`) or file-local synthetic fixtures
  (14 assertion-literal files, 8 setup-literal files, 1 quantity-pinned files).
- Replace every shipped-identifier literal and shipped display-prose literal in the
  migrated files with kit constants or locally built synthetic definitions; replace
  pinned data quantities with values derived from the patched synthetic catalogs.
- Where a shared helper is part of this area's debt, rewrite its builders on kit data so
  every borrower stops inheriting shipped ids.

- Restate converted assertions as the mechanics the owning OpenSpec requirement
  describes. A test that only echoes synthetic-fixture content is deepened or deleted;
  a deleted test's `@covers_requirement` annotation moves onto the replacement test.
  A deleted test MUST name the test that exercises the same production branch; a test
  that is the only evidence for a branch is retained, never deleted for gate
  cleanliness (the aggregate coverage gate stays the CI-owned floor).
- Remove this area's debt entries from `tools/test_data_freeze.json` and add the area
  closure test in `tests/test_data_independence_art_imports.py`. Its `@covers_requirement` annotation is added in the
  archive step that syncs this delta into `openspec/specs/` — the traceability index only
  knows main-spec ids, so annotating earlier would fail with `unknown-requirement-id`.

### Migrated files (tier S = quantity-pinned, A = assertion literal, B = setup literal)

| file | tier |
| --- | --- |
| `world/art/tests/test_art_observability.py` | B |
| `world/art/tests/test_connectivity.py` | B |
| `world/art/tests/test_gallery.py` | A |
| `world/art/tests/test_gallery_fallback.py` | A |
| `world/art/tests/test_gallery_match.py` | A |
| `world/art/tests/test_gallery_prompt.py` | A |
| `world/art/tests/test_gallery_seed.py` | B |
| `world/art/tests/test_presenter.py` | B |
| `world/art/tests/test_queue.py` | A |
| `world/art/tests/test_scheduler.py` | B |
| `world/art/tests/test_sd_worker.py` | A |
| `world/art/tests/test_service.py` | A |
| `world/art/tests/test_subjects.py` | S |
| `world/art/tests/test_worker.py` | A |
| `world/imports/tests/test_degraded_banner.py` | B |
| `world/imports/tests/test_loader_trait_values.py` | A |
| `world/imports/tests/test_profession_assembly_loader.py` | A |
| `world/imports/tests/test_profession_assembly_schema.py` | A |
| `world/imports/tests/test_schema.py` | A |
| `world/imports/tests/test_validation_semantics.py` | B |
| `world/prompts/tests/test_degrade.py` | A |
| `world/prompts/tests/test_loader.py` | B |
| `world/prompts/tests/test_verbatim_shipment.py` | A |

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `test-data-independence`: adds the Art, imports, and prompts closure requirement — every test file in this
  change's migration manifest passes the test-data lint gate and the manifest's freeze-list
  debt entries are removed. Files under world/art/, world/imports/, world/prompts/ owned by other changes (contract-tagged
  files, sibling migration areas) are unaffected by this requirement.

## Impact

- The 23 listed test files plus the new closure test file `tests/test_data_independence_art_imports.py`.
- `tools/test_data_freeze.json` shrinks by exactly the listed entries (shrink-only
  ratchet; this change removes entries only).
- No production code, no shipped data, no player-command surface changes (docs untouched
  unless a command-surface bug is discovered — then `tests/test_command_docs.py` applies).
- The closure test is a top-level repository check under `tests/` (owned by
  `unittest discover`, outside the Evennia shard manifest). Migration edits themselves
  add no new Evennia test modules, so `.github/evennia-shards.json` stays untouched.
