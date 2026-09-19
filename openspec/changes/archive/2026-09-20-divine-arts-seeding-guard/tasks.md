Every test command below runs with `MUD_TEST_SETTINGS=1` supplied through the Bash tool's `env`
input — an inline prefix is rejected by the Evennia test guard.

## 1. Preset registry guard

- [x] 1.1 In `world/lore/player_presets.py::_validate_preset_disguised_stats`, reject a non-empty
  `disguised_stats` when `RACE_REGISTRY.get(preset.race)` is `None` or declares no divine arts,
  raising with the preset key and the reason. Follow `_validate_preset_skill_kits`'s existing
  fail-closed phrasing so both validators read alike, and update the validator's docstring, which
  currently states the check is shape-only.
- [x] 1.2 Cover it with a behavior test over a SYNTHETIC preset registry, not the shipped cards
  (design D6): a divine-capable card with a layer validates, a non-divine card with a layer raises, a
  card whose race does not resolve raises, and a non-divine card with an empty declaration validates.
  Verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_player_presets`.

## 2. Import validation guards

- [x] 2.1 Add `_check_disguised_stats_race(record)` to `world/imports/validate.py` returning the
  bloodline rejection for a non-empty `disguised_stats` on a race that cannot use divine arts or does
  not resolve, and wire it into the rejection pipeline beside `_check_disguised_stats_subset` so both
  issues can be reported for one record.
- [x] 2.2 Extend `_check_skills` to reject a `skills`/`passives` key whose registry entry declares
  `requires_divine_arts` on such a record, reusing the resolved registry the function already holds
  so the check degrades with the existing degraded-state reporting rather than rejecting everything
  when the registry is unavailable.
- [x] 2.3 Cover both with behavior tests over SYNTHETIC records in
  `world/imports/tests/test_validation_semantics.py`, matching that module's existing record-builder
  style: the divine-capable, non-divine, unresolvable-race and empty-declaration cases for the layer;
  the `skills`, `passives`, divine-capable, non-divine-skill and degraded-registry cases for
  ownership; plus the both-issues-reported case. Verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb world.imports.tests.test_validation_semantics`.

## 3. Bring shipped content into line

- [x] 3.1 Empty the `disguised_stats` block in `world/imports/examples/example_character.json` to
  `{}` (the key stays — `CHARACTER_SCHEMA_V1` requires it), keeping `race: "human"` per design D5.
  Verify with
  `uv run --locked -m world.imports.validate world/imports/examples/example_character.json`, which
  must report no issues.
- [x] 3.2 Update `world/imports/tests/test_reference_example.py`'s
  `test_reference_example_is_clean_and_exercises_contract` to assert `disguised_stats` is empty
  (design D7) instead of a non-empty subset of `stats`, then verify the reference-example contract
  still holds:
  `uv run --locked evennia test --settings test_settings.py --keepdb world.imports.tests.test_reference_example`.
- [x] 3.3 Confirm no shipped preset card violates the new preset guard — the lore registry raises at
  import, so `uv run --locked python -c "import world.lore.player_presets"` succeeding IS the check.
  If it raises, the named card is real content that needs a content decision, not a guard weakening.

- [x] 3.4 (Discovered during implementation, design D7) Replace the `import-reference-example`
  requirement "exercises every major schema branch" via `REMOVED`+`ADDED` under a new title in
  `specs/import-reference-example/spec.md`, since its disguised_stats scenario asserted the field
  non-empty — no longer true for the human baseline record under the new guard. Repoint the
  `covers_requirement` call in `world/imports/tests/test_schema.py` that named the old ID, and add
  the new ID to `test_reference_example.py`'s existing contract test.

## 4. Docs and traceability

- [x] 4.1 Add the two new rejection rows to the validator table in
  `docs/development/adding-player-presets.md`, and correct §107's prose, which currently states the
  axis names carry no whitelist and implies no other constraint on the field. Verify with
  `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_preset_authoring_docs_contract`.
- [x] 4.2 Annotate the new tests with `covers_requirement` for the three ADDED requirements, taking
  the literal IDs from `uv run --locked python -m tools.spec_traceability list` rather than composing
  them. Verify with `uv run --locked python -m tools.spec_traceability check`.
- [x] 4.3 Verify the data-contract gate stays clean — the new tests use synthetic fixtures and must
  NOT be added to `tools/test_data_freeze.json`:
  `uv run --locked python -m tools.test_data_lint check`.

## 5. Verification

- [x] 5.1 Confirm no new test module was created, so `.github/evennia-shards.json` needs no entry:
  the new tests live in `world.lore.tests.test_player_presets`,
  `world.imports.tests.test_validation_semantics` and
  `world.imports.tests.test_reference_example`, all already registered.
- [x] 5.2 Run `openspec validate divine-arts-seeding-guard --strict` and verify it reports no errors.
- [x] 5.3 Re-read the design's Non-Goals and verify the diff adds no runtime check inside a writer,
  no migration, and no change to the cast gate or the display layer.
