# Design

## Context

world/imports/assembly.py resolves blueprint-minus-explicit overrides. profession_assembly owns attachment and binding. PlaceDefinition in world/lore/settlements/places.py owns profession and flat authored_kwargs; _hosts.py derives ServiceHostRow. Current six blueprint sets are merchant, guild_staff, guild_examiner (renamed by R), quest_issuer, attendant and clergy. All shipped schedule_template/default_tier values are null.

## Goals / Non-Goals

Deliver `D` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

### Exact direct input and shared core

Retain imported field `components`, independent of profession. Each entry has exact required `{type, kwargs}` and optional `binding`. `binding`, when required, has exact `{kind:"person"}` or `{kind:"place",anchor_room:<nonempty room tag>}`; no anchor on person, no dbid authoring. Reject unknown keys, types, duplicates, unknown kwargs and runtime-owned fields. The vocabulary is the six H slots. PlaceDefinition replaces profession/authored_kwargs with `components: tuple[CapabilityDeclaration,...] = ()`, a frozen carrier of exactly the same fields as JSON. ServiceHostRow carries validated frozen component declarations, host_key/profile/name and spawn_room (the former row anchor_room used for initial location). A hosted place may declare zero capabilities; hostless rows carry none. No flat kwargs projection or implicit binding based on place type survives.

New `world/rules/npc_capabilities.py` owns COMPONENT_TYPES, CapabilityDeclaration, CapabilityPlan, CapabilityValidationError, `validate_capabilities(entries, *, room_resolver)` and `assemble_capabilities(entity, plan, *, reconcile=False)`. Validation is pure until injected room resolution; assemble accepts only a complete validated immutable plan. Imports and roster use this one owner. Room tags resolve to exactly one Room, rejecting missing/ambiguous/non-Room references before batch persistence. Resolve all plans after separately owned interior preparation in the outer transaction; failed preparation/resolution rolls back interiors too. No partial host batch, warning-and-skip or first-room fallback.

Required kwargs are service_id+shop_key for merchant, service_id+branch_key for staff/reception, service_id for quest issuer with optional issuer_key (empty/absent retains existing npc:#dbid identity), service_id+church+initial_arousal for church_host. Validate registry references and existing church baseline values with existing owners. scripted_dialogue requires dialogue_key; optional service_id is ordinary config, never host identity. Native service capabilities require binding. A narrative-only scripted_dialogue omits binding and carries no anchor; its conversation uses the existing talk/co-presence/schedule gates and grants no service entry. An explicitly service-associated dialogue requires binding; it is added by P's explicit associations later. Bound scripted dialogue may retain binding for existing talk gating, without becoming a service.

Authored kwargs never include service_binding, anchor_room_id, merchant_stock or last_restock_day. The core alone persists binding fields; H's config allowlists and managed reconciliation remain authoritative. Missing/unknown binding on a bound service now fails closed in service_gate. Allow unbound narrative dialogue only through its separate ordinary-talk path; remove the generic binding=None means allowed branch for service operations.

### Exact producer conversion

Convert every PlaceDefinition row in places_altoria_lower.py, places_altoria_middle.py, places_altoria_upper.py and places_ciaran.py. Expand the currently authored blueprint at planning-defined conversion: merchant -> merchant+scripted_dialogue; guild_staff -> guild_staff+guild_exam_reception+scripted_dialogue; attendant -> scripted_dialogue; clergy -> scripted_dialogue+church_host; quest_issuer -> quest_issuer. Copy each row's own consumed kwargs into its own component; copy row service_id only to components requiring it; each existing place-bound component explicitly anchors at that place.key. No runtime expansion remains after conversion. Keep venue `church` flags as place-owned metadata in a dedicated `church` boolean on PlaceDefinition; church derivation reads it, and ChurchHost config authors the same validated venue identity. Keep assortments, goods, geography, profile identity and explicit schedules unchanged. Source schedules remain with profile/host lifecycle; imported explicit schedule still uses set_npc_schedule. Imported literal stats always merge race floor and never read profession tier. Existing explicit npc_tier creation paths remain independent.

Delete profession_config.py, profession_assembly.py, rulebook/professions.yaml, imports/assembly.py, profession_row caches, plan_bindings, project_row_kwargs, expansion/override tests and unused exports. Replace assembly tests with direct behavioral tests. Remove profession registry loader/inventory/reference metadata and docs including GM world-data registry inventory. Reject legacy profession fields through closed schema, never ignore or translate them. No unused adventurer profession remains after R.

### Logging cutover

Replace import_profession_assembled with import_capabilities_assembled using char and components context. Keep guild_service_host_created with char, host_key, profile and component type list; remove profession and first-component shop inference. Existing lifecycle events retain their deterministic after-commit boundaries. Record the current event contract in docs/development/adding-npcs.md and the changed delta scenarios; the 2026-09-02 historical design is not rewritten. Run `uv run --locked python -m tools.observability_lint check` with focused logging tests at apply handoff.


## Risks / Trade-offs

D follows H to avoid losing reuse identity when blueprints disappear. Shares places/imports/guild_config/core specs with title-authoring N; N follows D. Content batches keep profile/topic identity and may run before D; serialize docs and lore fixture changes. No active content prose is reauthored.

The root-level batch contract in `../npc-examination-reception/batch.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.imports.tests world.rules.tests.test_guild_config.test_service_host_roster world.rules.tests.test_service_binding_persistence world.rules.tests.test_guild_economy_sync world.rules.tests.test_service_gate
uv run --locked python -m tools.contract_gate
openspec validate npc-direct-capability-declarations --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
