# Tasks: declarative-service-hosts

## 1. Roster config

- [x] 1.1 `world/rules/rulebook/guild_economy.yaml`: add `service_hosts:` with the two shipped
  rows reproducing `sync_service_content`'s hardcoded pair — guild master (`profession:
  guild_staff`, kwargs branch_key `guild_branch_altoria` + service_id `altoria_guild_master` +
  dialogue_key `guild_staff`, anchor tag `GUILD_HALL_TAG`'s tag string, names sourced from
  `GUILD_BRANCH_REGISTRY["guild_branch_altoria"]`) and merchant (`profession: merchant`,
  service_id `altoria_merchant`, shop_key `altoria_general_store`, `GENERAL_STORE_TAG`, names
  from the shop registry). Cross-check every value against the current code literals before
  writing.
- [x] 1.2 `world/rules/guild_config.py`: frozen `ServiceHostRow`; parse + batch-validate per the
  delta (fields, profession-row existence, identity-kwargs coverage against the profession
  blueprint, anchor tag non-empty); expose through the catalog read surface;
  `GuildEconomyConfigError`-family naming.

## 2. Shared assembly helper

- [x] 2.1 Create `world/rules/profession_assembly.py`: `assemble_profession_components(entity,
  profession, authored_kwargs, explicit_types=())` — the pure attach loop moved out of
  `world/imports/loader.py::_apply_profession` (component classes resolved via
  `PROFESSION_COMPONENT_TYPES`, attach via `entity.components.add(cls.create(host, **kwargs))`
  guarded by `entity.components.has(...)`); raise a typed `ProfessionAssemblyError(missing=…)`
  for identity-kwargs gaps.
- [x] 2.2 `world/imports/loader.py`: `_apply_profession` delegates to the helper and converts
  `ProfessionAssemblyError` into the existing batch-rejection path; schedule/tier behavior stays
  in the loader.

## 3. Sync interpreter

- [x] 3.1 `world/rules/guild_economy.py`: rewrite `sync_service_content` to iterate the parsed
  roster — resolve room, `_sync_service_host(row)` (new signature), keep
  `_initialize_merchant_stock()` after the loop; delete the `component_specs` literals and the
  `GUILD_SERVICE_KEY` / `MERCHANT_SERVICE_KEY` / `_LEGACY_HOST_KEYS` constants (service_ids now
  live in the roster).
- [x] 3.2 `_sync_service_host`: anchor slot from the row's first blueprint component;
  never-rename/never-retitle reuse, race baseline, `ensure_npc_adult_identity`, creation log
  event unchanged except context gains `profession`.
- [x] 3.3 Replace `_cleanup_legacy_service_hosts` with roster convergence: sweep live NPCs whose
  anchor component `service_id` matches no row, identity-shape guard, ambiguous residue → named
  warning; one info event per deletion.

## 4. Tests

- [x] 4.1 Config tests (pure, in the existing guild-config test module or a new registered one):
  shipped roster parses; each named rejection path; kwargs-coverage check against the blueprint.
- [x] 4.2 `EvenniaTestCase` sync tests: bit-for-bit recreation after host deletion (key, title,
  room, components+kwargs equality against pre-change expectations); double-sync idempotence;
  unknown-anchor warning names the row and skips only that row; roster-shrink deletion + party
  purge; unrelated same-key NPC survives; duplicate-anchor integrity error preserved.
- [x] 4.3 Regression: the entire existing guild/shop/schedule/economy suites pass unmodified
  (behavior-neutrality proof).
- [x] 4.4 `covers_requirement` annotations for both added requirements; shard manifest updated
  for any new test module.

## 5. Verification

- [x] 5.1 Focused Evennia run: `… evennia test … --keepdb world` (guild economy + config + party)
  and `uv run --locked python -m tools.spec_traceability check`.
- [x] 5.2 `uv run --locked python -m tools.observability_lint check`; `compileall -q world`.
- [x] 5.3 Grep proof: no `component_specs`/legacy-key constants remain in
  `world/rules/guild_economy.py`; import path and sync path both call `profession_assembly`.
