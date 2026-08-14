## Context

Art records are keyed purely by the stable-key string: `record_key(subject)` builds `art:<subject.full()>` (`world/art/queue.py:30-32`), so a character portrait is `art:portrait:character:<stable_key>`, and `ArtAssetRecord` is a durable Script with no live-object reference (`world/art/store.py:1-7`). Every producer of a character `stable_key` therefore shares one keyspace:

- Player activation: `world/rules/character_creation.py:398-414` — `{"mode": "named", "stable_key": str(character.pk)}` (digit-only by construction).
- Import loader: `world/imports/loader.py:78-84` — `record["key"]` verbatim; a record key `"42"` yields the identical policy string as a player with pk 42.
- Quest blueprint portraits: `world/ai/scenario_director.py:151-162` (`BlueprintPortrait`), serialized/deserialized at `:363-368`/`:435-441`, validated at the guardrail (`:759`) and the compile boundary (`world/quests/compile.py:283-325,725`) through the shared helper `world/quests/characterization.py:114-149`, which today accepts digit-only `stable_key` values.
- Hand-written templates: `world/ai/director_templates.py:61` (`forest_bandit_chief` — non-digit, unaffected).
- Browser seeds: `web/tests/browser/seed.py:177-180` (`f"browser-{character.pk}"` — prefixed, unaffected).

The only uniqueness guard today is within-batch duplicate keys (`world/imports/validate.py:311-341`); it never compares against existing player pks. The shared key contract (`world/art/subjects.py:36-38`, `world/imports/schema.py:33-41`, `world/imports/validate.py:102-131`) constrains characters, length, and bytes but never excludes digit-only strings. Consequently an import record whose key equals a player's pk resolves both entities to the same `ArtAssetRecord`: the second `ensure()` overwrites `source_hash`/`source_description`/`prompt_digest` when the record is `missing`/`failed` or silently reuses the first entity's `done` image (world/art/queue.py:95-124), and `_living_entity_for_stable_key` (`world/art/service.py:104-119`) returns whichever character the scan finds first, so staff retry/requeue hit the wrong entity.

## Goals / Non-Goals

**Goals:**
- No non-player producer can ever produce a stable key that equals a player pk string.
- The player convention `str(pk)` stays unchanged (no prefixing, no re-keying, no churn in the creation paths or their tests).
- `validate.py` stays a pure, DB-free module (its CLI runs standalone via `uv run --locked -m world.imports.validate`).
- The shared-helper rule source stays single (`world/quests/characterization.py`), keeping `tests/test_characterization_boundary.py` green.

**Non-Goals:**
- DB cross-check of import batches against live player pks (rejected — D3).
- Cross-batch import-import key identity: two batches naming the same key describe the same intended character; within-batch duplicates already reject, and sharing one portrait record is the documented first-writer-wins behavior, identical to shared blueprint keys (`2026-08-09-generated-named-portraits-design.md`: "Same `stable_key` in two quests → Shared portrait").
- Renaming or reconciling existing entities/records (no users — D5).
- Changing the art layer's acceptance of digit-only keys — players are the legitimate owners and the policy dict cannot distinguish player from NPC (D4).

## Decisions

**D1 — Host the digit-only reservation in `world/art/subjects.py`.** Add `DIGITS_ONLY_KEY_PATTERN = r"[0-9]+"` and `is_reserved_player_stable_key(key) -> bool` next to the existing shared constants (`MAX_SUBJECT_KEY_LENGTH`, `FORBIDDEN_SUBJECT_KEY_CHARACTERS`), with a docstring stating that the digit-only region of the character-portrait keyspace is reserved for player pks. The predicate (not a silent constant) is the single rule source every producer consumes, mirroring how the schema derives its structural pattern from the shared constant set (fix-art-pipeline-contracts D1). ASCII digits only (`[0-9]+`), because Django pks are ASCII-digit strings; a Unicode-digit key (e.g. full-width `０`) cannot equal a pk and stays legal. The rule conservatively also reserves leading-zero digit-only strings (e.g. `"042"`): they cannot equal a pk either, but keeping the pattern a single `[0-9]+` class avoids a special case and over-reservation is harmless.

**D2 — Enforce at the three producer layers, not in the art layer.** Player policies (`str(pk)`) are digit-only by design and the art layer must keep accepting them — `character_subject_for` (`world/art/subjects.py:132-155`) cannot and must not distinguish a player from an NPC. The reservation therefore lives at every non-player producer, in the same structure fix-art-pipeline-contracts D1 used (schema structural + validator mirror + characterization helper):

1. `world/imports/schema.py` — extend `_ENTITY_KEY_RULES["pattern"]` with a digit-only negative lookahead derived from the shared constant: `\A(?!<digits>\Z)[...]{1,64}\Z`, preserving the absolute `\A`/`\Z` anchors (jsonschema validates with `re.search`, so the anchors are what make the lookahead a whole-string check — the same idiom fix-import-key-validity D1 documents). Applies uniformly to `character` and `world_entry` keys: the entity-key rule set is shared (fix-import-key-validity kept it identical for both record kinds), and no legitimate digit-only lore key exists — the reference example and every test fixture use descriptive snake_case keys.
2. `world/imports/validate.py` — `_check_entity_key_contract` adds `is_reserved_player_stable_key(key)` → rejection "digit-only entity keys are reserved for player characters (portrait stable-key collision)", mirroring the schema for the shared-contract philosophy. The named digit-only issue is additionally appended in the structural phase of `validate_character`/`validate_world_entry` (via the shared `_digit_only_key_issues` helper), because a digit-only key always fails the schema pattern and the semantic phase is skipped once structural issues exist — without the structural-phase append, the named message would never reach the report. Only the digit-only check runs in the structural phase; the full contract mirror (printable/byte-bound checks) stays after the early return so pre-existing diagnostics for other structurally invalid keys are unchanged.
3. `world/quests/characterization.py` — `characterize_errors` rejects a digit-only `portrait.stable_key` through the same predicate, so blueprint-authored keys (including templates, which flow through the same validation) fail at both the scenario-director guardrail and the compile boundary with one named message.

The player path (`character_creation.py:410`), the loader, `scene_builder.py:238-246`, the blueprint payload jsonschema, the queue, and the store need no change: a digit-only key is now unreachable from any non-player producer, so the player is the exclusive owner of the region by construction.

**D3 — No DB cross-check against player pks; no player-side prefixing.** Option (a)'s "batch cross-check against existing player pks" is evaluated and rejected: the static reservation makes a pk collision structurally impossible (every pk string is digit-only, and no digit-only key can pass any producer, for all present and future pks), a DB check would (1) couple the pure, DB-free `validate_batch`/CLI to live Evennia state and (2) carry a TOCTOU window (a player created between validation and load) that the static rule does not have. Option (b) — prefixing the player side (e.g. `player-<pk>`) — is also rejected: the main `art-asset-lifecycle` contract pins the player stable key as `str(pk)` verbatim in its web-activation scenario (`openspec/specs/art-asset-lifecycle/spec.md`), so prefixing would change the documented contract, churn both activation paths and their tests, and put the reservation burden on the player side instead of the producers that caused the collision.

**D4 — Art layer unchanged.** `character_subject_for`, recovery, retry, and requeue keep accepting digit-only keys; the fail-closed boundary is the producer set. This preserves the "named portrait" policy semantics and the adult gate untouched.

**D5 — No migrations; dev-DB cleanup note.** 0 users. A dev database that already carries an `art:portrait:character:<digits>` Script created by a numeric-key import (or an old test artifact) should delete just that Script so the player's next ensure recreates the record from the player's own description. No code path or startup fix is involved.

## Risks / Trade-offs

- **Existing fixtures/tests with digit-only entity keys**: none — the example card uses `human_reference`, import tests use descriptive keys, and the art tests that use `"42"` do so as a *player-style* key, which remains valid.
- **Blueprint authors who used a numeric stable key**: none shipped (templates use `forest_bandit_chief`); a numeric key now rejects at validation with a named message and the fix is renaming the key.
- **World-entry keys become digit-only-restricted too**: uniform entity-key contract; no legitimate digit-only lore key exists (all examples use snake_case with letters).
- **Shared-key semantics preserved**: two non-player entities may still share a portrait subject deliberately (blueprint sharing, first-writer-wins); only the unintended player collision is made impossible.
