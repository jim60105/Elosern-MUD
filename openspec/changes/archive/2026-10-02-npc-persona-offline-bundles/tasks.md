Apply on branch `feat/npc-persona-offline-bundles` in worktree `.worktrees/npc-persona-offline-bundles`. Run every Evennia label with `MUD_TEST_SETTINGS=1` passed through the Bash tool's `env` input, one focused label per command, output captured to a scratch file.

## 1. Vocabulary and selector

- [x] 1.1 Create `world/lore/npc_profiles/bundles.py` with `NpcPersonaBundle`, `NpcBundlePool`, import-time validation (design D1/D2), `offline_pool_for`, and `select_offline_bundle` (design D3), importing only `world/lore`; verify with `unittest.TestCase` cases in `world/lore/tests/test_npc_persona_bundles.py` over synthetic pools: malformed bundle, wrong-race bundle, one-bundle pool, duplicate speech style, tier vs race resolution, determinism across two calls and across a `subprocess` interpreter, distinct seeds reaching both bundles of a two-bundle pool with their specific `speech_style` text, and no state write (pure function, no Evennia import).

## 2. Authored pools (content)

- [x] 2.1 Author two bundles for each of the ten tier pools and two for `beastfolk_generic` per design D4, reading `world/lore/npc_tiers.py`, `world/lore/races.py`, and `docs/lore/overview.md` first; verify the registry imports cleanly (the budget and distinctness rules run at import).
- [x] 2.2 Review each pool's two bundles side by side and the combat-role pools for humanity rather than stat blocks; record the review in this task's note, and state whether any model-output review was performed.
  Note on 2.2 review:
  - Reviewed all 11 pools side by side (22 cards total).
  - Combat roles (`guard`, `adventurer`, `bandit`, `knight`): Each possesses distinct human motivations, personal backgrounds, and vulnerabilities rather than stat blocks or weapon stereotypes:
    - `guard`: veteran gatekeeper (values orderly duty and quiet empathy for tired commoners) vs alert watchman (eager curiosity, civic responsibility, and patrol vigilance).
    - `adventurer`: seasoned tracker (wilderness respect, cautious risk aversion, and mentoring) vs aspirant swordsman (discipline, swordplay dedication, and strict adherence to party contracts).
    - `bandit`: highway ambusher (wary desperation, survival calculation, fear of regular troops) vs disillusioned outlaw (bitter regret, moral qualms, trapped in banditry by hardship).
    - `knight`: cavalry banneret (chivalric honor, oath-keeping, battlefield forthrightness) vs border ranger (stoic endurance, frostbitten border grit, pragmatic defense prioritization).
  - Non-combat roles (`civilian`, `merchant`, `mage`, `noble`, `priest`, `elven_civilian`, `beastfolk_generic`):
    - Clear divergence in outlook, speech mannerisms, habits, and trade experience across each pair.
    - All cards strictly adhere to sex/age-agnostic phrasing (no personal names, no numeric ages, zero third-person pronouns).
  - Model-output review: Model generated the prose directly adhering to authoring guidelines without external LLM API output ingestion.

## 3. Gates

- [x] 3.1 Add a data-contract test over the shipped pools (every tier and race resolves; each pool ≥ 2; every bundle has empty `identity.hidden` and `social_connection`; no bundle text contains a personal name, a numeric age, or a sex-specific pronoun from a small deny list, because the selector cannot check sex or age eligibility) registered in `tools/test_data_freeze.json`; verify the label and `uv run --locked python -m tools.test_data_lint check`.
- [x] 3.2 Confirm the new `world/lore/tests` modules are owned by the `world.lore` package shard label (no manifest edit) with `tests.test_evennia_test_optimization_contract`; leave the new capability's requirements unannotated until archive sync unless already synced, then annotate with literal IDs from `uv run --locked python -m tools.spec_traceability list`; run `tools.spec_traceability check`, `tools.contract_gate`, `git diff --check`, and `openspec validate npc-persona-offline-bundles --strict`.
