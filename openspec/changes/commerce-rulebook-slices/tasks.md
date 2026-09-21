## 1. The guard first

- [x] 1.1 Capture the resolved shop catalog — every shop's offers, prices, stock and hours —
  before touching anything, and write the test that compares it after. Moving 470 lines of
  YAML by hand is exactly where a row goes missing.
  Captured with a throwaway dumper (`tools/_tmp_catalog_guard.py`, removed at cleanup) that
  resolves the full catalog through `load_commerce_config` + the validators and dumps
  normalized JSON: 8 shops, 67 resolved offers, 2 scales. The split itself was performed
  programmatically from line ranges of the original file with an `assert` that the merged
  parsed sections equal the original parsed sections, so no row was hand-moved.

## 2. The split

- [x] 2.1 Create `rulebook/commerce/scales.yaml` with the `price_scales:` section.
- [x] 2.2 Create `rulebook/commerce/altoria.yaml` with the four capital assortments and the
  four capital shop rows, moved verbatim.
- [x] 2.3 Create `rulebook/commerce/ciaran.yaml` with the four elven assortments and the
  four village shop rows, moved verbatim.
- [x] 2.4 Delete `rulebook/commerce.yaml`.

## 3. The loader

- [x] 3.1 Replace the single `yaml.safe_load` of `commerce.yaml` in `guild_config.py` with a
  sorted read of every `*.yaml` in `rulebook/commerce/`.
  (`guild_config.py` is now the `guild_config/` package; the loader lives in `_loaders.py`.)
- [x] 3.2 Merge: concatenate `assortments:` and `shops:`, merge `price_scales:`. Reject a
  duplicate assortment key, shop key or settlement scale, naming the key and both files.
- [x] 3.3 A parse or shape error must name the offending file, not just the rulebook.
  Parse errors surface as `commerce/<file>: failed to parse: …`, shape errors as
  `commerce/<file>: <section> must be a …`; both covered by tests.

## 4. Coverage

- [x] 4.1 The resolved catalog is unchanged — the task 1.1 comparison passes.
  `diff /tmp/catalog_before.json /tmp/catalog_after.json` is empty after the split and loader:
  every shop's offers, prices, stock and hours byte-for-byte identical.
- [x] 4.2 Sections spread across synthetic files load as one catalog.
  `test_commerce_rulebook_slices.py::test_sections_spread_across_files_load_as_one_catalog`.
- [x] 4.3 A duplicate key across two synthetic files fails naming both.
  `…::test_duplicate_key_across_two_files_fails_naming_key_and_both_files` (subTests over
  assortment key, shop key and settlement scale), plus the shipped-slice load pin.
- [x] 4.4 Run the rules-commerce, guild-config and guild-economy-sync suites plus
  `uv run --locked python -m tools.spec_traceability check`.
  Run and green: guild-config (all seven slice modules, 111 tests incl. the new module),
  shop economy + shop clock sources (49), equipment-effect rulebook (56),
  guild-economy-sync (all seven modules incl. the ciaran-village commerce pair, 75),
  lore shops/settlements, and the shard-ownership contract. `spec_traceability check`:
  1639 requirements, 1639 covered, 0 errors. The delta requirement was pre-synced into
  `openspec/specs/commerce-assortments` so the new tests' IDs resolve (archive re-applies
  idempotently). Note: `tools.test_data_lint check` reports one pre-existing violation in
  `world/rules/tests/test_dialogue.py` (`symbol-ref:DIALOGUE_TABLE`) that is present on the
  master baseline too — untouched by this change and not newly introduced here.

## Duck review dispositions (plan-as-executed critique)

- 🔴 Adopted: PyYAML silently keeps the LAST duplicate mapping key, so a repeated
  settlement scale (or any duplicated mapping field) inside one slice would reprice
  without signal. The loader now parses each slice with a duplicate-rejecting
  SafeLoader (the repo's item_effects/equipment_effects pattern) — commit 1d7fdf78.
- 🟡 Adopted: unknown top-level sections / empty slices are rejected naming the file
  (a typo'd section can no longer load as a silent no-op slice).
- 🟡 Adopted: non-string row keys raise the named GuildConfigError instead of a raw
  TypeError from the owners map.
- 🟡 Adopted: the task-1.1 guard is permanent — the pre-split resolved catalog ships
  as `commerce_catalog_baseline.json` and a covering test compares every shop's
  offers, prices, stock and hours against it.
- 🟢 Adopted: same-file duplicate row keys report `declared twice in commerce/<file>`
  rather than naming one file as if it were two.
