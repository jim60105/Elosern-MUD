## 0. Prerequisites

- [ ] 0.1 Confirm `elementless-damage-effect` is merged and re-read its shipped delta (the `damage:none:<school>` token and the one-directional `SkillDef` consistency check); design.md D1 is the reconciliation point if that change's implementation revised a detail.
- [ ] 0.2 Re-inspect the current 武技 registry block, the shipped devastation/execution policy forms, the `agility_flat`/`atk_phys` modifier rows, the `fire_ignite` DoT row shape, and the `skill_owned` cast-condition evaluation, and verify every D1 mechanic exists before authoring; if one is missing, STOP and fix it in its owning surface rather than in this catalog.

## 1. Registry data

- [ ] 1.1 Author the nine 劍術 nodes exactly per design.md D1 (keys, labels, SINGLE/AREA targets, SP costs, prerequisites, coefficients, damage policies, `element=None` with `damage:none:physical`, `usable_out_of_combat=True`), and verify the registry imports with the two-parent canopy validating through the shipped lineage validator.
- [ ] 1.2 Author the 影流 route per D1: re-author `shadow_slash` in place as the root, add `phantom_dance`, `dual_blade_waltz`, `shadow_veil_execution`, `shadow_dance_finale` with `element="dark"`, and retire `dual_blade_mastery` with no alias; verify the retired key is absent from the registry and that a cast of it rejects as an unknown skill.
- [ ] 1.3 Add `CastCondition(ACTOR, {"skill_owned": "dual_wield_style"})` to `phantom_dance` and every node above it, leaving `shadow_slash` ungated (D3); verify both gate outcomes through real casts in the behavior module.
- [ ] 1.4 Verify the derived tip caps match the lore doc's cap column for all fourteen nodes and that no cap is authored anywhere, and confirm the frozen `USABLE_OUT_OF_COMBAT_FALSE` inventory still resolves to exactly `{"flee"}`.

## 2. Rulebook data

- [ ] 2.1 Add the three buff rows per D2 (`martial_hamstring`, `shadow_wound`, `sword_saint_domain`) and verify each loads and applies through the shipped buff handler with no dangling `buff_apply:`/`self_buff_apply:` target left anywhere in the registry.
- [ ] 2.2 Add the two `combat_modifiers.yaml` rules (`martial_hamstring_agility_penalty` → `{agility_flat: -5}`, `sword_saint_domain_atk_phys_bonus` → `{atk_phys: 12}`) and verify each resolves only while its mount is live.
- [ ] 2.3 Add the five `status_display.yaml` census rows (three buff keys, two rule IDs) and verify the fail-closed coverage check passes over both vocabularies.

## 3. Shipped-content follow-through

- [ ] 3.1 Move 悠花's `dual_blade_mastery` entry to `dual_blade_waltz` in `world/lore/player_presets.py` and verify the preset validation passes at load.
- [ ] 3.2 Delete `test_dual_blade_mastery_is_a_higher_tier_sibling` with its retired requirement and update the existing category census key set in `world/skills/tests/test_skill_registry.py` to the authored 武技 keys; add no new data-contract test of any shape (no key-set, node-table, cost, cap, tier or lineage-edge echo) and leave `tools/test_data_freeze.json` untouched unless retiring that test leaves a stale entry.

## 4. Behavioral evidence (synthetic only)

- [ ] 4.1 Run a disposable offline scenario before writing permanent tests, exercising each distinct D1 composition through real casts: each coefficient rung and its stamina payment; the two- and three-judgment rungs under every hit/miss combination and across a lethal roll; execution against high defense; devastation against full HP; each rider's mount, its effect on its real consumer, and its expiry; the wound rider's kill credit; the stance gate both ways; both canopies' two-parent gating.
- [ ] 4.2 Write the synthetic behavior module `world/skills/tests/test_martial_arts_behavior.py` mirroring the ADDED requirement's scenarios, naming no shipped key, label, cost or coefficient anywhere; confirm no `.github/evennia-shards.json` edit is needed (the `quests-skills-art-ai-lore` shard's `world.skills` package label already resolves it) and verify with `tests.test_evennia_test_optimization_contract`.

## 5. Focused verification

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests.test_martial_arts_behavior world.skills.tests.test_skill_registry world.skills.tests.test_cost_tiers world.rules.tests.test_skill_lineage world.rules.tests.test_buffs world.rules.tests.test_status_display world.rules.tests.test_combat_modifiers world.lore.tests.test_player_presets tests.test_evennia_test_optimization_contract
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate martial-arts-catalog --strict
```

- [ ] 5.1 Run the focused labels and gates above and record the results. Pass `MUD_TEST_SETTINGS=1` through the tool environment, never as an inline shell prefix. No full suite, no browser run, no aggregate-coverage run.
- [ ] 5.2 Annotate the new behavior tests with the canonical requirement ID from `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-spec sync; the retired `skill-registry::dual-blade-mastery-exists-as-a-higher-tier-sibling-to-dual-wield-style` entry leaves the ledger at that sync. No apply, archive, sync or merge happens in the proposal turn.
