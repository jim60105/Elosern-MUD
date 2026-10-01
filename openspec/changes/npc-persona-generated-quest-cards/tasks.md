Apply on branch `feat/npc-persona-generated-quest-cards` in worktree `.worktrees/npc-persona-generated-quest-cards`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Proposal shape, schema, prompt

- [ ] 1.1 Replace `background` and the pair-tuple `persona` on `BlueprintNpcReq` with the frozen `BlueprintPersona` card (design D1), updating `to_payload`/`from_payload`; verify immutability and round-trip tests in `world/ai/tests/` for the scenario director.
- [ ] 1.2 Update the `npc_req` output schema in `world/ai/scenario_director/validators.py` per design D3 and the `scenario_director.system` text in `prompts/scenario_director.yaml`; verify schema tests (missing `speech_style`, `background` key rejected) and a prompt test asserting the seven field names, optional-leaf marking, and bounds, plus `world.prompts` loader tests green.
- [ ] 1.3 Add `SCENARIO_DIRECTOR_MAX_TOKENS = 4096` in `world/ai/profiles.py` per design D6; verify the profile-defaults test asserts all three per-layer exceptions.

## 2. Shared helper and compile chain

- [ ] 2.1 Make `world/quests/characterization.py::characterize_errors` require and validate `persona` through the card contract (design D2), removing the local persona bound, `PERSONA_PROSE_KEYS`, and their parity test; verify guardrail-level and compile-level rejection tests name the persona leaf.
- [ ] 2.2 Carry the normalized `NpcCard` through `StageNpcCharacterization`, `fields.py`, `canonical.py`, and a strict `payload.py` decoder (design D4); verify a compile→encode→decode round trip equals the card leaf for leaf and an old-shape payload raises naming quest, stage, and occupant.

## 3. Materialization

- [ ] 3.1 Revalidate in `_validate_characterization` and write through `initialize_npc_persona` with `generated_quest` provenance in `_apply_characterization` (design D5); verify in `world/quests/tests/`: spawned card and metadata, forged invalid requirement raises before any spawn with nothing persisted, idempotent re-materialization keeps an edited version-2 card.

## 4. Template content

- [ ] 4.1 Author 黑鬍's card in `world/ai/director_templates.py` (design D6), grounded in the template's scene, tier, and age; add a data-contract test that every NPC-bearing template occupant carries a valid card, registered in `tools/test_data_freeze.json`; verify the offline end-to-end template test (all profiles disabled) now asserts the occupant's card and metadata; record a short editorial review in this task's note.

## 5. Gates

- [ ] 5.1 Run `world.ai.tests` scenario-director modules, `world.quests.tests`, and `world.prompts.tests` labels, each focused, plus `uv run --locked python -m tools.observability_lint check` if any materialization log context changed; verify green.
- [ ] 5.2 Confirm the `world.ai`/`world.quests` package shard labels own every touched test module (no manifest edit) with `tests.test_evennia_test_optimization_contract`; sync the deltas into `openspec/specs/` (MODIFIED/ADDED `scenario-director`, REMOVED/ADDED `scene-builder`, MODIFIED `llm-profiles`), re-anchor annotations from the removed scene-builder requirement to the new one with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `tools.test_data_lint check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-generated-quest-cards --strict`.
