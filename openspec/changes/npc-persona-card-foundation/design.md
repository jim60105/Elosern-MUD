## Context

See proposal.md for motivation. The authoritative product design is `docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md` (sections 4, 5.1, 10, 12, 13). Current facts this design builds on:

- `world/rules/persona.py::PersonaStore` reads `entity.db.persona`, renders strings as `label + capped value`, renders a mapping `identity` as a `身分：` line followed by `公開身分：…` / `隱秘身分：…` lines capped as one section, joins sections with `\n`, and caps the block at 2,000 code points. Field bound 600, block bound 2,000.
- Persona writers today: the import loader, `starting_companions`, `persona_edit` (player only), `character_creation` (player only), and the scene builder. Service hosts (`guild_economy._sync_service_host`) and exam opponents (`guild_exams._spawn_opponent`) write no persona.
- `world/lore/` must never import `world/rules/` (registry-only), while `world/rules/`, `world/ai/`, `world/quests/`, and `web/` all may import `world/lore/`.
- `world/rules/surfaces.py` provides `attribute_snapshot` / `restore_attribute_best_effort` for Evennia attribute-cache restoration after rollback.

## Goals / Non-Goals

**Goals:**
- One pure contract that producers (lore, rules, quests, ai, imports) and the browser mirror can all apply identically.
- A persistence writer whose version semantics are correct under two browser sessions and a concurrent import process.

**Non-Goals:**
- The profile vocabulary, inventory, place reference, and dialogue split (`npc-persona-profile-registry`); authoring any profile, switching any creation path to the writer, prompt changes, voice routing, the editor, or the cutover (later changes).
- Restricting the persona shape of player characters, monsters, or any non-NPC living entity.

## Decisions

### D1. The contract lives in `world/lore/npc_card.py`, pure and dependency-free

The card contract is vocabulary (shape, bounds, labels), which lore owns; placing it under `world/lore/` lets the lore profile registry validate profiles at import without the lore→rules import that `world/lore/guild.py` has to defer. It imports nothing from Evennia, Django, or `world/rules/`. Alternative rejected: `world/rules/npc_card.py` (forces function-local imports from lore and from the shared quest characterization helper, which is deliberately rules-light).

Public surface (names are binding for later changes):
- `NPC_CARD_FIELDS` — storage key set; `NPC_CARD_RENDER_ORDER = ("identity", "appearance", "personality", "speech_style", "life_story", "habit", "social_connection")` — `speech_style` adjacent to `personality`.
- `REQUIRED_TEXT_LEAVES` = `identity.public`, `appearance`, `personality`, `speech_style`, `life_story`, `habit`; optional leaves `identity.hidden`, `social_connection` persist as `""`.
- `normalize_card(raw) -> NpcCard` raising `NpcCardError(code, field)`; `NpcCard` is a frozen dataclass with `to_record()` (the exact `db.persona` dict) and `from_record()`.
- `render_card_block(card) -> str` and `card_budget(card) -> CardBudget(per_leaf, identity_section, total, remaining_total)`.
- Stable error codes: `card_not_object`, `unknown_field`, `missing_field`, `not_text`, `required_empty`, `leaf_too_long`, `identity_section_too_long`, `card_too_long`; `field` names the leaf as `identity.public`, `identity.hidden`, or the top-level key (`None` for `card_not_object`/`card_too_long`).
- Bounds re-exported as `LEAF_LIMIT = 600`, `IDENTITY_SECTION_LIMIT = 600`, `CARD_BLOCK_LIMIT = 2000`; a parity test pins them to `persona.FIELD_LIMIT`/`BLOCK_LIMIT`.
- `NPC_PERSONA_CONTENT_GENERATION = 1` and `NPC_CARD_FORMAT = 1`.

Normalization: `\r\n` and lone `\r` become `\n`, outer whitespace is stripped from every leaf, interior text is kept verbatim; text is never interpreted as markup or template. Code points are Python `len()` of the normalized string (astral characters count once). Booleans, numbers, `None`, lists, and nested objects other than the `identity` object reject with `not_text`.

### D2. Rendering parity with `PersonaStore` is a tested invariant, not a reimplementation risk

`render_card_block` reproduces exactly what `PersonaStore.flatten(NPC_CARD_RENDER_ORDER)` emits for a valid card: `label + value` for text sections, the `身分：` header plus `公開身分：`/`隱秘身分：` lines (hidden omitted when empty), empty optional sections omitted, sections joined with `\n`. Validation measures the identity section and the total on that rendered string, so a valid card can never be truncated by the reader. A parity test renders the boundary fixture cards through both paths on a stub entity and asserts equality and absence of the `…` marker. `PersonaStore` keeps its generic behavior; the only edit is the `speech_style` → `說話風格：` label.

### D3. Metadata is a separate attribute with a closed provenance vocabulary

`db.npc_persona_meta = {"format": 1, "generation": 1, "persona_version": <int ≥ 1>, "provenance": {...}}`. Provenance kinds (closed; validated by `validate_provenance` in the contract): `{"kind": "profile", "profile": key}`, `{"kind": "companion", "profile": key, "owner": pk}`, `{"kind": "import", "record": key}`, `{"kind": "generated_quest", "quest": key, "stage": int, "occupant": int}`, `{"kind": "offline_bundle", "pool": key, "bundle": key}`. Provenance carries identities only, never prose. Meta is never inside `db.persona`, never flattened, and only `persona_version` is ever projected outward (by the editor change).

### D4. One writer core; three entry points in this change

`world/rules/npc_persona.py`:
- `read_npc_persona(npc) -> NpcPersonaSnapshot | NpcPersonaUnavailable` — never writes; NPC family only; unavailable reasons `not_npc`, `missing_card`, `missing_meta`, `corrupt_card`, `corrupt_meta`, each emitting `npc_persona_unavailable` (warn) with `npc` and `reason`.
- `initialize_npc_persona(npc, card, provenance)` — used by every creation path in later changes. Normalizes and validates before writing; writes card + meta (`persona_version = 1`, current generation) atomically; if the NPC already carries a meta record with the current generation it returns the existing snapshot unchanged (repeated spawn/reuse never overwrites). Returns the snapshot.
- `update_npc_persona(npc, card, expected_version, *, actor)` — the editor writer. Rejects booleans/non-integers for the version. Outcome is one of `updated(new_version)`, `unchanged(version)` (exact equality of the complete normalized card, still version-checked), `version_conflict(current_version)`, `invalid(NpcCardError)`, `unavailable(reason)`, `storage_unavailable`.

All three share `_write_card(npc, card, meta)`. Writes run inside `transaction.atomic()`; the version comparison reads the persisted meta from the database (the `Attribute` row, not the Evennia attribute cache) after the transaction has taken the database write lock with a guarded no-op `UPDATE` of the NPC's `ObjectDB` row. This serializes the editor (server process) against a concurrent import run through `evennia shell` (separate process) on SQLite, and is a row lock elsewhere. The re-read MUST bypass Evennia's idmapper (`SharedMemoryModel` returns cached `Attribute` instances): read the value with a query that does not materialize the cached instance (`values_list("db_value", flat=True)`) or `refresh_from_db()` on the instance, never `Attribute.objects.get()` alone. The guarded `UPDATE` is the first statement of the write path, before any read, so a caller's outer atomic block that has not yet written does not hold a snapshot that SQLite cannot upgrade; an `OperationalError` (database locked/busy) is caught at the writer boundary, the caches are restored, an event is emitted, and the outcome is `storage_unavailable` (never a raw exception to the editor; initializers re-raise it as `NpcPersonaStorageError` so the caller's all-or-nothing transaction fails). Alternative rejected: an in-process lock (does not cover the import CLI process) and check-then-assign (explicitly forbidden). On any exception the caller's snapshots of `persona` and `npc_persona_meta` are restored with `restore_attribute_best_effort` before re-raising, so no reader observes an uncommitted card.

### D5. Commit-bound events, no prose

`npc_persona_initialized` (info: `npc`, `source` = provenance kind, `profile` when present, `version`), `npc_persona_updated` (info: `npc`, `char` = acting character, `version_from`, `version_to`), `npc_persona_update_rejected` (info: `npc`, `char`, `reason`), `npc_persona_unavailable` (warn: `npc`, `reason`). Success events are registered with `transaction.on_commit`. No card text, hidden identity, or dialogue ever enters context. The four rows are added to the catalog in `docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.2.

## Risks / Trade-offs

- [Stale idmapper read defeats the cross-process check] → mandated non-cached re-read plus a test that changes the meta row behind the cache with a queryset `.update()` and expects a conflict.
- [A refactor moves the read before the lock] → an ordering test with `CaptureQueriesContext` asserts the guarded `UPDATE` precedes the meta `SELECT` inside the atomic block.

- [Rendering drift between contract and `PersonaStore`] → parity test over the shared boundary fixture; any `PersonaStore` rendering change fails it.
- [Guarded `UPDATE` adds a write to read-only no-op saves] → acceptable: editor saves are rare and the lock is what makes the no-op version check correct.

## Migration Plan

None. No persisted data changes; the new attribute is written only by later producers and the cutover.
