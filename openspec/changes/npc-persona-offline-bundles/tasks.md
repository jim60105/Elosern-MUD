Apply on branch `feat/npc-persona-offline-bundles` in worktree `.worktrees/npc-persona-offline-bundles`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Vocabulary and selector

- [ ] 1.1 Create `world/lore/npc_profiles/bundles.py` with `NpcPersonaBundle`, `NpcBundlePool`, import-time validation (design D1/D2), `offline_pool_for`, and `select_offline_bundle` (design D3), importing only `world/lore`; verify with `unittest.TestCase` cases in `world/lore/tests/test_npc_persona_bundles.py` over synthetic pools: malformed bundle, wrong-race bundle, one-bundle pool, duplicate speech style, tier vs race resolution, determinism across two calls and across a `subprocess` interpreter, distinct seeds reaching both bundles of a two-bundle pool with their specific `speech_style` text, and no state write (pure function, no Evennia import).

## 2. Authored pools (content)

- [ ] 2.1 Author two bundles for each of the ten tier pools and two for `beastfolk_generic` per design D4, reading `world/lore/npc_tiers.py`, `world/lore/races.py`, and `docs/lore/overview.md` first; verify the registry imports cleanly (the budget and distinctness rules run at import).
- [ ] 2.2 Review each pool's two bundles side by side and the combat-role pools for humanity rather than stat blocks; record the review in this task's note, and state whether any model-output review was performed.

## 3. Gates

- [ ] 3.1 Add a data-contract test over the shipped pools (every tier and race resolves; each pool ≥ 2; every bundle has empty `identity.hidden` and `social_connection`; no bundle text contains a personal name, a numeric age, or a sex-specific pronoun from a small deny list, because the selector cannot check sex or age eligibility) registered in `tools/test_data_freeze.json`; verify the label and `uv run --locked python -m tools.test_data_lint check`.
- [ ] 3.2 Confirm the new `world/lore/tests` modules are owned by the `world.lore` package shard label (no manifest edit) with `tests.test_evennia_test_optimization_contract`; leave the new capability's requirements unannotated until archive sync unless already synced, then annotate with literal IDs from `uv run --locked python -m tools.spec_traceability list`; run `tools.spec_traceability check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-offline-bundles --strict`.
