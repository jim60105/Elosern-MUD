# Design

## Context

Observed `typeclasses/components.py::GuildExaminer` uses slot `guild_examiner`. `guild_exams.py::resolve_exam_request_target` resolves a counter separately from `human_guild_hosts.qualified_host`. `GuildAdventurer.profession` defaults to adventurer and `sync_persistent_adventurers` writes it despite no gameplay consumer. The current rulebook still expands counter blueprints, so this first slice keeps that mechanism coherent until direct declarations replace it.

## Goals / Non-Goals

Deliver `R` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

### Exact rename and complete caller categories

Rename the class to `GuildExamReception`, authored type/slot to `guild_exam_reception`, and temporary blueprint key to `guild_exam_reception`. Rename counter-local variables/documentation from examiner to reception where they mean the counter. Keep `examiner`, `ExamQualification`, actual opponent terminology, qualification records and `requested_by` semantics where they mean the actual adventurer.

Change `typeclasses/components.py`, profession_config vocabulary, `rulebook/professions.yaml`, guild_exams, service_view, service_gate capability iteration, web action tests/presenters, command tests and lore/test fixtures. Every import, `.name`, `get_component_slot`, authored type and lookup for the removed counter name must use the new name. No alias or old-slot reader survives. Existing stored old components are unsupported historical state; there is no save repair.

Delete only GuildAdventurer.profession, its constructor/default/validation and `db.profession` write from `world/lore/guild_adventurers.py` and `world/rules/human_guild_hosts.py`. Keep PERSON_ATTRIBUTE, home, profile, seven literal bases, equipment, skill closure, rank and schedules. Preserve E/D/C/B -> altoria_hok, A -> altoria_cassandra, S -> altoria_augustine. Qualification alone never attaches reception. Preserve the request coordinator's schedule-first below-merit response, ordinary examination kit/hold/restoration and current invitation eligibility.

### Closed intermediate behavior

The rulebook still exists and expands the renamed type; imports and sync remain runnable with renamed fixtures. This is an atomic vocabulary cutover, without introducing a second component API. Direct-declaration deletion later removes this temporary blueprint key together with every blueprint.


## Risks / Trade-offs

Shared components.py, profession vocabulary, guild_exams, service_actions tests and shard ownership with H/D/T/P. Serialize with authored-dialogue-refresh-lifecycle and webclient-settlement-alignment when editing guild_exams/service adapters; their mutation/publication logic is unchanged.

The root-level batch contract in `../npc-examination-reception/batch.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb typeclasses.tests.test_components world.rules.tests.test_guild_exam_requests world.rules.tests.test_human_guild_hosts commands.tests.test_guild_economy_commands web.webclient.actions.tests.test_service_actions
uv run --locked python -m tools.contract_gate
openspec validate npc-examination-reception --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
