## Why

The forthcoming sexual act system scopes `virgin`-breaking to vaginal intercourse with an
opposite-sex partner (same-sex, anal, and interspecies acts never break it — see
`docs/superpowers/specs/2026-08-15-sexual-act-system-overview-design.md` D-12 and
`docs/superpowers/specs/2026-08-15-sexual-act-catalog-design.md` §4.1). That branch cannot be
evaluated today: no notion of sex or gender exists anywhere in the codebase. `CHARACTER_SCHEMA_V1`
declares `age`, `apparent_age`, `race`, and `subrace` and nothing else identity-related, and
`LivingEntity` carries no comparable attribute. This change adds the minimal field the later branch
needs, with no mechanic of its own.

## What Changes

- Add a new canonical vocabulary module, `world/lore/sex.py`, declaring `SEX_VALUES = ("female",
  "male", "other")` and `DEFAULT_SEX = "other"`. Follows the existing `world/lore/sexual_vocab.py`
  precedent: a dependency-free constants module read by both the import schema and, later, act
  catalog logic, so the value set has exactly one owner.
- Add a required `sex` property to `CHARACTER_SCHEMA_V1` (`world/imports/schema.py`), constrained to
  `SEX_VALUES` by JSON Schema `enum`. An import record must declare a value explicitly — `"other"`
  is a valid, deliberate declaration, not merely a fallback.
- Add `sex: str = AttributeProperty(default=DEFAULT_SEX)` to `LivingEntity`
  (`typeclasses/entities.py`), immediately after `subrace`. Any entity constructed without going
  through the import loader — every `Monster` today, since no bestiary/spawn system exists yet, and
  any `LivingEntity` built before this field reaches it — reads `"other"` until told otherwise.
- Update `world/imports/loader.py` to assign `entity.sex = record["sex"]` during instantiation,
  mirroring the existing `entity.race = record["race"]` / `entity.subrace = record.get("subrace")`
  lines exactly.
- Update `world/imports/examples/example_character.json` to declare a `sex` value, which cascades to
  every test built on `world/imports/tests/helpers.py::example_record()` (8 test files, 52 combined
  invocations today; none reference `sex` in a way the fixture update would break).

**BREAKING**: `sex` becomes a required `CHARACTER_SCHEMA_V1` property. Any import record missing it
now fails structural validation. Per project convention (pre-release, zero users), no migration path
is provided; the one shipped example record is updated in this same change.

## Capabilities

### New Capabilities
- `entity-sex-vocabulary`: the canonical `SEX_VALUES`/`DEFAULT_SEX` constants in
  `world/lore/sex.py`, mirroring `sexual-vocabulary`'s existing treatment of
  `world/lore/sexual_vocab.py` as a dependency-free, single-source-of-truth lore module.

### Modified Capabilities
- `import-schema`: `CHARACTER_SCHEMA_V1` gains a required `sex` property.
- `living-entity-hierarchy`: `LivingEntity` gains a `sex` attribute, defaulting to `"other"` (a
  different default shape than `race`/`subrace`'s `None`, since the vocabulary already has an
  explicit "unspecified" value and does not need a second null state).
- `import-loader`: the loader assigns `entity.sex` from the validated record.

## Impact

- **Affected code**: `world/lore/sex.py` (new), `world/imports/schema.py`,
  `world/imports/examples/example_character.json`, `typeclasses/entities.py`,
  `world/imports/loader.py`.
- **Affected tests**: every test built on `world/imports/tests/helpers.py::example_record()` keeps
  passing once the shared fixture gains `sex` (8 files, 52 combined invocations: `test_schema.py`,
  `test_batch_all_or_nothing.py`, `test_loader_trait_values.py`, `test_age_gate.py`,
  `test_reference_example.py`, `test_import_portrait_seam.py`, `test_validation_semantics.py`,
  `test_record_dispatch.py`); no test currently asserts the exact required-field set as a fixed
  list, so no other file needs updating for the schema change alone.
- **Also touches**: `import-reference-example`'s governed artifact
  (`world/imports/examples/example_character.json`). That capability's existing requirement already
  states the example "stays valid against `CHARACTER_SCHEMA_V1`" without enumerating fields, so this
  change needs no delta spec against it — the existing requirement text already covers the new
  required property.
- **Not affected**: `world/rules/character_creation.py` (the player-creation wizard). Player
  characters are not built through `CHARACTER_SCHEMA_V1` and are out of scope for this change — see
  Out of Scope in `design.md`. A freshly created player character reads the class-level `"other"`
  default until a future change wires the creation wizard to collect it.
- **Downstream consumer**: the later `sexual-catalog-partner` proposal (`C4` in the sexual-act-system
  design set) reads `entity.sex` to decide which `sexual.yaml` event 交合/深度交合 emits. This change
  ships the field only; no behavior reads it yet.
