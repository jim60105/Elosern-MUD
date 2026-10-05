## 1. Reference core

- [ ] 1.1 Create `world/art/official_refs.py` with the frozen `OfficialContentReference(kind, key)` type, stable-key-grammar validation, registry-membership resolution, and a zero-import-cycle boundary test (mirrors `gallery_kinds.py` discipline)
- [ ] 1.2 Implement provenance-derived resolution for preset, npc, and monster kinds (display-name/tier/row-identity inference structurally impossible) and verify resolver unit tests cover valid, unregistered, malformed, and inference-trap cases with bounded diagnostics

## 2. Preset provenance

- [ ] 2.1 Bind preset resolution to the existing `creation_preset_key` provenance and verify two same-preset characters resolve the same reference while their gallery records stay disjoint and mutation-free
- [ ] 2.2 Add preset-preview resolution taking the preset key directly (no synthetic entity) and verify a before/after DB-comparison test proves previews create no character, gallery record, or stored file

## 3. NPC provenance

- [ ] 3.1 Write `npc_profile_key` provenance at the settlement-host/guild-examiner instantiation sites and the `scene_builder.py` occupant spawn path for profile-named entries, under the same transaction discipline as neighboring attributes, and verify per-path tests (host spawn, examiner spawn, blueprint occupant, import) plus rollback tests that no provenance survives a rollback
- [ ] 3.2 Enforce the tier-separation rule and verify a test where two NPCs share `npc_tier_key` and only the profile-bearing one resolves a named reference; a generated NPC with a lookalike display name resolves nothing, while one with an explicitly attached allowed reference resolves it

## 4. Monster boundary honesty

- [ ] 4.1 Ship the `monster` kind vocabulary with zero producers and verify: a production-import scan finds no construction of a monster reference; tier-keyed resolution against populated `monster/` directories yields no reference; an injected synthetic species-reference provider resolves its own content and never a sibling's (acceptance criterion 5's contingent form)
- [ ] 4.2 Record the prerequisite in code docstrings and the deployment guide pointer: species-specific official monster art activates when the separate monster species catalog lands, preserving the existing guarded seams and the shared-by-species (never by tier) rule

## 5. Verification

- [ ] 5.1 Register the new test modules in the shard manifest and run the package-adjacent tests plus the contract gate for changed modules, verifying all pass with synthetic entities and synthetic registries
