Apply on branch `feat/npc-persona-companion-profiles` in worktree `.worktrees/npc-persona-companion-profiles`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Companion profiles (content)

- [ ] 1.1 Read each partner preset's card and story text (`world/lore/player_presets/data_story_cards.py`, `data_pack_cards.py`) and record per companion the established facts the NPC card must stay consistent with (name, race, age band, role, family/court relationship) in this task's note; verify all four are covered.
- [ ] 1.2 Author the four profiles in `world/lore/npc_profiles/companions.py` per design D1 (newly written cards with explicit `speech_style`, owner relationship left out of `social_connection`, offline `greeting`, `misunderstood=None`); verify `uv run --locked python -c "import world.lore.npc_profiles"` succeeds.

## 2. Declaration and validation

- [ ] 2.1 Add the required `npc_profile_key` to `StartingCompanion`, update the four declarations, and extend `world/lore/player_presets/validation.py` per design D4; verify synthetic rejection cases (unresolved key, mismatched key) in `world/lore/tests/test_player_presets.py` and the label passes.
- [ ] 2.2 Replace the relationship-length check in `_validate_preset_companion_bounds` with the composed-card check of design D2 (synthetic 64-code-point owner, leaf ≤ 600, rendered block ≤ 2,000 via the card contract); verify a synthetic over-budget profile raises naming the preset in `world/rules/tests/test_starting_companions.py`.

## 3. Builder

- [ ] 3.1 Replace `_build_persona_record` with the composed card written through `initialize_npc_persona` and `companion` provenance per design D3, keeping the delete-compensation; verify in `world/rules/tests/test_starting_companions.py`: card leaves equal the profile (except the composed `social_connection`), owner line first, metadata version 1 with provenance, partner preset persona unchanged (compare `PresetPersona.to_record()` before/after), an injected initializer failure deletes the NPC, and the existing mechanical-parity, suffix, and no-player-state cases stay green.
- [ ] 3.2 Run the activation labels that build companions (`world.rules.tests.test_character_creation` or the module that covers `activate_player_character` companions — find with `rg "starting_compan" world/rules/tests`) and `tests.test_data_independence_rules_party`; verify each passes.

## 4. Review, docs, gates

- [ ] 4.1 Review each companion card against its partner preset facts and against the other three companions side by side (the twins especially must not differ only by name); if an approved dialogue model is configured, record one free-form prompt/reply per companion, otherwise state that none was performed; record in this task's note.
- [ ] 4.2 Update `docs/development/adding-player-presets.md` Step 6 (companion declaration now names an NPC profile; the preset persona is not copied) and run `uv run --locked evennia test --settings test_settings.py --keepdb tests.test_preset_authoring_docs_contract`.
- [ ] 4.3 Add a data-contract test `world/lore/tests/test_npc_profiles_companions.py` (every declaration resolves `companion_<partner>`; each profile authors a greeting; no two companion `speech_style` or `personality` texts are equal) registered in `tools/test_data_freeze.json`; verify the label and `uv run --locked python -m tools.test_data_lint check`.
- [ ] 4.4 Confirm shard ownership (`world.lore` tests are package-owned; `world.rules.tests.test_starting_companions` is already registered) with `tests.test_evennia_test_optimization_contract`; sync the MODIFIED `starting-companions` requirements into the main spec and re-anchor/annotate tests with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-companion-profiles --strict`.
