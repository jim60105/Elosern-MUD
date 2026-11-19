# Design

## Context

`world/lore/items/assembly.py` concatenates Python slices in observable order. `world/rules/item_effects.py` and `world/rules/equipment_effects.py` load separate per-item tables and expose validated profiles. Items are stored in inventory and equipment by item key. The equipment enum's value already equals that key for every shipped equipment definition.

## Goals / Non-Goals

**Goals:** One authored item row with its dedicated effects; a cutover that preserves loaded definitions, gameplay, and stored identifiers; exact file provenance on the existing GM detail.

**Non-Goals:** A generic content framework, new effect verbs, a second authoring frontend, live catalog reload, or changes to map formats, prices, offers, authored balance, save formats, and other catalogs.

## Decisions

### D1. Explicit authoring order, one data-only reader

Use `content/items/catalog.yaml` as the only entry point. Its exact keys are `schema_version: 1` and `files`, a non-empty ordered list of distinct `.yaml` basenames other than `catalog.yaml`. Each listed file contains one `items` list; preserve file and row order. Require listed files to be readable regular files resolving inside the catalog directory; reject missing, duplicate, or undeclared YAML files. Adding an item to an existing list changes only that file. An explicit manifest avoids coupling presentation order to filenames.

Rows carry `key`, `display_name_zh`, `price_table_key`, `sellable`, and `presentation`, with optional `guild_property`, `liturgical_role`, `use_mechanics`, or `equipment_slot` under existing meanings. Require keys matching `[a-z][a-z0-9]*(?:_[a-z0-9]+)*` and check every existing key during the scratch export. In particular, a colon would break the existing `buff_key:item_key` attachment identifier. For usable rows, place `effects` inside `use_mechanics` alongside `consumable` and `combat_allowed`. For equipment rows, require `equipment_effects` at row level, including `{}` for utility equipment. Inspect-only rows carry neither form. Use enum values for closed vocabularies, exact booleans and numeric types, and the existing dataclass validation. Reject unknown keys, duplicate keys at every level, non-data YAML constructs, invalid field values and repeated item identifiers across files. Do not add includes, expressions, inheritance, or coercion. Errors name the file and, where available, item key or row position and field. Keep `price_table_key` reference metadata and current authoring-time integrity checks.

### D2. One loaded candidate; existing domain validators own semantics

In `world/lore/items/assembly.py` (and a leaf loader beside it if needed), parse once into an ordered typed definition map, source provenance by key, and raw inline effect inputs keyed by the same row keys. Publish the structurally validated catalog only after all documents parse. Do not import `world.rules` from lore or add effects to `ItemDefinition`; the loaded definition and profile remain separate runtime views. `world/rules/item_effects.py` and `world/rules/equipment_effects.py` consume the same loaded inputs and build their full validated profile maps before making them available. Keep `ItemUseMechanics` flag-only.

Cold-import rejection is intentional: imports from command or startup dependencies may force validation before the startup hook, with a named source error and no guarantee of a startup-step event. Within `server/conf/at_server_startstop.py::at_server_start`, extend the existing fail-loud `equipment_rulebook_validation` step to invoke the two modules' idempotent initialization checks. Each check completes that domain's validation for the loaded production catalog if it has not run; an already validated catalog is not reread or revalidated by the gate. Preserve step order and event identifier. Guarantee rejection before `sync_map_world`, not before `world_clock_init`, which may already persist its singleton. Existing test-only revalidation helpers should consume an injectable candidate and dependencies; never reread item rows independently of their definitions.

Keep `item_effects.yaml` for `item_use_seconds` and `equipment_effects.yaml` for `budgets`; remove their per-item sections. Retain use verb, order, duplicate-stat, duration and scope checks, and equipment rarity, buff, gauge-bound, weapon-only and church-doctrine checks. Do not move or reinterpret any settlement code. Feed row provenance into semantic diagnostics; shared-table errors name their shared file. Keep `ITEM_REGISTRY` and the two existing profile maps as consumer entry points; preserve scoped synthetic override semantics.

### D3. Use the stable item key throughout equipment lookup

Remove `EquipmentModifierKey` and `ItemDefinition.modifier_key` from `vocab.py`, `__init__.py` and all callers. Key `EQUIPMENT_EFFECT_RULES` by plain item key, including in `validate_church_doctrine`, worn-rule reads, weapon and per-item helpers in `equipment_effects.py`, and `world/rules/status_query/breakdown.py`. Preserve each accessor's existing unknown or malformed input behavior. Replace test helpers that borrow arbitrary shipped modifier keys with effect profiles bound to the synthetic items' actual keys. Use semantic shipped-data selectors only for existing production smoke and keep distinct synthetic items distinct in effect maps.

### D4. Attach provenance to the loaded row, not the disk view

Set the `items` source directory in `world/lore/registry_index.py` to `content/items/`. Extend `RegistrySpec` with an optional lazy entry-source lookup used by the items registry, so the browse index remains cheap to import. `web/gm/readers/world.py::detail` adds a top-level `source_path` for entries with exact provenance; `registry.source_path` still identifies the registry directory. `web/admin-app/views/WorldEntryView.vue` uses the detail path for its existing provenance note, falling back to registry metadata for other registries. Do not add item YAML to the raw-file endpoint or open files based on a GM request.

### D5. Keep independent tooling aware of the source change

Add `content/items/*.yaml` to `tools/map_reference_context.py::DISCOVERY_RULES` and regenerate `content/map-reference-context.json` after all covered files stabilize. The standalone editor still checks freshness without importing game code; it does not parse items. In `tools/test_data_lint.py`, drop the retired `RULEBOOK_CATALOG_KEYS` entries for both effect files and verify existing `ITEM_REGISTRY` harvesting still covers all item keys, without adding a second YAML reader or ledger exemptions. The existing `Containerfile` copies `content/`; no runtime dependency or image-layout change is required.

## Risks / Trade-offs

- **Conversion drift:** Export current live definitions and typed profile values once, before removing old declarations. Compare exact registry iteration order and per-item use-effect list order; compare the profile maps by key and value, retaining sorted equipment-profile iteration. The lookup-only use-profile map needs no second ordering declaration. Check expanded builder rows, text, and units. Do not keep a golden catalog or conversion path in production.
- **Import cycles:** Keep the data reader independent of Django, Evennia, and effect modules; let existing validators attach meaning to the raw effect inputs after lore imports. Test production startup as well as pure candidate validation.
- **Fixture fan-out:** Many fixtures currently share enum values. A blind substitution would merge unrelated test items under the wrong effect key; migrate the shared synthetic kit first and keep effect-bearing fixtures paired with their own profiles.

## Migration Plan

Deliver source, consumers, tests, and derived artifacts in one cutover. Amend design decision D9 in `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md`: Git-tracked declarative content may live under `content/`, items adopt this boundary, and existing sources for other domains are unchanged. Deploy by restarting with the new sources; no save migration, compatibility alias, or parallel read. Reverting the code and authored data together restores the prior source layout without a save conversion.
