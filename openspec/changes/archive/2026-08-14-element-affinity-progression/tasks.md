## 1. Progression rule changes

- [x] 1.1 Add `affinity_element_multiplier: 1.1` and `non_affinity_element_multiplier: 0.9` to `world/rules/rulebook/progression.yaml`; validate both as finite and non-negative at module load (a `nan`/negative/infinite yaml value fails at import)
- [x] 1.2 Implement `element_affinity_multiplier(entity, element)` in `world/rules/progression.py` (pure read of `entity.db.affinity_elements`, 1.1/0.9/1.0, `ValueError` on unknown element, reads constants from yaml)
- [x] 1.3 Amend `can_cast_spell_tier` to validate the element key against `ELEMENT_REGISTRY` first (raise `ValueError` before the mastery check), then apply the mastery override, then compare `floor(magic_level × element_affinity_multiplier)` against `MAGIC_TIER_THRESHOLDS`
- [x] 1.4 Wrap the whole gate (not only `spell_tier_for`) in `monster_behaviour._gate_allows`'s existing `ValueError → False` handler
- [x] 1.5 Add progression tests: neutral default 1.0, favored 1.1, non-favored 0.9, unknown element fail-closed (even with a fabricated `"<unknown>_mastery"`), tier unlock edges (fire-affinity 29 → 大師, non-affinity 34/35 → 大師, human 83 → 主宰 fire but never wind), mastery override still wins, and a monster-policy test that a malformed spell/element denies instead of raising

## 2. Player preset affinity

- [x] 2.1 Add `affinity_elements: tuple[str, ...] = ()` field to `PlayerPreset` in `world/lore/player_presets.py`
- [x] 2.2 Populate `affinity_elements` for the shipped human/beastfolk presets from their lore (violet `fire,wind`, yuna is an elf so `()` — subrace seeds, elosia `()` — subrace seeds, etc.); elf presets MUST stay empty
- [x] 2.3 Add registry-load validation rejecting unknown/duplicate affinity element keys AND any non-empty set on an elf preset, with tests

## 3. Custom creation race-bounded affinity

- [x] 3.1 Add `affinity_elements` to `CharacterCreationRequest` and thread it through `preflight_character_creation`
- [x] 3.2 Implement the single race-bound mapping `max_affinity_elements(race_key)` (`human` 2, `beastfolk` 1, `elf` 0) in `world/rules` and validate against it (elf rejects any player-supplied set)
- [x] 3.3 Seed elf affinity from `SUBRACE_REGISTRY[subrace].affinity_elements` (validating the seed keys exist and are unique) and write the resolved set to `entity.db.affinity_elements` inside the atomic activation transaction (preset mode uses the preset's declared set; elf presets always seed from subrace)
- [x] 3.4 Persist `affinity_elements` in the custom creation wizard draft (save/validate/clear atomically) and expose it via the wizard draft read path
- [x] 3.5 Add Telnet wizard custom-mode prompt for the affinity choice (human/beastfolk only, race-bounded) and update `commands/character_creation.py`
- [x] 3.6 Update `docs/game/commands.md` and `docs/game/command-reference.md` for the new custom-mode affinity prompt and keep `tests/test_command_docs.py` green
- [x] 3.7 Add creation tests: human two accepted / three rejected, beastfolk one accepted / two rejected, elf supplied set rejected, elf subrace seed (fionnen → `light`, eolas → all eight, each favored ×1.1), unknown/duplicate rejected, preset affinity persisted (human) and elf preset seeds from subrace, activation rollback restores affinity

## 4. Import affinity field

- [x] 4.1 Add optional `affinity_elements` to `CHARACTER_SCHEMA_V1` in `world/imports/schema.py` (enum of eight elements, `uniqueItems`, `maxItems: 8`, description)
- [x] 4.2 Add semantic validation in `world/imports/validate.py`: registry membership, duplicates, race-aware counts (human ≤ 2, beastfolk ≤ 1, elf-supplied set rejected)
- [x] 4.3 Persist `affinity_elements` in `world/imports/loader.py`; for an elf record seed it from the record's subrace (validated) so no elf contradicting its subrace persists
- [x] 4.4 Update an import example card to carry `affinity_elements` and add import tests: schema structural (unknown/duplicate/oversize), semantic race counts, elf rejection, and loader persistence into `entity.db.affinity_elements`

## 5. WebClient creation surface

- [x] 5.1 Extend the `custom` view (wizard `CustomFormView`) with an `affinity` descriptor (per-race `maximum` derived from `max_affinity_elements` — 2/1/0 — and eight element choices from `ELEMENT_REGISTRY`)
- [x] 5.2 Extend `web/webclient/presentation/creation.py`: validate/serialize the `affinity` descriptor and the custom draft `affinity_elements`, deriving bounds from `max_affinity_elements`
- [x] 5.3 Extend `creation.custom` action adapter (`web/webclient/actions/creation_actions.py`) to accept optional `affinity_elements` and reject unknown/over-bound/elf sets before the deterministic service
- [x] 5.4 Mirror the affinity bounds and payload in the client validator (`web/static/webclient/js/elosern/protocol.js`) and the creation menu (`creation_menu.js`) with the dual-direction parity test kept green
- [x] 5.5 Add presenter/action tests asserting the descriptor `maximum` equals `max_affinity_elements` for each race, and payload acceptance/rejection

## 6. Spec, design-doc, and validation sweep

- [x] 6.1 Amend `docs/superpowers/specs/2026-08-12-skill-system-redesign-design.md` §4.2 (D4) with an explicit amendment note for the element-effective gate and the elf subrace authority
- [x] 6.2 Run `openspec validate element-affinity-progression --strict`, the affected Evennia package tests (`world.rules world.imports commands web.webclient`), the Node JS tests, and `python -m tools.spec_traceability check`
- [x] 6.3 Run `git diff --check` and `python -m compileall -q world typeclasses commands server web`
