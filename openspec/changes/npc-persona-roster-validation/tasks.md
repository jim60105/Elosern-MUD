Apply on branch `feat/npc-persona-roster-validation` in worktree `.worktrees/npc-persona-roster-validation`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Validation module

- [x] 1.1 Implement `derive_shipped_sources()` and `validate_npc_roster()` in `world/rules/npc_roster_validation.py` per design D1/D2 (all violations collected), resolving `starting_companion` sources through the shared partner-preset derivation of `npc-persona-companion-profiles`; verify `world/rules/tests/test_npc_roster_validation.py` with synthetic registries: missing profile, invalid template card, table answered by zero/two hosts, missing misunderstanding reply, companion partner preset with empty `speech_style` or `greeting`, orphan profile, inventory mismatch both directions, and multiple violations in one failure.
- [x] 1.2 Add a data-contract test that the shipped roster validates (first docstring line `Data-contract test: …`, registered in `tools/test_data_freeze.json`) and switch the profile-registry inventory test to `derive_shipped_sources()`; verify both labels and `uv run --locked python -m tools.test_data_lint check`.

## 2. Boot step

- [x] 2.1 Add the fail-loud `npc_persona_roster_validation` step to `at_server_start` and `STARTUP_STEP_ORDER` per design D3; verify the startup-order guard tests in `server/conf/tests/` (update the expected order) and a test that a failing validation aborts before `sync_all`.

## 3. Review and docs

- [ ] 3.1 Write `docs/lore/npc-persona-roster-review.md` per design D4 from the slices' recorded reviews plus a fresh cross-slice same-profession comparison; state model-review status honestly.
- [ ] 3.2 Update the authoring-flow sections of `docs/development/adding-npcs.md` (creation paths now initialize cards; profiles and slices; references; inventory and boot validation; voice lines; the in-game editor and its no-regeneration rule) in Traditional Chinese; run any docs contract test that covers the file.

## 4. Gates

- [ ] 4.1 Register `world.rules.tests.test_npc_roster_validation` in exactly one rules shard and verify `tests.test_evennia_test_optimization_contract`; sync the ADDED requirement into `openspec/specs/npc-profile-registry/spec.md` and annotate with the literal ID from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `uv run --locked python -m tools.observability_lint check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-roster-validation --strict`.
