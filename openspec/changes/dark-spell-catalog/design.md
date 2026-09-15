## Context

Final data-only integration of the dark wave: the 13-node tree of `docs/lore/skill-trees/dark.md` authored into `world/skills/registry.py` + the dark rulebook rows over the vocabulary the two behavior changes ship. This design.md is the wave's single integration contract (light/water pattern): interface-ownership matrix, batch order, shared verification contract, and the per-node coverage table below govern ALL dark changes; the behavior changes defer to it on interface names and land first. Pre-audited engine facts and user-ratified givens (recorded where they bind):

- **NON-GOAL — game-data contracts.** No dark catalog/data-contract tests: no key-set equality, no row mirroring, no MP-cost/cap/tier assertions, no echo of the dark.md table. All verification is BEHAVIOR contracts on synthetic skills/state transitions (light/water convention).
- **No second rules engine / no dark-key branches in generic code.** Everything this wave adds is declarative vocabulary on existing surfaces: the `caster_share` rate clause (dark-erosion-leech), the `self_heal:missing_fraction` magnitude mode (dark-self-recovery-missing-fraction), `buffs.yaml` rows, `combat_modifiers.yaml` rows, registry data.
- **Zero users: no migrations, no aliases, no back-compat.** The dev-era dark rows are wholesale replaced; re-homed buff keys carry the new numbers with no alias (the old water/element echo-test convention applies: behavior tests replace echo tests where they exist).
- **Serialization:** `openspec list --json` returned an empty change set at authoring time — light, water and the taxonomy consolidation are FULLY ARCHIVED. The two sibling dark changes are queued from this file's Batch section; conflict matrix: `dark-erosion-leech` ∥ `dark-self-recovery-missing-fraction` are file-disjoint (buffs engine+tests vs effects/combat/registry-validation+tests) and may run concurrently; `dark-spell-catalog` is strictly after both (authored data over their shipped grammar).
- **Node-data authority:** MP costs and coefficients already sit in the §3.1/§3.2 bands by construction; do NOT rebalance — author dark.md's columns as-is (given). Cap semantics: reverse-edge derived, leaf 10 (`proficiency_cap`, already implemented; no stored cap field). Lv.N thresholds are `SkillPrerequisite(node, N)` data rows only.

## Goals / Non-Goals

**Goals:** Registry data for all 13 nodes; every lore clause delivered by some primitive the wave owns (coverage table); old rows gone without trace; echo tests retired the water way; the §4.4 恐懼留暗 ruling realized as two independent state keys; wave-wide integration contract stated once.

**Non-Goals:** No new behavior code in this change (anything missing is a defect in the behavior changes, fixed there, not bolted on here); no main-spec sync, no freeze-list pre-editing, no command-surface work; no data-contract tests; `dark.md` and `tests/test_command_docs.py` untouched; `magic-system.md` §3 touched only if a real contradiction surfaces (none found at authoring — the section's dark identity IS this tree); the 2026-08-12 design doc stays frozen history.

## Decisions

### D1 — Node coverage table (all 13 nodes × delivering primitive)

Stat-axis mapping (lore → engine): 攻擊力→`atk_phys`, 防禦→`defense`, 敏捷→`agility`. The dev-era rows' `magic_power` axes retire with them — dark.md's columns never mention 魔力 (clean cut; node data is authority). Buff keys below are the authored homes; `dark_curse`/`dark_corrosion` are re-homes (same key, new numbers), the rest are new; `dark_atk_down` is deleted.

| Node (key) | 節點數據 (dark.md) | Delivered by |
|---|---|---|
| 衰弱術 `weaken` | 學徒 11MP 單體；攻擊 −3，15 s；cap 3 | `buff_apply:dark_weaken` (new bounds row atk −3 / 15 s); root |
| 詛咒術 `curse` | 術師 26MP 單體；攻/防/敏 −5，20 s | `buff_apply:dark_curse` (re-homed bounds rows −5×3 / 20 s); prereq (weaken, 3) |
| 詛咒擴散 `curse_spread` | 大師 45MP 範圍；攻/防 −8，30 s；cap 5 | `buff_apply:dark_spread` (new bounds rows atk −8, defense −8 / 30 s); prereq (curse, 3) |
| 黑暗支配 `dark_dominion` | 賢者 72MP 範圍；恐懼無法行動 40 s；cap 10（樹冠） | `buff_apply:fear` (existing shared key; duration re-homed 60→40 per node/§3.3 band) + new `fear_locks_actions` row `{actions_per_turn: 0}` — fear stays an INDEPENDENT buffs key from ice's physical-still keys (§4.4 恐懼留暗: two keys, narrative source distinction author-side); prereq (curse_spread, 5) |
| 暗影之刑 `shadow_torture` | 大師 41MP 單體；2.0 + 侵蝕 −12/10 s 300 s，流失全額轉入施法者；cap 8 | damage component coefficient 2.0 + `buff_apply:dark_corrosion` (re-homed: delta −12, duration 300, `caster_share: 1.0` — dark-erosion-leech's clause); prereq (curse, 3) |
| 暗影侵蝕 `shadow_blight` | 賢者 80MP 單體；2.8 + 侵蝕 −18/10 s 300 s，流失全額轉入施法者；cap 8 | coefficient 2.8 + `buff_apply:dark_corrosion_deep` (new −18/10 s 300 s `caster_share: 1.0`); prereq (shadow_torture, 8) |
| 冥界審判 `underworld_judgment` | 主宰 135MP 單體；4.0 處決級（無視防禦）；cap 10 | coefficient 4.0 + `DamagePolicy(bypass_defense=True, predicate=())` (unconditional execution bypass shipped by the water wave); prereq (shadow_blight, 8) |
| 暗影箭 `shadow_bolt` | 學徒 14MP 單體；1.0；cap 3 | `damage:dark:magic` coefficient 1.0; root |
| 闇裂術 `dark_burst` | 術師 29MP 範圍；1.0；cap 3 | coefficient 1.0 |
| 闇蝕領域 `dark_corrosion_domain` | 大師 47MP 範圍；1.4 + 侵蝕 −12/10 s 300 s，範圍內每個受蝕者的流失量都全額轉入施法者；cap 5 | coefficient 1.4 + `buff_apply:dark_corrosion` — the per-victim origin credit is automatic under the leech contract (each victim's instance stores its own grant-time source; the area cast's per-target attribution is the shipped `_handle_buff_apply` behavior); prereq (dark_burst, 3) |
| 深淵吞噬 `abyss_devour` | 賢者 85MP 單體；2.8 處決級；cap 8 | coefficient 2.8 + unconditional `bypass_defense` |
| 虛空湮滅 `void_annihilation` | 主宰 155MP 範圍；2.8 毀滅級，命中回復施法者已損 HP 10%；cap 10 | coefficient 2.8 + `DamagePolicy(max_hp_fraction=0.10)` (existing devastation rider) + `self_heal:missing_fraction:0.1` (dark-self-recovery-missing-fraction's grammar); prereq (abyss_devour, 8) |
| 深淵神格 `abyssal_apotheosis` | 神格 225MP 範圍；3.8 毀滅級 + 全體攻/防 −25 90 s + 命中回復已損 HP 15%；cap 10 | three independent effect components per the node's own design note: coefficient 3.8 + devastation policy + `buff_apply:dark_apotheosis` (new bounds rows atk/defense −25 / 90 s) + `self_heal:missing_fraction:0.15`; erosion leech rides only through the OTHER nodes' ticks — this node prices no erosion (掠取與自癒是兩回事 note: never double-priced); two prerequisites (underworld_judgment 10 + void_annihilation 10) ride the existing n-ary DAG + capstone derivation |

cap column → existing reverse-edge tip-cap derivation (leaf 10); this change authors no cap field. 位階 labels are display grouping via the existing tier derivation from MP cost; costs authored as-is per the given (dark_dominion's 72 sits in the 賢者 column dark.md's table states; the cost-derived tier grouping tolerates the rung as light/water showed — implementation verifies the derivation, never rebalances the cost).

### D2 — Wholesale replacement, key census

Old→new: all ten dev-era registry keys (`shadow_bolt`, `weaken`, `curse`, `dark_burst`, `dark_corrosion_domain`, `shadow_torture`, `abyss_devour`, `dark_dominion`, `void_annihilation`, `underworld_judgment`) re-authored under tree data (coefficients, prereqs, new effect bindings); three keys ADDED (`curse_spread`, `shadow_blight`, `abyssal_apotheosis`). Buff keys: `dark_atk_down` DELETED (superseded by `dark_weaken`'s authored −3/15 s row), `dark_curse` re-homed (−10×3 → −5×3, 60→20 s), `dark_corrosion` re-homed (−5 → −12/10 s, `caster_share: 1.0`), `fear` duration re-homed 60→40 s (shared key — the fearless_brooch immunity row and every existing behavior ride the key unchanged; only its duration moves, and the new lock row makes it action-blocking per the node text). Nothing aliases. Grep census at implementation must show: registry block, the two echo-test files (retired here), `test_buffs.py` dev-era row references adjusted to the re-homed numbers (behavior assertions preserved, no row mirroring added), and the frozen 2026-08-12 design doc (NOT edited).

### D3 — Wave interface-ownership matrix (integration contract for all dark changes)

| Interface | First owner | Consumers |
|---|---|---|
| `caster_share` rate clause (validation + tick-site origin credit, extinguishment) | dark-erosion-leech | catalog (`dark_corrosion`/`dark_corrosion_deep` rows), any future DoT-family element |
| `SelfHealEffect` missing-fraction basis + `self_heal:missing_fraction:<f>` grammar + handler leg | dark-self-recovery-missing-fraction | catalog (`void_annihilation`, `abyssal_apotheosis` data) |
| 13-node registry block + dark buff/modifier rows + echo-test retirement + shard manifest final state | dark-spell-catalog | — |
| (inherited, unchanged) `gauge_transfer` family, execution bypass, devastation rider, reverse-edge caps, grant-time source attribution, `fear` key + `buff_active` condition engine | archived light/water waves | this wave's data only |

Shared-file schedule: `dark-erosion-leech` owns `world/rules/buffs.py` (engine) + its test module + shard row; `dark-self-recovery-missing-fraction` owns `world/skills/effects.py` + `world/rules/combat.py` + existing test modules; the catalog change edits only the registry dark block, `buffs.yaml`/`combat_modifiers.yaml` dark rows, the two echo-test files, and the shard manifest's last edits. No pair of changes touches the same file concurrently except buffs.yaml (leech ships zero rows; catalog owns every row) — conflict matrix is empty by ownership.

### D4 — Batch order

1. `dark-erosion-leech` and `dark-self-recovery-missing-fraction` — independent, any order / concurrent.
2. `dark-spell-catalog` — after BOTH merge (data over their shipped grammar).

### D5 — Verification contract, shared by the whole wave

1. **Every test is behavior on synthetic state** — synthetic skills/buffs/entities, real settlement through the action/buff/clock/combat stages; tests MUST fail on plausible bugs (credit on requested-not-actual loss, double dispatch, target-gap basis read, clamp escape, revival, alias survival, audience misroute, half-applied rollback, prereq gate leak). Source-text, data-echo and row-mirror assertions are prohibited, including in this catalog change.
2. **The catalog change's own proof** is a disposable offline engine scenario exercising each distinct D1 composition through real casts (debuff ladder stat reads at authored values/durations; fear lock skipping actions and its independence from ice keys — a frozen entity and a feared entity are separate keys with separate narratives; erosion tick → full HP transfer to the origin caster incl. the area cast's per-victim origins; execution bypass vs high defense; devastation max-HP rider; missing-fraction recovery at authored 10 %/15 %; leech + self-heal composing on one settlement without double-pricing; branch/convergence gates and the two-parent capstone through the lineage engine), plus synthetic behavior tests for settlement paths not already pinned by the sibling suites.
3. **Focused invocation** (each change's tasks.md): `uv run --locked evennia test --settings test_settings.py --keepdb <modules>` with `MUD_TEST_SETTINGS=1` via the tool env, NEVER a shell prefix; plus `tools.observability_lint check`, `tools.test_data_lint check`, `tools.spec_traceability check`, `openspec validate <change> --strict`. No full local suite / browser / aggregate-coverage run; no command above ten minutes.
4. **Traceability:** canonical IDs via `uv run --locked python -m tools.spec_traceability list`; `@covers_requirement` literal IDs only; the retired 暗-element ID leaves the ledger with its requirement at the separately authorized main-sync.
5. **Shards:** new non-browser test modules join exactly one shard in `.github/evennia-shards.json`; this change owns the wave's last manifest edit; the ownership-contract test verifies.

### D6 — Requirement retirement (water-spell-catalog's exact pattern)

`skill-registry::skill-registry-contains-the-full-暗-element-spell-set` REMOVED with reason (duplicated ten-row data contract superseded by a 13-node tree + the ratified no-data-contract-tests given) and migration (delete `DARK_SPELL_CATALOG` + its test class, the tier-table dark rows, and the obsolete traceability/freeze entries during the separately authorized main-sync; replaced by the ADDED behavioral requirement in this change's delta). The other elements' echo requirements stay untouched — dark's retirement is scoped to dark.

## Risks / Trade-offs

- **`fear` duration re-home is a shared-key change** (60→40 s): every existing `fear` consumer asserts mechanics (presence, immunity, cleanse), none pins the duration (verified: `test_buffs.py` refresh/stacks tests, `test_combat_modifiers.py` value reads, item tests — none assert 60). If implementation finds a duration pin, that test is a data echo and retires per the verification contract.
- **Fear gaining an action lock** strengthens an existing shared key: the `fear_agility_and_accuracy_penalty` row stays (the node's 無法行動 is the lock; the agility/accuracy penalty is the shipped identity of the same key and stays compatible), and fearless_brooch immunity now also immunizes the lock — intended (免疫恐懼).
- **Execution-tier bypass + devastation already exist** (water change 2 / light precedent) — if either fails fit at implementation it is a defect fixed in the shipped primitive's owning surface, not re-proposed here.
- **Erosion 300 s + `caster_share: 1.0` is the wave's long tail** (「對高 HP 的長耗損戰收益最大」): bounded for free by the victim's own HP pool and the dead-origin skip; no cap needed (dark.md prices none).

## Migration Plan

Nothing migrates. Registry dark block swap + rulebook row re-home/new rows + fear lock row + echo-test retirement + shard finalization; offline scenario proof; synthetic settlement tests for the compositions. Main-spec sync, ledger and freeze-list edits stay in the separately authorized workflow.

## Open Questions

One tension resolved at authoring: the design note 深淵神格 mentions 「加上其侵蝕掠取」 among the capstone's stacked clauses, but the node DATA row carries no erosion DoT for `abyssal_apotheosis` (only damage/devastation/−25 debuff/15 % recovery), and the leech has no carrier without an erosion tick (dark.md's own 侵蝕即掠取 note names the erosion tick as the verb's carrier). Per the node-data-authority rule the DATA row wins: the capstone prices no erosion row, and the note reads as the tree's two branches (erosion leech + self-recovery) converging at the apex, demonstrated — not stacked — in one node. If the lore owner later adds an erosion clause to the row itself, it authors as `buff_apply:dark_corrosion_deep` data with zero engine work. Otherwise nothing blocks: the −25 debuff's stat axes are read from the node row verbatim (攻擊力、防禦 only), and the void/apotheosis recovery fractions are the node table's own 10 %/15 %.
