## Why

The dark skill tree (`docs/lore/skill-trees/dark.md`, 13 nodes, updated in b69d47a with the erosion-leech and self-recovery clauses) is the node-data authority, but the registry still ships the dev-era 2026-08-12 ten-row dark set — no prerequisites, no coefficients, `shadow_torment`-era bindings, a `fear` marker that never actually locks actions, and erosion DoTs whose HP simply evaporates. Every behavior primitive this wave needed is now specified by the sibling changes: the erosion-tick leech clause (`dark-erosion-leech`) and the missing-fraction self-heal basis (`dark-self-recovery-missing-fraction`). This change is the final **data-only** integration: it replaces the old rows wholesale, authors the 13-node tree as registry + rulebook data over that vocabulary, re-homes the dev-era dark buff rows to the §3.3 tier bands, and retires the duplicated dark catalog-contract test exactly as the archived light and water waves did. Per the ratified NON-GOAL this change adds no data-catalog tests.

## What Changes

- **Batch declaration.** This change lands LAST; both sibling dark changes are listed in `## Batch` below with machine-readable `depends-on:` lines and the code-conflict notes the supervisor queues from.
- Replace the ten dev-era dark registry rows with the 13-node tree verbatim from the node table (keys, labels, targets, MP costs, prerequisites via `SkillPrerequisite(node, N)`, coefficients per §3.2, 處決級/毀滅級 tiers, caps via the existing reverse-edge derivation — no stored cap field; `abyssal_apotheosis` is the two-parent capstone). Key census: ten re-authored (eight keys unchanged in name, `shadow_torment`→`shadow_torture` was already renamed in the shipped rows; `underworld_judgment` already matches lore), plus THREE new keys (`curse_spread`, `shadow_blight`, `abyssal_apotheosis`). Re-homed keys keep no aliases.
- Author every node's effect composition over the wave's vocabulary: `damage:dark:magic` coefficients, `DamagePolicy(bypass_defense=True)` execution rung and `max_hp_fraction=0.10` devastation rung (both shipped), `buff_apply:` the §3.3 debuff rows / erosion rows / `fear`, and `self_heal:missing_fraction:0.1|0.15` on the two recovery nodes.
- Re-home the dark rulebook rows to the tree's authored numbers (data-only, same surfaces): `dark_atk_down`→replaced by the 衰弱術 row (−3/15 s), `dark_curse` re-homed (−5×3 stats/20 s), new 詛咒擴散 row (−8 atk/def/30 s), new 深淵神格 debuff row (−25 atk/def/90 s); `dark_corrosion` re-homed to the −12/10 s erosion tier and one new −18/10 s sibling, both 300 s duration and both carrying `caster_share: 1.0` (the shipped dark-erosion-leech clause); `fear` duration re-homed 60→40 s per the node/§3.3 band and one `combat_modifiers.yaml` lock row (`actions_per_turn: 0`) so 恐懼 = 心理性靜止 becomes behavior — an independent buffs key from ice's physical-still keys per the §4.4 恐懼留暗 ruling (two keys, narrative distinction author-side).
- Retire the dark catalog echo tests in-file: `DARK_SPELL_CATALOG` and its test class in `world/skills/tests/test_spell_catalogs.py`, the dark rows in `test_cost_tiers.py`'s tier table; the canonical ID `skill-registry::skill-registry-contains-the-full-暗-element-spell-set` retires with its requirement (per-file freeze-list entries adjusted only as `tools.test_data_lint check` output decides).
- Docs/traceability integration owned here: shard-manifest final state (`.github/evennia-shards.json` — this change owns the wave's last manifest edit); `dark.md` stays the authority and is untouched; `magic-system.md` §3's dark row checked for contradiction only (expected: none — it states the 讓敵人先弱下去 + 掠取 identity this tree implements); `tests/test_command_docs.py` untouched (no command-surface change).

This design.md additionally carries the wave-wide **interface-ownership matrix, batch order and shared verification contract** (light/water pattern) for the whole dark wave.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `skill-registry`: the duplicated ten-row 暗-element data-contract requirement is REMOVED and replaced by one behavioral requirement — dark spell progression composes executable curse/erosion behavior (stat-debuff ladders, action-locking fear, erosion ticks whose full loss is leeched to the origin caster, execution and devastation rungs, missing-fraction self-recovery, two-parent capstone) through the shared mechanics, with the old set deleted without alias.

## Impact

`world/skills/registry.py` (dark set block); `world/rules/rulebook/buffs.yaml` (debuff/erosion/fear rows) and `world/rules/rulebook/combat_modifiers.yaml` (fear lock row); `world/skills/tests/test_spell_catalogs.py`, `world/rules/tests/test_cost_tiers.py` (echo-test retirement); new synthetic behavior module → `.github/evennia-shards.json`; traceability ledger hygiene at the separately authorized main-sync. `openspec list --json` returned an empty change set at authoring time — no serialization gate against active changes; the dark wave's internal ordering is declared below. One engineer-day.

## Batch

- depends-on: dark-erosion-leech
  (code conflicts: `world/rules/rulebook/buffs.yaml` — this change authors the erosion rows carrying `caster_share` over that change's shipped clause; `.github/evennia-shards.json`)
- depends-on: dark-self-recovery-missing-fraction
  (code conflicts: `world/skills/registry.py` dark block only data-wise — the grammar/policy surface is frozen by that change; this change only authors data)

Planning artifacts only this turn; no apply/archive/sync/merge.
