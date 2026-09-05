# Tasks: profession-import-assembly

## 1. Schema fields

- [ ] 1.1 `world/imports/schema.py`: add optional `profession` (non-empty string; validated
  against `profession_config.get_profession` — validator-layer, same all-or-nothing batch) and
  optional `components` (list of `{type, kwargs}`; `type` ∈ `PROFESSION_COMPONENT_TYPES`;
  `kwargs` a flat string→value mapping) to `CHARACTER_SCHEMA_V1`; reject `profession` on
  PlayerCharacter-targeted records (the loader's `typeclass` parameter is known at validation
  entry — if it is not, thread it through `validate_record`).
- [ ] 1.2 Schema-description rows for both fields (the schema's description text is
  contract-tested — keep the age-gate doc requirement green).

## 2. Loader assembly

- [ ] 2.1 `world/imports/loader.py`: add `_apply_profession(record, entity) -> None` — resolve
  the blueprint row; compute blueprint-minus-explicit component set; merge kwargs (record entry
  wins per D5; identity kwargs missing → raise the batch's validation-failure path, never
  invent); attach each through the same component-attach call the guild sync uses; apply
  `set_npc_schedule` for a non-null template on NPC entities only.
- [ ] 2.2 Trait tier branch: `_resolve_trait_values(record, tier: str | None = None)` — tier
  used only when `record["stats"]` empty; thread the profession row's `default_tier` from
  `_instantiate_validated_character`.
- [ ] 2.3 Call `_apply_profession` from `_instantiate_validated_character` after attribute
  writes, inside the same transaction; keep the absent-`profession` path a no-op guard as the
  first statement.
- [ ] 2.4 `world/observability`: emit one `log_info` event per assembled NPC (`context` =
  `{"char": key, "profession": key}`) — the imports boundary trace the catalog asks for.

## 3. Tests

- [ ] 3.1 Schema tests (`world/imports/tests/`, pure): unknown profession key names the record;
  bad component type; PlayerCharacter+profession rejection; both-fields-absent fixtures validate
  byte-identically (re-run the existing example through the validator and diff the result dict).
- [ ] 3.2 Loader tests (`EvenniaTestCase`): D5 precedence (explicit guild_staff wins, blueprint
  scripted_dialogue still attaches, no duplicate slot); missing identity kwargs rejects the batch
  and persists nothing; assembly failure mid-batch persists nothing; tiered-profession +
  empty-stats traits equal `initial_trait_config(race, subrace, tier)`; literal stats beat tier;
  template-applied vs null-template schedule state. Register the module in
  `.github/evennia-shards.json` if new.
- [ ] 3.3 Byte-identity pin: load one pre-change fixture record with and without the feature
  flags and assert every seam attribute equals.
- [ ] 3.4 `covers_requirement` annotations on all three delta requirements.

## 4. Verification

- [ ] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  world` focused on imports tests; `uv run --locked python -m tools.spec_traceability check`.
- [ ] 4.2 `uv run --locked -m world.imports.validate world/imports/examples/example_character.json`
  still passes untouched.
- [ ] 4.3 `uv run --locked python -m tools.observability_lint check` and `compileall -q world`.
