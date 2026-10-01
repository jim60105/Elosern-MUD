Apply on branch `feat/npc-persona-host-examiner-producers` in worktree `.worktrees/npc-persona-host-examiner-producers`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Mandatory host profile

- [x] 1.1 Add `host_profile_key` to `HOST_IDENTITY_FIELDS` in `world/lore/settlements/places.py` per design D1 and update every synthetic hosted `PlaceDefinition` in tests (`rg "PlaceDefinition\(" world web commands tests --glob "*tests*"`) to name a synthetic profile from a file-local or test-data-kit fixture; verify `world.lore.tests.test_settlements` (new missing-profile rejection case) and `world.rules.tests.test_guild_config` pass.

## 2. Service hosts

- [x] 2.1 Carry `profile_key` on the derived roster row in `world/rules/guild_config/_hosts.py`, failing closed on an unresolved profile, and initialize only in `_sync_service_host`'s creation branch per design D2; extend the creation event context with `profile`; verify in `world/rules/tests/test_guild_economy_sync/`: created host carries the card at version 1 with provenance, re-sync after a synthetic profile edit leaves an edited version-2 card unchanged, a reused host without metadata gets no write, and an injected initializer failure leaves no host.
- [x] 2.2 Run `world.rules.tests.test_guild_economy_sync`, `world.rules.tests.test_guild_economy_scenarios`, `world.rules.tests.test_guild_economy_guards`, and `world.maps.tests.test_service_interiors`, each in its own command; verify green.

## 3. Exam opponents

- [ ] 3.1 Initialize the opponent's card from `examiner_profile_key` inside `_spawn_opponent`'s compensation per design D3 and extend `guild_exam_opponent_created` with `profile`; verify in `world/rules/tests/test_guild_exams.py`: card and provenance at spawn, injected failure rolls back opponent/record/session, a second spawn after editing the first carries the unedited card.

## 4. Gates

- [ ] 4.1 Update the two event rows in the observability catalog (§4.2) and run `uv run --locked python -m tools.observability_lint check` in the same batch as the focused labels; `tools/observability_freeze.json` unchanged.
- [ ] 4.2 Confirm shard ownership with `tests.test_evennia_test_optimization_contract` (register any new `world/rules/tests` module in exactly one rules shard; existing modules are already owned); sync the three ADDED requirements into the main specs and annotate the tests with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `uv run --locked python -m tools.test_data_lint check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-host-examiner-producers --strict`.
