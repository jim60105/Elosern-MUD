# Design

## Context

build_services_view(actor, viewed) independently resolves one staff, examiner and merchant. service_actions validators omit provider identity and _resolve_local selects a room host. Shop/guild UI consumes room-wide surfaces. request_guild_exam already accepts speaker and validates the actual counter separately from the qualified opponent. Existing host-independent quest abandonment/tracking must remain host-independent.

## Goals / Non-Goals

Deliver `T` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

### Targeted deterministic contract

Add `world/rules/service_targets.py::require_service_target(actor, npc_id, component_class)` returning the exact live co-present visible NPC and component or a stable rejection. Use the current exploration target resolver/visibility rules; reject missing, bool/nonpositive/non-safe integer, invisible, departed, wrong component, failed binding/schedule/control/permission. Never fall back to a different provider. Domain APIs still validate the passed host and own writes. Explicit host APIs accept multiple same-class bystanders; remove accidental room-uniqueness checks inside domain APIs when an exact host is already supplied. Implicit text commands may retain their existing ambiguity error because they did not select a host.

Extend build_services_view with keyword-only `provider_id`; targeted mode resolves guild/staff/reception/merchant solely on that NPC and keeps no other room provider's surfaces. The existing untargeted full services panel retains room discovery for room/global UI, with explicit provider metadata added per non-null guild/shop/rank section. Do not repurpose top-level display-only host as authority. Introduce action `services.open` with exact `{npc_id}` returning a private, read-only result containing the targeted services snapshot; register as a session read with no game clock/effects. Existing drawers opened from a provider read this correlated local result. Subsequent canonical services pushes may refresh targeted drawers only by repeating services.open for the same target after current committed state settles. Do not persist a selected provider on NPC/actor or install polling.

Bump services panel schema 7 -> 8 in Python registry, exact serializers and UMD mirror together. Keep section existing fields and add `provider_id` (positive JS-safe integer) to guild and shop, plus `provider_id` to rank for the reception identity; targeted guild can be absent when provider has reception only, so publish a top-level nullable `rank` section independent of guild and remove guild.rank. This preserves a reception-only provider's existing examination route. Move rank validators/menu consumers/fixtures in the same cutover; personal quest log/inventory remain in their existing panels. services.open private result uses the identical schema-8 snapshot plus requested npc_id; reject mismatched result target/transport generation.

### Exact action payload changes and callers

Required npc_id is added only to provider-dependent `guild.register`, `guild.quest_accept`, `guild.quest_turnin`, `guild.exam_request`, `shop.buy`, `shop.sell`. Keep every existing argument and bound, including recipient_id/seller_id. Do not add npc_id to host-independent `guild.quest_abandon` and `guild.quest_track`, private escort abandonment, personal inventory, equipment or skill actions. Migrate producers in service_view, serializers, UMD service menu builders, app frame-resolvers/drawers, action allowlists, tests/story fixtures and docs to required npc_id in one change. Unknown/missing fields reject; no optional legacy payload.

The exam adapter passes the explicitly resolved reception as speaker to request_guild_exam. The qualified adventurer remains separately selected by EXAM_QUALIFICATIONS. Preserve schedule-first below-merit requests and existing terminal settlement metadata from webclient-settlement-alignment. Possession keeps merchant access and suppresses guild/reception as before. Combat suppresses provider operations without changing personal information.

### Closed intermediate behavior

Before the new interaction card exists, the existing guild/shop drawers work through provider IDs already supplied by their room-discovered surfaces and use services.open on entry. A second merchant no longer makes a targeted drawer ambiguous; the untargeted room summary can still report ambiguity. services.open never performs registration, purchase, exam start or a dialogue effect.


## Risks / Trade-offs

T follows R and active webclient-settlement-alignment to preserve its service exam causal receipt; shares service_view/actions/protocol/constants/frame resolvers with P/U and active publication/immutable work. No change to protocol envelope E/R/B or publication queue ownership. Serialize shared service fixtures and schema registry.

The root-level batch contract in `../npc-examination-reception/batch.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_service_view web.webclient.presentation.tests.test_services_panel web.webclient.actions.tests.test_service_actions world.rules.tests.test_guild_exam_requests
node --test web/static/webclient/js/tests/protocol_services_a.test.js web/static/webclient/js/tests/protocol_services_b.test.js
uv run --locked python -m tools.contract_gate
openspec validate npc-targeted-service-flows --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
