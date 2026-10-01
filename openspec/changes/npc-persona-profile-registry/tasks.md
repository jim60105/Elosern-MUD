Apply on branch `feat/npc-persona-profile-registry` in worktree `.worktrees/npc-persona-profile-registry`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Profile vocabulary and inventory

- [ ] 1.1 Create `world/lore/npc_profiles/shape.py` (`NpcVoiceLines`, `NpcProfile`), the seven empty slice modules of design D1 (each `ROWS: tuple[NpcProfile, ...] = ()` with a docstring naming its owning change), and `world/lore/npc_profiles/__init__.py` assembling `NPC_PROFILE_REGISTRY` in the fixed order with duplicate-key and contract validation naming key and slice; verify with synthetic-slice tests in `world/lore/tests/test_npc_profiles.py` (duplicate key, malformed card, over-bound voice line, read-only mapping, no lore Script created by `sync_all`).
- [ ] 1.2 Create `world/lore/npc_profiles/inventory.py` with `NPC_SOURCE_INVENTORY` rows and owners exactly as design D1 lists, and a data-contract test (first docstring line `Data-contract test: <rationale>`) deriving sources from the live registries and example files and asserting set equality; register it in `tools/test_data_freeze.json`; verify the label passes and `uv run --locked python -m tools.test_data_lint check` is clean.

## 2. Place reference

- [ ] 2.1 Add `PlaceDefinition.host_profile_key` and its validation per design D2 in `world/lore/settlements/places.py`; verify with synthetic-place tests (unresolved key, hostless with key) in `world/lore/tests/test_settlements.py`, which keeps passing together with `world.rules.tests.test_guild_config`.

## 3. Altoria dialogue split

- [ ] 3.1 Move the 16 capital tables verbatim into `altoria_lower.py`, `altoria_middle.py`, and `altoria_upper.py` per design D3, update the assembly, delete `altoria.py`, and update every import site found by `rg "world.lore.dialogue.altoria\b|dialogue import ALTORIA_ROWS"`; verify a test asserting the assembled `DIALOGUE_ROWS` key order and each table's terrace matching its place row, plus `world.rules.tests.test_dialogue` and `world.lore.tests.test_settlements` unchanged.

## 4. Gates

- [ ] 4.1 Confirm no shard edit is needed (`world.lore` package label) with `tests.test_evennia_test_optimization_contract`; sync the deltas (new `npc-profile-registry`, ADDED `settlement-place-registry`) into `openspec/specs/`, annotate with literal IDs from `uv run --locked python -m tools.spec_traceability list`; verify `tools.spec_traceability check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-profile-registry --strict`.
