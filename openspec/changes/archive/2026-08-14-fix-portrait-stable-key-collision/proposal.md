## Why

Run-2 finding 3 (verified still present at run-3): the `portrait:character:<stable_key>` keyspace is shared by players (stable key = `str(pk)`, a digit-only string) and every other producer — imported entity keys (the raw record `key`, verbatim), blueprint-authored `portrait.stable_key` values, and hand-written templates — and nothing forbids those producers from emitting a digit-only key. When an import record's key equals an existing player's pk as a string, both entities resolve to the identical `art:portrait:character:<key>` record: whichever `ensure()` runs second either overwrites the first entity's `source_hash`/description/`prompt_digest` or transparently reuses the first entity's image as its own, and staff retry/requeue lookups (`_living_entity_for_stable_key`) resolve to the wrong character.

## What Changes

- Reserve the digit-only region of the character-portrait keyspace for player characters, enforced at every non-player producer:
  - The import schema's entity-key pattern rejects digit-only keys structurally (both `character` and `world_entry` record kinds), before any semantic validation.
  - The import key-contract check in `validate.py` mirrors the rejection with a named message.
  - Quest blueprint `portrait.stable_key` validation (the shared characterization helper) rejects digit-only keys, so both the scenario-director guardrail and the deterministic compile boundary refuse them.
- The digit-only rule is hosted once in `world/art/subjects.py` as a shared constant + predicate (`DIGITS_ONLY_KEY_PATTERN`, `is_reserved_player_stable_key()`), and the import schema/validator and the quest characterization helper all consume it — no duplicated rule text.
- Player stable keys stay `str(pk)`; the player-activation path is unchanged and becomes the exclusive owner of the digit-only region by construction. The browser seed already uses the `browser-<pk>` prefix and is unaffected; blueprint template keys (`forest_bandit_chief`) are non-digit and pass unchanged.
- The art layer itself keeps accepting digit-only keys (players are the legitimate owners); enforcement lives at the producers so no future producer can silently drift.
- No migration: the project has 0 users. A dev-database cleanup note for any pre-existing digit-only portrait records is included in the tasks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-stable-key-contract`: the shared producer contract gains the digit-only reservation rule (hosted rule + predicate consumed by import and characterization).
- `import-schema`: "Imported entity keys use a safe character set" extends to reject digit-only keys.
- `import-validation`: "Key charset is checked at import validation" extends to reject digit-only keys.
- `blueprint-portrait-policy`: `portrait.stable_key` validation in the shared bound helper rejects digit-only keys.

## Impact

- `world/art/subjects.py` — hosts `DIGITS_ONLY_KEY_PATTERN` and `is_reserved_player_stable_key()`.
- `world/imports/schema.py` — `_ENTITY_KEY_RULES["pattern"]` gains the digit-only negative lookahead, derived from the shared constant.
- `world/imports/validate.py` — `_check_entity_key_contract` mirrors the rejection.
- `world/quests/characterization.py` — `characterize_errors` rejects digit-only `portrait.stable_key` (covers scenario-director guardrail and compile boundary through the one helper).
- Unchanged: `world/rules/character_creation.py` (player keys stay `str(pk)`), `world/imports/loader.py`, `world/quests/scene_builder.py`, `world/ai/scenario_director.py` + `director_templates.py`, `web/tests/browser/seed.py`, and the entire `world/art/` queue/store/service layer.
- Tests: `world/imports/tests/test_schema.py`, `test_validation_semantics.py`, `world/quests/tests/test_characterization.py`, `test_compile.py`, `world/ai/tests/test_scenario_director.py`, `world/art/tests/test_subjects.py` (predicate unit tests); existing art tests using `"42"` as a *player* stable key stay valid.
