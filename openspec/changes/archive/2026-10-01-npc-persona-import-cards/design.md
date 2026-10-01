## Context

See proposal.md for motivation. `world/imports/validate.py::validate_character(record, typeclass=None)` already resolves `_is_npc_target(typeclass)` (`None` → NPC default, else `issubclass(typeclass, NPC)`) for profession checks, and stores a normalized record (`report.record`) that the loader instantiates. `world/imports/loader.py::_instantiate_validated_character` writes `entity.db.persona = record["persona"]` inside the batch transaction; `instantiate_character` and the batch loader take `typeclass` (default `NPC`). The CLI validates against the NPC default. `CHARACTER_SCHEMA_V1["properties"]["persona"]` is `{"type": "object"}` with a "never inspected" description.

## Goals / Non-Goals

**Goals:** NPC imports carry a complete valid card and get versioned metadata like every other NPC; player/non-NPC imports are byte-for-byte unchanged; the reference example is a real compact card.

**Non-Goals:** any persona rewriting or summarization by a model; restricting player imports; a compatibility reader for old NPC import files (pre-release).

## Decisions

### D1. Discriminate on the resolved class, never on record content

The card check runs exactly when `_is_npc_target(typeclass)` is true for the class the caller passes to both validation and instantiation. A record cannot opt out (there is no typeclass field in the record), and a `PlayerCharacter` target never sees the check. Alternative rejected: a schema-level `oneOf` keyed by a record field — the design forbids trusting a claimed typeclass inside the record.

### D2. Validation reports contract reasons as named issues and normalizes

`_check_npc_persona_card(record)` calls `normalize_card`; an `NpcCardError(code, field)` becomes `Issue(f"persona.{field}" if field else "persona", f"{code}: …")`, so the existing "every issue names the record, field, and reason" rule holds. On success the report's record carries `persona = card.to_record()` (normalized), so the loader persists exactly what was validated. Only one card issue is reported per record (the contract stops at the first violation) — acceptable because the CLI is iterative and the reason names the leaf.

### D3. The loader writes NPC personas through the initializer

For an NPC target the loader calls `initialize_npc_persona(entity, card, {"kind": "import", "record": record["key"]})` in place of the direct assignment, inside the same batch transaction, so a later record's failure rolls back every card and metadata row with the batch; the initializer's cache restoration covers the rollback. A non-NPC target keeps `entity.db.persona = record["persona"]`. Because import may run in a separate process (`evennia shell`), the foundation's database-held write lock serializes it against server-side editor saves.

### D4. The reference example becomes a Traditional Chinese compact card

The example keeps every other field and branch it already exercises. Its persona becomes a complete card for an ordinary human reference character (public identity, empty-or-short hidden identity demonstrating the optional leaf, explicit speech style, short life story, concrete habit, empty `social_connection` is allowed but one plausible line is preferred to demonstrate the field), with no `background`. The example is validated through the CLI default (NPC target) with zero rejections and zero warnings.

## Risks / Trade-offs

- [Synthetic NPC import fixtures across the suite carry partial personas] → enumerate with `rg` and give them complete synthetic cards via one shared fixture helper; never relax the check in tests.
- [Behavior tests that asserted "persona never inspected" now contradict the contract] → replace them with the new player-target opacity tests (a player target still accepts arbitrary nesting).
- [The look path renders `background` for imported NPCs today] → NPC cards no longer carry `background`; the look path is unchanged and simply has no such section for NPCs. Player imports may still carry it.
