# Proposal: profession-import-assembly

## Why

The profession registry (change `profession-rulebook-registry`) is inert until authored records
can reference it. Imported character records are the user's named-NPC pipeline
(`world/imports/`), and today they carry no way to say "this NPC is a merchant" — component
assembly, schedule templating, and tier defaults are either absent or must be hand-pinned in
`stats`. This change wires the import path to the blueprint: assembly-time only, per-NPC
overrides win, and an absent `profession` keeps byte-identical behavior.
Source design: `docs/superpowers/specs/2026-09-05-profession-registries-design.md` (§4, D4/D5).

## What Changes

- `CHARACTER_SCHEMA_V1` gains two optional fields: `profession` (string, must name a registry
  key — unknown keys reject the whole batch) and `components` (list of
  `{type, kwargs}` pairs, type constrained to the profession vocabulary) validated by the same
  batch pipeline.
- The loader assembles after construction, inside the existing per-record transaction:
  - components = blueprint components minus every type the record lists explicitly (D5
    precedence), each attached with its kwargs; a blueprint component whose identity kwargs
    (`shop_key`, `branch_key`, `service_id`, `dialogue_key`) cannot be fully supplied from the
    record's explicit `components` entry or a same-type blueprint default is a named batch
    rejection — the loader never invents identity values;
  - `schedule_template`: when the profession row's template is non-null, the constructed NPC
    receives `set_npc_schedule(npc, {"schema_version": 1, "template": <key>})`; the shipped
    rows are all null, so no shipped profession schedules anything;
  - `default_tier`: when the profession row's tier is non-null and the record declares empty
    `stats`, trait construction routes through `initial_trait_config(race, subrace, tier)`
    instead of the plain race floor; a record with literal `stats` keeps its literal values —
    imported base stats stay literal (AGENTS.md invariant).
- `profession` is only valid for NPC-targeted records; a PlayerCharacter record declaring it is
  a named rejection (professions assemble NPC components; PC identity owns none of those seams).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `import-schema`: the two optional fields with their vocabularies and the batch-rejection rule
  for an unknown profession key (plus the NPC-only rule).
- `import-loader`: blueprint assembly semantics — explicit-components precedence, no invented
  identity kwargs, template application, tier-only-when-stats-empty rule, and byte-identical
  behavior when `profession` is absent.

## Impact

- `world/imports/schema.py`, `world/imports/loader.py`, `world/imports/tests/` (schema + loader
  tests), `world/imports/examples/example_character.json` gains a comment row only if the
  `import-reference-example` contract demands it (checked, else untouched).
- Depends on: `profession-rulebook-registry` (registry reads). Dependents: none mandatory —
  `declarative-service-hosts` reuses the same assembly helper directly.
- No player-facing commands, no webclient surface.
