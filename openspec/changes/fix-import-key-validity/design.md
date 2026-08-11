## Context

`CHARACTER_SCHEMA_V1` (`world/imports/schema.py:15-62`) constrains `key` only to `minLength: 1`; `_structural_issues` (`world/imports/validate.py:89-96`) runs the schema verbatim; the loader instantiates the entity with the raw key (`world/imports/loader.py:44`) and uses it as the portrait stable key (`loader.py:64`). `_handle_damage` serializes `f"damage|{key}|..."` (`world/rules/combat.py:303-312`) and `_entries_from_effect` re-parses with `split("|")` (`world/rules/action.py:573-617`); a `|` in the key shifts fields, raising `EVENT_LOG_CONSTRUCTION_FAILED` after initiative. Batch uniqueness exists only for `world_entry` records (`world/imports/validate.py:282-296`).

## Goals / Non-Goals

**Goals:**
- No accepted key can corrupt `|`-delimited effect serialization.
- No batch can create two entities with one portrait subject.

**Non-Goals:**
- Replacing the `|`-delimited PendingEffect wire format with structured payloads (tracked as a larger refactor; the key contract removes the reachable corruption).
- Renaming existing entities (no users).

## Decisions

**D1 — Schema-level key pattern.** `key` gets `pattern: ^[^|/:{}\x00-\x1f]{1,64}$` in the character schema (and matching world-entry checks), making the restriction structural and enforced before semantic validation. This rule set mirrors the shared key contract hosted by the art stable-key change (`fix-art-pipeline-contracts`); the two changes land with identical constants so no producer set drifts.

**D2 — Batch character-key uniqueness.** Extend the existing duplicate-key scan to `character` records; duplicates become a structural issue that fails the whole batch (all-or-nothing, consistent with `loader.py:74-87`).

**D3 — Parity at character creation.** `_validate_name` (`world/rules/character_creation.py:125-134`) already rejects `|`/`{`/control chars; extend it to reject `/` and `:` and the length bound so the same contract holds for player-created names.

## Risks / Trade-offs

- **Existing example/test data**: any fixtures using separators or >64-char keys are updated in the same change.
- **Display-name semantics**: `display_name` remains a separate free-form field; only the stable `key` is constrained.
