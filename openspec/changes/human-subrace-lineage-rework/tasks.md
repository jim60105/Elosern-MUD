# Tasks: human-subrace-lineage-rework

Mirror design doc §3.5 (files) and §8 (testing). Do NOT touch the §3.6 sites: the
`StaticTier` key `human_commoner` at `world/lore/races.py:137-138`,
`world/lore/npc_tiers.py:41,43,45,46,48` (`static_tier_key`),
`world/lore/tests/test_races.py:118`,
`world/rules/tests/test_profession_config.py:283,289` (`default_tier`),
`openspec/specs/entity-trait-scales/spec.md:142-143` — all name the unrelated static-tier
concept. `web/static/webclient/js/tests/protocol.test.js:3132` stays too (deliberate
synthetic fixture with invented names 竈生民).

## 1. Code

- [x] 1.1 Rewrite the five human `Subrace` entries in `world/lore/races.py`: rename keys
      `human_wealthy`→`human_coastal`, `human_commoner`→`human_plains`,
      `human_laborer`→`human_highland` (`human_royal`/`human_noble` keep keys); set
      `display_name_zh`/`common_name_zh` to 王族/王室血脈, 貴族/貴族血脈, 濱海民/濱海血脈,
      平原民/平原血脈, 山地民/山地血脈; replace the five `specialty` strings verbatim with
      §3.3's zh-TW lineage prose; keep every `StatModifiers` value and the 王族
      `vital_overrides {"mp": (120, 220)}` unchanged. Verify: importing `world.lore.races`
      succeeds and the delta-spec naming scenarios hold.
- [x] 1.2 Rework `world/lore/starting_kits.py:32-36` to the §3.4 table: `human_coastal` →
      `plain_sword`, `leather_armor`, `iron_dagger`; `human_plains` → `plain_sword`,
      `leather_armor`, `silver_hairpin`; `human_highland` → `plain_sword`, `leather_armor`,
      `hunting_throwing_axe`; 王族/貴族 kits unchanged; `wooden_club` removed from every
      kit. Verify: kit-registry load validation passes.
- [x] 1.3 Update `world/lore/player_presets.py:278`: 艾莉莎 (`elysa_snow`) subrace
      `human_commoner` → `human_plains`. Verify: preset registry imports.

## 2. Tests

- [x] 2.1 Update `world/lore/tests/test_races.py`: the `HUMAN_SUBRACES` tuple (27-33) to the
      five new keys, and `test_human_subraces_exist_with_bloodline_names` (159-166) to the
      new bloodline naming; keep the `human_commoner` StaticTier assertion at line 118
      untouched; add one test asserting the retired subrace keys resolve nowhere in shipped
      registries (SUBRACE_REGISTRY, kit registry keys, preset subraces) and decorate it
      `@covers_requirement("lore-registries::human-lineage-renames-ship-without-a-save-data-compatibility-layer")`
      — the new requirement gets coverage or `tools.spec_traceability check` fails it as
      uncovered. Verify: targeted run of `world.lore.tests.test_races` passes.
- [x] 2.2 Update the 12 `subrace="human_commoner"` fixture sites in
      `world/lore/tests/test_player_presets.py` (lines 117, 146, 236, 261, 300, 343, 369,
      394, 419, 519, 558, 706) to `human_plains`. Verify: targeted run of
      `world.lore.tests.test_player_presets` passes.
- [x] 2.3 Update the 16 `human_commoner` subrace-key sites in
      `world/lore/tests/test_starting_kits.py` (lines 76, 81, 86, 91, 96, 101, 106, 112,
      119, 124, 129, 136, 138, 140, 151, 164) to `human_plains`, and assert the new §3.4
      human kit table (three COMMON triads; no `wooden_club` anywhere), decorating that
      assertion `@covers_requirement("lore-registries::human-starting-kits-express-lineage-character-not-an-affluence-ladder")`.
      Verify: targeted run of `world.lore.tests.test_starting_kits` passes.

## 3. Data and fixtures

- [x] 3.1 Update `world/imports/examples/example_character.json:10` (`subrace`) and
      `web/browser_support/browser_fixtures_data.py:61` (`SHIPPED_BASE_SUBRACE`) from
      `human_commoner` to `human_plains`. Verify: the import example and browser-fixture
      loaders resolve the subrace key in `SUBRACE_REGISTRY`.

## 4. Specs and docs

- [x] 4.1 Apply this change's delta to `openspec/specs/lore-registries/spec.md` (the
      modified Subrace-registry requirement text at :115 and its scenarios, incl. :154's
      bloodline-ordering scenario, plus the two ADDED requirements) during archive — do not
      hand-edit the main spec ahead of archive. Verify: `openspec archive` output contains
      the requirement.
- [x] 4.2 Update `docs/lore/overview.md:39` and
      `docs/development/adding-player-presets.md:63,76` to the new keys/names. Verify: the
      retired-term grep (task 5.4) reaches zero in `docs/`.
- [x] 4.3 Update `tmp/story_settings/world_info.md`: line 42, the human subrace list at
      141-146, line 156, and add the new human 〈數值傾向〉 block mirroring the beastfolk
      「亞種數值傾向」 block's format (design principles + per-lineage rationale per §3.2:
      王都王室重統御學識 / 領地貴族自幼習劍術馬術 / 港市海岸船上作業練就輕捷 /
      東部平原農耕與工坊並重 / 西部丘陵谷地礦坑與工坊重勞動). Verify: the five modifier
      rows in the block match `races.py` exactly.
      NOTE: `tmp/` is gitignored (`.gitignore:87`) and NOT present in the worktree — edit
      `tmp/story_settings/world_info.md` in the main checkout (`/var/home/jim60105/repos/MUD`);
      the edit is invisible to git by design and must be verified by reading the file back.

## 5. Verification

- [x] 5.1 Run the canonical Evennia runner —
      `MUD_TEST_SETTINGS=1 uv run --locked python -m evennia test --settings test_settings.py --noinput world.lore world.rules`
      — and confirm it passes (bare pytest fails with `ModuleNotFoundError: No module named
      'django'`; do not use it). DEVIATION (owner steer + AGENTS.md ≤10-min rule): replaced
      with scoped canonical runs covering every affected label — full `world.lore` (173 tests
      incl. `world.lore.tests.test_sync`, DB-backed), `world.imports` (166, loads
      example_character.json), `world.rules.tests.test_character_creation` (66) — all OK.
- [x] 5.2 Run `uv run --locked python -m tools.spec_traceability check` and
      `uv run --locked python -m tools.test_data_lint check`; both pass with every
      `@covers_requirement` slug still resolvable (no requirement heading was renamed).
      Note: no test modules added or renamed, so `.github/evennia-shards.json` needs no
      update.
- [x] 5.3 Re-run the DB rebuild / `world.lore.sync.sync_all` path used by the test settings
      and confirm no shipped data references a retired subrace key (the three orphan
      `lore:subraces:*` Scripts exist only in pre-rebuild databases; adding pruning to
      `sync_all` is out of scope). Verified via the fresh-test-DB `world.lore.tests.test_sync`
      run (exact `lore:` Script count over every registry, no orphans) plus the retired-key
      registry test and the fixture grep sweep.
- [x] 5.4 Grep sweep to zero — each of `human_wealthy`, `human_laborer`, `底層平民`,
      `富裕平民`, `農民與勞工`, `中小貴族`, `皇族與大貴族`, `普通平民` has no match outside
      `.worktrees/` and `openspec/changes/archive/`. Also sweep the overview.md fullwidth
      variant `皇族／大貴族` of §8's 皇族與大貴族 term (it is the form actually present at
      `docs/lore/overview.md:39`), and `商人與高階冒險者` / `工匠、商人、冒險者` (the retired
      `common_name_zh` occupation lists). Retirees of `human_commoner` outside the §3.6
      static-tier sites are covered by tasks 1–4 and verified by the targeted test runs;
      the string itself legitimately survives at the §3.6 sites.
