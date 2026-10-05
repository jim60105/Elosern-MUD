## Context

See proposal.md for motivation. The precedent provenance pattern is `world/art/gallery_fallback.py`'s `_declared_key_for_entity`, which already reads `creation_preset_key` / `npc_tier_key` off entities and validates declarations against the live registry — this change generalizes that shape into a typed official-content-reference resolver rather than inventing a second convention. Source design §6 (and §2's amendment 1 for the monster boundary). Consumers (resolution chain, personalization) land after this change and bind to this API.

## Goals / Non-Goals

**Goals:**
- One resolver answering `(entity | preset key | authored channel) -> OfficialContentReference | None`, shared by every consumer.
- Provenance writes ride existing authored-attribute sites, one writer per path, transaction-scoped.

**Non-Goals:**
- No resolution-order change, no payload field, no media-route change (sibling changes own those). No species producer, alias table, or tier mapping — that belongs to the separate, unapproved monster species catalog design.

## Decisions

- **New leaf module `world/art/official_refs.py`** (import-light `gallery_kinds.py` discipline): consumers are presenter-side and spawn-side; a leaf type+resolver avoids the `subjects.py` prompt-layer cycle. The alternative — methods on `ArtSubject` — re-couples the two identities design §6 deliberately separates.
- **Validation through the shared stable-key contract** (`world/art/subjects.py` predicate/pattern), so content keys can never break the media route or filesystem bounds; registry membership is checked against the live registries at resolution time (the `gallery_fallback._declared_key_for_entity` precedent), not cached at import.
- **NPC authored provenance = new attribute `npc_profile_key`**, written where hosts/examiners/occupants are already instantiated. Alternatives rejected: deriving from `npc_tier_key` (a numeric role band the design forbids equating with a named character) and from `display_name` (explicitly banned inference).
- **Monster kind exists in the vocabulary but has zero producers in this change**: the resolver validates `(monster, key)` shape only; a scan test asserts no production module constructs a monster reference. The future species catalog supplies the producer behind this same API, preserving the guarded seams (design §6's "runtime image or built-in silhouette until a species reference exists").
- **Preset preview passes the preset key directly to the resolver** instead of a synthetic entity, so no preview can ever touch character/gallery storage.
- **One published stable-key predicate, not three copies**: `world/art/subjects.py` gains `is_valid_subject_key(key)` and both the catalog's `_content_key_is_valid` and the reference module's predicate delegate to it, so a key the catalog indexed can never be refused at resolution (or the reverse). The kind vocabulary is the one thing duplicated by design (a leaf module may not import the catalog's Pillow/Django chain); a contract test compares it against `world.art.official.OFFICIAL_CONTENT_KINDS`.
- **The unresolved-reference diagnostic is bounded by distinct key**: one `official_content_reference_unresolved` event per `(kind, key)` pair, at most `MAX_UNRESOLVED_DIAGNOSTICS` (64) distinct pairs per process, carrying `kind`, `key`, the entity identity, and a `reason` of `malformed_key` or `unregistered_key`. Re-reading the same bad key is silent after its one event, and pairs beyond the cap are suppressed (the set is memory-bounded and the ceiling is pinned by a test). The authored preset-preview entry point stays silent: a caller-supplied key is not a named entity's stored provenance.
- **Blueprint occupants and import records stay producer-less by construction, not by omission**: the compiled occupant contract is closed (display name, title, age pair, optional stable portrait key, persona card, combat traits) and its persona provenance is `generated_quest`; an import record's provenance is `import`. Adding an import schema field or reading a profile key out of a generated proposal would create a *generated* attachment channel, which the dynamic-NPC rule forbids, so this change adds neither and records the boundary in code with negative tests.
- **`npc_profile_key` is a distinct entity attribute from the persona-meta `{"kind": "profile", "profile": <key>}` provenance** already readable through `world.rules.npc_persona.provenance_profile_key`: that reader lives behind the rules layer (ObjectDB, `django.db.transaction`, the NPC typeclass), which the reference module may not import. The duplication is a creation-time-only authored attribute exactly like the existing `npc_tier_key`, and a test pins the two reads equal for a spawned host and a spawned examiner so they cannot drift.

## Risks / Trade-offs

- [Spawn-path attribute writes widen blast radius] → each write sits next to an existing attribute write in the same transaction; rollback tests per path cover creation, import, blueprint spawn, and host instantiation.
- [Registry-membership-at-resolution cost] → dictionary lookups on module-level registries; no I/O; identical to the fallback resolver's cost.
- [Authors expect `monster/<tier>` directories to work] → the deployment guide (owned by `official-artwork-deployment`) states the species-catalog prerequisite; resolution stays silent-but-fallthrough with the catalog's bounded diagnostics vocabulary.

## Migration Plan

Additive provenance attribute; entities lacking it behave exactly as today. No migration, no backfill (pre-release policy).

## Open Questions

None for this change; the species catalog is a separate design's decision, not an open question here.
