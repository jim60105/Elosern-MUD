# Tasks: profession-import-assembly

## 1. Schema fields

- [x] 1.1 `world/imports/schema.py`: add optional `profession` (non-empty string or null) and
  optional `components` (list of `{type, kwargs}` shape-checked objects) to `CHARACTER_SCHEMA_V1`;
  registry membership, vocabulary, kwargs-field membership, duplicate types,
  components-without-profession, and identity completeness are SEMANTIC checks.
- [x] 1.2 Schema-description rows for both fields (the schema's description text is
  contract-tested — keep the age-gate doc requirement green).
- [x] 1.3 `validate_character`/`validate_batch` gain an optional `typeclass` parameter (default
  `None` = NPC target) so the PlayerCharacter+profession rule is a named batch ISSUE, not a
  mid-construction raise; the loader threads its own `typeclass` through.

## 2. Assembly resolution + loader assembly

- [x] 2.0 `world/imports/assembly.py` (new, pure): `resolve_plan(profession, record)` is the ONE
  deterministic resolution algorithm (D5: blueprint minus explicit types; an explicit same-type
  entry replaces the blueprint entry entirely; extra vocabulary entries append in record order),
  plus `explicit_map`, `component_field_names` (from `cls._fields`), `identity_fields`, and
  `missing_identity_kwargs` (identity fields = class DBFields ∩ {service_id, shop_key,
  branch_key, dialogue_key}). Validator and loader BOTH consume it — no drift.
- [x] 2.1 `validate.py`: `_check_profession_fields` rejects (as named issues, before any entity
  is constructed) unknown profession keys, vocabulary-external component types, kwargs keys
  outside the class's DBField names, duplicate types, `components` without `profession`, and
  identity kwargs missing from the FINAL resolved plan.
- [x] 2.2 Trait tier branch: `_resolve_trait_values(record, tier: str | None = None)` — tier
  used only when `record["stats"]` is empty, routing through
  `build_initial_traits(race, subrace, tier)`; otherwise the unchanged race-floor + literal-stats
  path (byte-identical for `tier=None`). Thread the row's `default_tier` from
  `_instantiate_validated_character`.
- [x] 2.3 `_apply_profession(record, entity, typeclass)` called from
  `_instantiate_validated_character` after attribute writes, inside the same transaction: absent
  `profession` is a first-statement no-op; re-runs `assembly.resolve_plan` fail-closed as the
  second gate; attaches every planned component through the same component-attach path the guild
  sync uses (`components.add(cls.create(entity, **kwargs))` guarded by `components.has(cls.name)`).
  The loader never invents identity values.
- [x] 2.4 `schedule_template` handling: non-null + `isinstance(entity, NPC)` →
  `set_npc_schedule(entity, {"schema_version": 1, "template": <key>})`; null → no-op. One
  `import_profession_assembled` info event per assembled NPC (context: char, profession,
  components) — the imports boundary trace the catalog asks for.

## 3. Tests

- [x] 3.1 Schema/semantic tests (`world/imports/tests/`, pure): unknown profession key names the
  record; bad component type; unknown/duplicate/kwargs-outside-fields entries;
  components-without-profession; PlayerCharacter+profession rejection; both-fields-absent fixtures
  validate byte-identically (re-run the existing example through the validator and diff).
- [x] 3.2 Loader tests (`EvenniaTestCase`): D5 precedence (explicit guild_staff wins, blueprint
  scripted_dialogue still attaches, no duplicate slot; extra vocabulary entries attach);
  incomplete identity plan rejects the batch as a named issue with NOTHING persisted; assembly
  failure mid-batch persists nothing; tiered-profession + empty-stats traits equal
  `initial_trait_config(race, subrace, tier)`; literal stats beat tier; template-applied vs
  null-template schedule state. (Package label `world.imports` already covers new modules — no
  shard-manifest change.)
- [x] 3.3 Byte-identity pin: load one pre-change fixture record through the new loader and assert
  every seam attribute + trait values equal the frozen expected state; the no-profession path
  never consults the profession registry.
- [x] 3.4 `covers_requirement` annotations (literal IDs) on all three delta requirements.

## 4. Verification

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  world` focused on imports tests; `uv run --locked python -m tools.spec_traceability check`.
- [x] 4.2 `uv run --locked -m world.imports.validate world/imports/examples/example_character.json`
  behaves the same as the master baseline (master currently fails with Django
  ImproperlyConfigured before this change — that CLI bootstrap is a separate concern; this
  change must not make it worse).
- [x] 4.3 `uv run --locked python -m tools.observability_lint check` and `compileall -q world`.
