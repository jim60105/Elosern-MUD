## 1. Vocabulary module

- [x] 1.1 Create `world/lore/sex.py` declaring `SEX_VALUES = ("female", "male", "other")` and
      `DEFAULT_SEX = "other"`, with a module docstring naming `CHARACTER_SCHEMA_V1` and
      `LivingEntity.sex` as consumers, matching `world/lore/sexual_vocab.py`'s docstring style.
- [x] 1.2 Add a unit test asserting `SEX_VALUES` equals `("female", "male", "other")` in order and
      `DEFAULT_SEX` equals `"other"` and is a member of `SEX_VALUES`.
- [x] 1.3 Add a test asserting `world/lore/sex.py` imports nothing from `world.rules` or
      `world.imports`.
- [x] 1.4 Add a unit test asserting the module docstring names `CHARACTER_SCHEMA_V1` and
      `LivingEntity.sex` as the consumers of `SEX_VALUES`/`DEFAULT_SEX` (the docstring-names-consumers
      scenario in `entity-sex-vocabulary`).

## 2. Schema

- [x] 2.1 In `world/imports/schema.py`, import `SEX_VALUES` from `world.lore.sex` and add `"sex"` to
      `CHARACTER_SCHEMA_V1`'s `required` list.
- [x] 2.2 Add the `sex` property definition: `{"enum": list(SEX_VALUES)}`.
- [x] 2.3 Add tests in `world/imports/tests/test_schema.py`: a valid record with each of the three
      `sex` values passes; a record omitting `sex` fails on the missing-required-property check; a
      record with an out-of-vocabulary `sex` fails on the enum constraint.

## 3. Typeclass

- [x] 3.1 In `typeclasses/entities.py`, import `DEFAULT_SEX` from `world.lore.sex` and add
      `sex: str = AttributeProperty(default=DEFAULT_SEX)` to `LivingEntity`, immediately after
      `subrace`.
- [x] 3.2 Add a test asserting a freshly created `LivingEntity` (or subclass) reads `entity.sex ==
      "other"` before any value is set.
- [x] 3.3 Add a test asserting a freshly constructed `Monster` (no import record) reads
      `entity.sex == "other"` with no `Monster`-specific override.
- [x] 3.4 Add a test asserting `LivingEntity`'s declared `sex` annotation is `str`, not `str | None`
      (the sex-is-never-None scenario in `living-entity-hierarchy`).

## 4. Loader

- [x] 4.1 In `world/imports/loader.py`, add `entity.sex = record["sex"]` immediately after the
      existing `entity.subrace = record.get("subrace")` line.
- [x] 4.2 Add a test asserting a character instantiated from a valid record carries the record's
      `sex` value verbatim on `entity.sex`.
- [x] 4.3 Add a test asserting the loader never writes `entity.db.sex` (confirms the direct-attribute
      shape, not the seam-attribute shape, per `import-loader`'s new requirement).

## 5. Fixture update

- [x] 5.1 Add `"sex": "female"` to `world/imports/examples/example_character.json`.
- [x] 5.2 Run the full `world/imports/tests/` suite and confirm every call site of
      `world/imports/tests/helpers.py::example_record()` still passes unmodified (8 test files, 52
      combined invocations as of this writing).
- [x] 5.3 Update `docs/gm/characters.md`'s required-field table and JSON example to include `sex`
      (rubber-duck finding: a GM following the doc without `sex` would produce a rejected card).

## 6. Traceability and validation

- [x] 6.1 Run `uv run --locked python -m tools.spec_traceability list` and apply `covers_requirement`
      annotations to the new tests for every requirement added in
      `specs/entity-sex-vocabulary/spec.md`, `specs/import-schema/spec.md`,
      `specs/living-entity-hierarchy/spec.md`, and `specs/import-loader/spec.md`.
- [x] 6.2 Run `uv run --locked python -m tools.spec_traceability check`.
- [x] 6.3 Run `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
      world.imports world.lore typeclasses`.
- [x] 6.4 Run `uv run --locked python -m world.imports.validate
      world/imports/examples/example_character.json` and confirm it passes.
- [x] 6.5 Run `openspec validate entity-sex-field --strict`.
