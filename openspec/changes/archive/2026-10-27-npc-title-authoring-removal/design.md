# Design

## Context

Current producers include CHARACTER_SCHEMA_V1 title, imports loader/semantic checker, GuildAdventurer.title, PlaceDefinition.host_title, GuildBranch/ShopDefinition host_title, BlueprintNpcReq.title, characterization helper, StageNpcCharacterization, materializer and prompt/templates. Generated-packages changes the same package/prompt schemas and must finish first so this slice removes title from its final schema as well.

## Goals / Non-Goals

Deliver `N` as one closed runnable engineer-day slice. Completed prerequisites are the exact depends-on lines in proposal.md.

No new gameplay services, balance, recruitment changes, save migration, legacy input conversion, capability bundles or player class system. The NPC-menu prototype proves layout/navigation only and never authorizes backend behavior. The approved source and archived history remain unchanged.

## Decisions

### Exact removal set

Remove NPC.npc_title AttributeProperty and its creation comments. Delete NPCTitleError, MAX_NPC_TITLE_CODE_POINTS, validate_npc_title and title-specific imports. Retain all NPC name charset/uniqueness validation. In import CHARACTER_SCHEMA_V1 remove the record property/required element `title`; keep the JSON Schema's own metadata `title: CHARACTER_SCHEMA_V1`. Delete _check_npc_title and loader assignment, all source examples/helpers/reference record title keys. Both NPC and PlayerCharacter import no longer require the inert NPC title field; closed schema rejects legacy input. Player title_collection/title_equipped/full_title APIs remain untouched.

Remove host_title/title from PlaceDefinition and every places_* row, ShopDefinition/derived shop readers, GuildBranch literals/validators, ServiceHostRow, GuildAdventurer and human_guild_hosts creation/validation. Retain descriptions, compact persona card identity.public/hidden, NPC tier, social identities and rank. Do not append removed text into key, desc or a replacement short-role field. Narrative role text already authored in descriptions remains unchanged.

Remove `title` from BlueprintNpcReq, its canonical serialization/deserialization, AI package schema, generic and scene prompts, director templates, world/quests/characterization.py, compile/contracts.py StageNpcCharacterization, compile field/payload/compiler propagation, materializer assignment and their generation/scene-builder tests. Keep npc_req.role, tier, display_name, persona, age pair, portrait stable key and existing generated immutable envelope/version rules. Apply the same removal to the generated-packages result, never reintroduce PhaseTopic.response or old keyword effect routes.

No save migration, attributes deletion sweep or legacy package converter. Stored profession/title attributes are inert and unread. Old closed-schema title-bearing input is rejected; historical immutable packages remain historical and unsupported if they violate the current closed schema. Preserve existing documented package rejection boundaries rather than fabricating converted identities.

### Active proposal amendment ownership

The exact planning supersession and source-file conflict matrix lives in section 11 of `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md`. At apply, amend materially affected still-active generated-packages schema, prompt and characterization references and each content batch's identity guidance to require display_name and persona without a title field. Preserve topic IDs, original baseline service semantics and narrative voice. Do not rewrite archived changes or the approved design source.


## Risks / Trade-offs

N follows D/S and authored-dialogue-generated-packages; it changes final generated schemas only after that active cutover. All ten authored-dialogue-content-* batches are prose-only identity consumers; if still active their no-title guidance is amended, without making optional literary work a prerequisite. Serialize places/prompts/templates/docs and traceability with their owners.

The batch contract in section 11 of `docs/superpowers/specs/2026-10-25-npc-capabilities-and-services-design.md` defines sequential cutover, active proposal amendment ownership, source conflicts and approved-scope traceability. New test files named below are proposed additions, not claims that they already exist. Existing focused labels were researched from current source.

## Worker execution contract

This is planning only. At apply time complete this slice within one engineer-day, using the exact interfaces below. Each checkbox includes its focused regression evidence and documentation. Do not add compatibility exports, legacy input readers, migrations, replacement professions, gameplay services, or a new persistent service registry. Deterministic owners retain every mutation; AI and UI propose/select only. Preserve player titles, ranks, age bounds, literal bases, scene roles/tiers, recruitment and possession eligibility, schedules and commerce arithmetic.

All paths are relative to the repository root. Reuse current test helpers and behavioral traceability decorators. Update `.github/evennia-shards.json` and `.github/browser-shards.json` only for changed test ownership; serialize manifest edits. Run focused checks once after the slice is complete, followed by `uv run --locked python -m tools.contract_gate` and strict validation of its delta. Use the project's test environment only during apply. Full browser/traceability suites remain CI-owned. No implementation checks were exercised during planning.

## Focused verification at implementation handoff

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.imports.tests world.ai.tests.test_scenario_director_validation world.ai.tests.test_scenario_director_package world.quests.tests.test_scene_builder.test_characterization world.rules.tests.test_guild_economy_sync
uv run --locked python -m world.prompts.validate
uv run --locked python -m tools.contract_gate
openspec validate npc-title-authoring-removal --strict
```

If this slice changes logging paths, also run `uv run --locked python -m tools.observability_lint check` with its focused event tests in the same final batch. Do not run the full browser or full traceability-evidence suite locally.
