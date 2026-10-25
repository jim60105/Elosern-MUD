# Design

## Context

Observed NpcProfile has key/card/ages/voice but no structured social identity; imports have race/subrace and opaque persona. Character creation snapshots explicit attributes. A separate persisted tag set is necessary; prose parsing and title-string heuristics violate the approved condition contract.

## Goals / Non-Goals

**Goals:** Typed social identity source without parsing persona prose. Deliver this runnable slice and its acceptance within one engineer-day.

**Non-Goals:** Unowned runtime/content work, compatibility migrations, new game effects and per-line server stepping.

## Decisions

Shared contract v2 uses this same acting-body identity reader for static/generated scenes. Generated roles may have an empty typed identity set and need no NpcProfile. Model-authored persona/scene prose never creates social tags or bypasses deterministic construction ownership.

Implement a bounded identity source, separate from hierarchy and racial status. Add frozen SocialIdentity(key, display_name_zh), read-only SOCIAL_IDENTITY_REGISTRY and deterministic set_social_identities(entity, keys) in world/rules/social_identity.py. Store sorted unique canonical keys in entity.db.social_identities; read_social_identities(entity) returns frozenset without creating storage; missing means unknown/empty, never commoner by default. Initial neutral label vocabulary is `noble`/貴族, `clergy`/神職人員, `official`/官員, `adventurer`/冒險者; these are membership tags, with NO numeric rank/order and no race-derived assignment. Expose no status editing UI or inferential runtime assignment.

Imports gain OPTIONAL social_identities array, <=8 unique registered keys; omission is empty; schema and semantic validation reject unknown/bool/prose values before writes. NpcProfile and PlayerPreset gain social_identities tuple default (); producers pass these explicit keys through set_social_identities during normal new construction. For this bounded source slice, all existing authored defaults remain empty unless a profile's explicit canonical role establishes one of the four labels; never parse npc_title/card/persona or equate elves with nobility. Populate canonical guild host as official, on-duty watch profiles as official, temple/sanctum profiles as clergy, and canonical guild adventurer construction as adventurer only from typed producer identity. Document these exact producer assignments and preserve age/card bounds. Custom player creation defaults empty; preset construction accepts explicit registry metadata, with snapshot/restore including social_identities. Do not derive tags from an equipped cosmetic title, guild rank or edited biography. Guild registration can add adventurer only through an explicit deterministic set-union call in its existing transaction with compensation.

The change is runnable through import and new character/NPC creation, independent of dialogue conditions. No world-state migration/backfill and no assumption of a universal class hierarchy. Existing characters with missing field stay unknown until an authorized typed creation/domain write establishes it. Content writers may add a key only with an explicit registry declaration and mandatory source review; unknown keys fail validation. Add docs of the import field and data-author semantics, not world prose. If a listed producer file differs, use its existing profile-application function rather than inventing a parallel constructor.

Exact producer integration is guild_economy._create_and_initialize_host for service-host profile tuples, human_guild_hosts.py for typed adventurer rows, starting_companions.build_starting_companion for partner preset tuples, imports.loader._instantiate_validated_character and character_creation activation for player presets. Do not teach initialize_npc_persona to parse tags from card/provenance or overwrite runtime identities when editing persona. Profile tuples are explicit source metadata, never inferred from display titles.

## Implementation handoff constraints

This proposed slice is capped at one engineer-day. Each numbered task is intended as a 45-120 minute implementation-and-focused-test unit; tests/docs land with their owning behavior. Use a local untracked `.env.test` containing `MUD_TEST_SETTINGS=1` for the commands below (create that environment file only at apply time). Run focused commands from the repository root; new test labels are explicitly proposed, existing labels are regression targets. Also run `uv run --locked python -m tools.contract_gate` before implementation handoff, with test ownership updates in the same feature commit. No live external model/image requests. Planning created no production code or test results.

Boundary events use the existing world.observability facade with available owner/actor/npc/topic/context identifiers; exceptions rethrow or log once with exc. No new telemetry subsystem. No compatibility shim, legacy aliases, data backfill or migration. No executable dialogue scripts, mid-scene choice tree, per-line server stepping/persistence or new gameplay effects.


## Exact target files

- `world/lore/social_identities.py (new)`
- `world/rules/social_identity.py (new)`
- `world/imports/schema.py`
- `world/imports/validate.py`
- `world/imports/loader.py`
- `world/lore/npc_profiles/shape.py`
- `world/rules/npc_persona.py`
- `world/lore/player_presets/vocab.py`
- `world/rules/character_creation.py`
- `world/rules/guild_economy.py::_create_and_initialize_host`
- `world/rules/human_guild_hosts.py`
- `world/rules/starting_companions.py`
- `world/rules/guild.py`
- `world/lore/npc_profiles/{altoria_guild,altoria_lower,altoria_upper}.py`

## Risks / Trade-offs

Shares profile shape/application and creation/import paths with later explicit content metadata only. Independent of runtime/player; physical conditions depend on this. Guild.py overlap with progression integration is serialized by dependency. Keep authored source validation separate from runtime eligibility. A failed post-commit push recovers on the next canonical sync, without reversing a successful owning commit. Read the approved design and dependency artifacts before edits; no interface decision is left open.

## Focused verification at implementation time

```text
uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.rules.tests.test_social_identity world.rules.tests.test_character_creation
uv run --locked python -m tools.contract_gate
```

Run only focused test labels/methods within the repository time limits. Full managed browser and evidence suites remain CI-owned. These commands are planned acceptance, not results from proposal creation.
