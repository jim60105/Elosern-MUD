## Why

The user has amended the approved design (`docs/superpowers/specs/2026-10-01-npc-persona-authoring-design.md`, see its §13a) for companions: the partner player preset is the **single authored source of truth** for a companion NPC's characterization — no separate `companion_*` NPC profile, no second authored copy, no prose rewrite of the five designed official presets (the four companions plus 伊洛). The preset template is extended with the fields a persona needs when its character plays an NPC but a player card never uses: the compact card's `speech_style` and the offline `greeting` voice line. The template is consumed only at instantiation: each built companion (one per activating player character, so several may exist) is an independent instance that detaches from the template exactly like the derived persona card already does. The four companion declarations are a small, self-contained source set whose contract extension and producer can be delivered together in one workday.

## What Changes

- `PresetPersona` gains two optional extension fields, both empty by default so every other preset's player-side persona record is byte-identical: `speech_style` (the compact card's required speech leaf, which the player persona contract does not carry) and `greeting` (one bounded offline voice line, ≤300 code points after the card leaf normalizer, single paragraph). The four companion presets author both fields; `speech_style` is newly written per companion and must keep each voice distinct (the twins above naming), while the presets' established identity, appearance, personality, life story, and habit prose stay as designed — the five presets are official characters. Player activation continues to project only its existing persona fields, so the extension fields never reach a player character.
- The companion builder stops copying the preset persona record and instead **derives** the compact card from the partner preset deterministically: `speech_style` from the extension field, structured `appearance` flattened to the card's single text leaf through the card contract's render vocabulary, `social_connection` composed as one factual owner line (`<owner>：<relationship>`) prepended to the preset's own entries, the rest mapped field-for-field. It writes the card through `initialize_npc_persona` with `companion` provenance naming the partner preset key and the owner pk, and persists the authored `greeting` to the companion's bounded per-instance offline-greeting field (`db.npc_offline_greeting`) in the same build, inside the existing delete-compensation. Mechanical values (traits, skills, equipment, ages, portrait policy, `creation_preset_key`) still come from the partner preset.
- This change owns the generic per-instance offline-greeting contract — a bounded single-paragraph authoring field on the NPC instance, outside the seven-field compact card, written only by creation paths that author a greeting (companions here; future bundle/director/import producers may add writers without contract change). Dialogue reads it (specified by `npc-persona-dialogue-consumption`); the author editor edits it (its transport and control are specified by `npc-persona-editor-window`, which therefore depends on this change). The template only seeds it: like the derived card, the built NPC detaches from the preset at instantiation, and an author's edit never writes back to the preset.
- Delete the empty `companions` profile slice (`world/lore/npc_profiles/companions.py` and its entry in `world/lore/npc_profiles/__init__.py`'s assembly), a leftover seam from the archived `npc-persona-profile-registry`: companion characterization is anchored in the partner preset, so a companion profile slice has no referent. The `starting_companion` rows in `world/lore/npc_profiles/inventory.py` remain — their owner label stays `companions` (this change's slice name), but the roster's resolution rule becomes "the partner preset's extended persona" rather than a profile lookup.
- `StartingCompanion` keeps exactly `preset_key`, `affinity`, `relationship` — no `npc_profile_key`, no BREAKING change to the declaration shape. `PresetPersona`, player activation persona records, and existing player characters are otherwise unchanged.

## Capabilities

### New Capabilities

None. (`db.npc_offline_greeting`'s write contract is carried by the `starting-companions` build requirement; its read routing is specified by `npc-persona-dialogue-consumption` and its author editing by `npc-persona-editor-window`.)

### Modified Capabilities

- `starting-companions`: the built companion's persona is derived from the partner preset's extended persona plus the factual owner relationship (the declaration shape is unchanged), and the companion's authored offline greeting is persisted to the NPC's own offline-greeting field at build.

## Impact

- Code: `world/lore/player_presets/vocab.py` (`PresetPersona` extension fields), `world/lore/player_presets/validation.py` (no declaration-shape change; greeting bound check if shaped here), `world/lore/player_presets/data_story_cards.py` and `data_pack_cards.py` (four presets gain `speech_style` + `greeting`), `world/rules/starting_companions.py` (sweep and builder), `world/lore/npc_profiles/companions.py` (deleted), `world/lore/npc_profiles/__init__.py` (assembly entry removed — rebase note: this file was owned by the archived profile-registry change; this is its only later editor).
- Tests: `world/rules/tests/test_starting_companions.py` (existing, rules shard), `world/lore/tests/test_player_presets.py`.
- Docs: `docs/development/adding-player-presets.md` (companion section: the preset persona is now the companion's authored source; `speech_style`/`greeting` documented), checked by `tests.test_preset_authoring_docs_contract`.
- Downstream (not edited here): `npc-persona-dialogue-consumption` reads the instance offline-greeting field ahead of the table and provenance-profile defaults; `npc-persona-editor-window` exposes the field for author editing on its transport delta; `npc-persona-roster-validation` resolves companion sources through the partner preset; `npc-persona-roster-cutover` recomputes built companions with this same derivation and field write.

## Batch:

depends-on: npc-persona-card-foundation
depends-on: npc-persona-profile-registry

Code-conflict notes (revised): owns `world/lore/player_presets/*`, `world/rules/starting_companions.py`, and the `companions` slice deletion + assembly entry alone in this batch. `npc-persona-roster-cutover` later reads the preset-derivation and owner-line rule to replace already-built companions, and `npc-persona-dialogue-consumption` reads the `db.npc_offline_greeting` field; neither edits these files. `npc-persona-editor-window` depends on this change for the field's existence. Shared append-only files: the observability catalog only (no new test module, no data-freeze row: no shipped-prose assertions). Independent of all content slices.
