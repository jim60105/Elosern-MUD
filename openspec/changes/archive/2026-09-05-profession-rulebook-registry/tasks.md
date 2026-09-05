# Tasks: profession-rulebook-registry

## 1. The rulebook file

- [x] 1.1 `world/rules/rulebook/professions.yaml`: `schema_version: 1` + the three shipped rows
  (`merchant` → `[{type: merchant, default_binding: place}]`; `guild_staff` →
  `[{type: guild_staff, default_binding: place}, {type: guild_examiner, default_binding: place},
  {type: scripted_dialogue, default_binding: place}]`; `guild_examiner` →
  `[{type: guild_examiner, default_binding: place}, {type: scripted_dialogue,
  default_binding: place}]`) — mirroring today's `sync_service_content` component tuples exactly;
  every row `schedule_template: null`, `default_tier: null`. Verify against the current
  `component_specs` literals in `world/rules/guild_economy.py::sync_service_content` and note the
  pinning comment in the YAML header.
- [x] 1.2 Header comment stating the assembly-time-blueprint semantics (design R3 D1) and that
  `default_binding` is stored-not-read until service-anchoring (R3 D6 seam).

## 2. The loader

- [x] 2.1 `world/rules/profession_config.py`: frozen dataclasses `ProfessionComponent(type_key:
  str, default_binding: str)` and `Profession(key: str, components: tuple[ProfessionComponent,
  ...], schedule_template: str | None, default_tier: str | None)`, module table +
  `load_professions_into_cache()`, `get_profession(key)`, `all_professions()`,
  `ProfessionConfigError`, following `world/rules/guild_config.py`'s structure (batch validation,
  named errors, nothing cached on failure).
- [x] 2.2 Component-type vocabulary: closed dict `PROFESSION_COMPONENT_TYPES` mapping
  `merchant|guild_staff|guild_examiner|scripted_dialogue` → the classes imported from
  `typeclasses/components.py`; keep the mapping module-level and importable so the contract test
  reads it.
- [x] 2.3 Cross-validation: schedule keys from `world/rules/npc_schedules.py`'s loaded template
  table (reuse its existing rulebook loader — do not re-parse the YAML), tiers from
  `world.lore.races.STATIC_TIER_REGISTRY`, bindings from `{person, place}`.

## 3. Tests

- [x] 3.1 `world/rules/tests/test_profession_config.py` (`unittest.TestCase`, pure): shipped-file
  loads and matches the three replica rows; one named-rejection test per validation rule of the
  delta (schema_version missing/wrong, no `professions:` list, unknown top-level key, empty and
  duplicate key, unknown component type, bad binding, unknown template, unknown tier);
  frozen-read immutability; each rejection asserts nothing was cached.
- [x] 3.2 Vocabulary contract test: every component class defined in `typeclasses/components.py`
  appears in `PROFESSION_COMPONENT_TYPES` values and every mapped key resolves to a class in that
  module (parse the module with `inspect`/`ast`, no DB).
- [x] 3.3 `covers_requirement` annotations on the four requirements (IDs from
  `uv run --locked python -m tools.spec_traceability list`).
- [x] 3.4 Register `world/rules/tests/test_profession_config.py` in exactly one shard of
  `.github/evennia-shards.json`.

## 4. Verification

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  world` (focused) and `uv run --locked python -m tools.spec_traceability check`.
- [x] 4.2 `uv run --locked python -m compileall -q world` and
  `uv run --locked python -m tools.observability_lint check` (loader logs its load event through
  the `world.observability` facade with a `context`).
- [x] 4.3 Repo-wide grep proving `default_binding` has no runtime consumer outside the loader and
  its tests.
