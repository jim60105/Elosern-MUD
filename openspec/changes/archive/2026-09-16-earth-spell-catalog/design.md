## Context

Final data-only integration of the earth wave: the 14-node tree of `docs/lore/skill-trees/earth.md` authored into `world/skills/registry.py` + the earth rulebook rows over the vocabulary the two behavior changes ship. This design.md is the wave's single integration contract (light/water/dark pattern): interface-ownership matrix, batch order, shared verification contract, and the per-node coverage table below govern ALL earth changes; the behavior changes defer to it on interface names and land first. Pre-audited engine facts and user-ratified givens (recorded where they bind):

- **NON-GOAL — game-data contracts.** No earth catalog/data-contract tests: no key-set equality, no row mirroring, no MP-cost/cap/tier assertions, no echo of the earth.md table. All verification is BEHAVIOR contracts on synthetic skills/state transitions (light/water/dark convention).
- **No second rules engine / no earth-key branches in generic code.** Everything this wave adds is declarative vocabulary on existing surfaces: the `marker: ground` clause + `buff:<key>` predicate + `unconditional_defense_bypass` (terrain-marker), the `physical_hit` event + `counter_damage` then-action (on-hit-counter-damage), `buffs.yaml`/`state_reactions.yaml` rows, registry data.
- **Zero users: no migrations, no aliases, no back-compat.** The dev-era earth rows are wholesale replaced; re-homed buff keys carry the new numbers with no alias; `earth_bind`/`earth_root` are deleted without trace (束縛 stays ice's verb — 土讓腳下變壞，冰讓身體停下). Behavior tests replace echo tests where they exist.
- **Serialization:** `openspec list --json` returned an empty change set at authoring time — the dark wave is FULLY ARCHIVED. The two sibling earth changes are queued from this file's Batch section; conflict matrix: `terrain-marker` and `on-hit-counter-damage` are file-disjoint EXCEPT the shared `world/rules/combat.py` `_handle_damage` (textually disjoint hunks, same function — the supervisor SEQUENCES their merges, terrain-marker first); `earth-spell-catalog` is strictly after both (authored data over their shipped grammar).
- **Node-data authority:** MP costs and coefficients are authored from earth.md's columns AS-IS — do NOT rebalance. Some 範圍 nodes' costs (dust_veil 22, ground_fissure 42, earthen_ward 75) sit in the 單體 band of §3.1 by the lore's own pricing; the cost-derived tier grouping already tolerates exactly this (light/water/dark precedent) and `spell_tier_for` still derives the node 位階 — implementation verifies the derivation, never «corrects» the cost. Cap semantics: reverse-edge derived, leaf 10 (`proficiency_cap`, already implemented; no stored cap field). Lv.N thresholds are `SkillPrerequisite(node, N)` data rows only. The 裂縫 DoT values (−12/10 s rung, −40/10 s top) and durations (60/40/90 world-seconds) live in the node table and are authored verbatim.

## Goals / Non-Goals

**Goals:** Registry data for all 14 nodes; every lore clause delivered by some primitive the wave owns (coverage table); old rows gone without trace including the bind node; echo tests retired the dark way; the two-root/two-branch/two-parent-capstone lineage validated through the shipped lineage engine; wave-wide integration contract stated once.

**Non-Goals:** No new behavior code in this change (anything missing is a defect in the behavior changes, fixed there, not bolted on here); no main-spec sync, no freeze-list pre-editing, no command-surface work; no data-contract tests; `earth.md` and `tests/test_command_docs.py` untouched; `magic-system.md` §3 touched only if a real contradiction surfaces; the 2026-08-12 design doc stays frozen history; 鎖動作 stays ice's verb (explicitly out of the earth tree per the lore note); no ice-side row changes (`ice_slow` reuse is pure consumer-side data).

## Decisions

### D1 — Node coverage table (all 14 nodes × delivering primitive)

Stat-axis mapping (lore → engine): 防禦→`defense` bounds ceilings; 命中→`accuracy` bounds ceiling; 敏捷 −3→ the shipped `ice_slow` key reused via `buff_apply:ice_slow` (lore explicitly names 冰階梯第一 rung — pure data reuse, no ice-side edit). Buff keys below are the authored homes; `earth_hardened_skin`/`earth_stone_armor`/`earth_dust_veil`/`earth_ward` are re-homes (same key, node-table numbers), the rest are new; `earth_root` is deleted.

| Node (key) | 節點數據 (earth.md) | Delivered by |
|---|---|---|
| 硬化肌膚 `hardened_skin` | 學徒 10 MP 單體(自)；防禦 +3，60 s；cap 3 | `self_buff_apply:earth_hardened_skin` (re-homed bounds row defense +3 / 60 s — numbers unchanged, SELF_ONLY shape kept); root |
| 岩甲術 `stone_armor` | 術師 24 MP 單體；防禦 +5，60 s；cap 3 | `buff_apply:earth_stone_armor` (re-homed defense +5 / 60 s); prereq (hardened_skin, 3) |
| 磐石壁壘 `bedrock_bastion` | 大師 45 MP 範圍(友)；全體防禦 +8，60 s；cap 5 | NEW `buff_apply:earth_bedrock` (bounds defense +8 / 60 s, audience ALLIES); prereq (stone_armor, 3) |
| 大地庇護 `earthen_ward` | 賢者 75 MP 範圍(友)；全體防禦 +12，60 s；cap 10 | `buff_apply:earth_ward` (re-homed defense 5→12 / 60 s, audience ALLIES); prereq (bedrock_bastion, 5) |
| 荊棘反甲 `thorned_carapace` | 大師 40 MP 單體(自)；受到物理攻擊時反彈 1.0 係數的傷害；cap 10（樹冠） | NEW `self_buff_apply:earth_carapace` (empty-modifier self buff, duration 60 s per the tree's own buff band — the row prices no effect; the counter is reaction data, D2) + ONE `state_reactions.yaml` rule `thorned_carapace_counter`: `when {event: physical_hit, buff_active: earth_carapace}` `then {counter_damage: 1.0}` — the on-hit-counter-damage shipped vocabulary, holder-gated through the shipped `buff_active` when-key (D2); prereq (stone_armor, 3) |
| 石礫術 `stone_shard` | 學徒 12 MP 單體；1.0；cap 3 | `damage:earth:magic` coefficient 1.0; root |
| 沙塵術 `dust_veil` | 術師 22 MP 範圍；命中 −5，20 s；cap 3 | `buff_apply:earth_dust_veil` (re-homed: accuracy −5 kept, duration 60→20 per node table); prereq (stone_shard, 3) |
| 地裂術 `ground_fissure` | 大師 42 MP 範圍；地面裂開成縫，留在裂縫上的目標承受土地形 DoT −12／10 s 並掛冰階梯第一 rung（敏捷 −3），持續 60 s；cap 5 | `buff_apply:earth_fissure` (NEW terrain-marker row: `marker: ground`, rate hp −12 per 10 s, duration 60) + `buff_apply:ice_slow` (shipped reuse, 敏捷 −3/60 s); prereq (dust_veil, 3) |
| 岩壁崩落 `rockslide` | 大師 48 MP 範圍；1.4；cap 8 | coefficient 1.4; prereq (dust_veil, 3) |
| 地震術 `earthquake` | 賢者 90 MP 範圍；2.0，附加裂縫地形標記（效果同地裂術），持續 40 秒；鎖動作一事仍由冰的標記執行；cap 8 | coefficient 2.0 + `buff_apply:earth_fissure_quake` (NEW marker row: same clause + rate −12/10 s, duration **40** per the node — the row-level duration cannot be shared with the 60 s key, D5) + `buff_apply:ice_slow`; prereq (ground_fissure, 5) |
| 地脈崩裂 `fault_rupture` | 賢者 80 MP 單體；2.8；cap 8 | coefficient 2.8; prereq (rockslide, 8) |
| 山嶽崩落 `mountain_collapse` | 主宰 150 MP 範圍；2.8，毀滅級；cap 10 | coefficient 2.8 + `DamagePolicy(max_hp_fraction=0.10)` (existing devastation rider); prereq (earthquake, 8) |
| 大地審判 `earths_judgment` | 主宰 130 MP 單體；4.0，處決級（無視防禦）；對站在裂縫標記上的目標額外 +0.6；cap 10 | coefficient 4.0 + `DamagePolicy(predicate=("buff:earth_fissure", "buff:earth_fissure_quake", "buff:earth_fissure_apex"), attack_multiplier=1.15, unconditional_defense_bypass=True)` — the terrain-marker shipped seam; the synergy rung is the multiplier whose product carries the node's intent, the catalog-owned numeric decision recorded in D6 (any-match-once pins one application); prereq (fault_rupture, 8) |
| 大地神格 `earthen_apotheosis` | 神格 220 MP 範圍；3.8，毀滅級，額外召出覆蓋全場的裂縫地形（留在其上者吃土地形 DoT 頂規 −40／10 s＋敏捷 −3），持續 90 s；cap 10 | three independent effect components: coefficient 3.8 + devastation policy `max_hp_fraction=0.10` + `buff_apply:earth_fissure_apex` (NEW marker row: clause + rate −40/10 s, duration 90) + `buff_apply:ice_slow`; 「覆蓋全场」 = the area audience applies the apex marker to every enemy target the area cast selects (targeting already does全场); two prerequisites (mountain_collapse 10 + earths_judgment 10) ride the existing n-ary DAG + capstone derivation |

cap column → existing reverse-edge tip-cap derivation (leaf 10); this change authors no cap field. 位階 labels are display grouping via the existing tier derivation from MP cost; costs authored as-is per the given (the cost-derived tier grouping tolerates rungs as light/water/dark showed — implementation verifies the derivation, never rebalances the cost).

### D2 — The counter rides the reaction table with a `buff_active` holder gate

`thorned_carapace`'s buff row carries NO modifier (empty `modifiers`, marker-less — the carapace is not terrain): it is the mount the shipped `when.buff_active` condition keys off, exactly the `poison_agility_penalty`/`fear_locks_actions` precedent inverted from the modifier table to the reaction table (the reaction engine's dispatch context already resolves `active_buffs` from storage — verified shipped). One rule id `thorned_carapace_counter` with `when: {event: physical_hit, buff_active: earth_carapace}`, `then: {counter_damage: 1.0}`; `counter_damage` validation and settlement are the on-hit-counter-damage change's shipped surface — this change ships the first live rule. No duration on the counter itself: it lives and dies with the carapace buff instance (60 s band, refresh stacking).

### D3 — Wholesale replacement, key census

Old→new registry: nine dev-era keys re-authored under tree data (coefficients, prereqs, new bindings); FIVE keys added (`bedrock_bastion`, `thorned_carapace`, `ground_fissure`, `fault_rupture`, `earthen_apotheosis`); `earth_bind` DELETED (no lore node; its `earth_root` control row and `束縛`-flavored display row retire with it — ice's `water_bind`/ice keys remain the game's 束縛 suppliers). Buff keys: five re-homes (`earth_hardened_skin` +3/60 unchanged, `earth_stone_armor` +5/60 unchanged, `earth_ward` +5→+12/60, `earth_dust_veil` −5 accuracy 60→20 s, no polarity drift), `earth_root` DELETED, FIVE new rows (`earth_bedrock` +8/60, `earth_carapace` empty/60, `earth_fissure` marker −12/60, `earth_fissure_quake` marker −12/40, `earth_fissure_apex` marker −40/90 — the quake/apex split is D5). Reaction rows: one new rule (D2). `ice_slow` untouched (reused via `buff_apply:ice_slow` — the consumer side owns the reuse). Display-key census obligation: `earth_fissure`/`earth_fissure_quake`/`earth_fissure_apex`/`earth_bedrock`/`earth_carapace` added, `earth_root` deleted. The reaction rule id needs NO display row: the fail-closed census (`world/rules/status_display.py`) covers exactly the live buff definition keys ∪ combat-modifier rule ids — state-reaction rule ids are NOT in it (verified at authoring).

### D4 — Wave interface-ownership matrix (integration contract for all earth changes)

| Interface | First owner | Consumers |
|---|---|---|
| `marker: ground` clause + standing-on-it fact + battlefield-exit extinguishment + `buff:<key>` predicate entry + `unconditional_defense_bypass` | terrain-marker | catalog (fissure rows + `earths_judgment` policy data), any future element's ground hazard |
| `physical_hit` event + `counter_damage`/`apply_buff_to_source` then-actions | on-hit-counter-damage | catalog (`thorned_carapace_counter` rule + buff row); future fire `scorching_armor` (data over the same event) |
| 14-node registry block + earth buff/reaction rows + status-display census sync + echo-test retirement + shard manifest final state | this change | — |
| (inherited, unchanged) `ice_slow` key, execution/devastation rungs, reverse-edge caps, grant-time source attribution, n-ary lineage DAG | archived light/water/dark waves | this wave's data only |

Shared-file schedule: `terrain-marker` owns `buffs.py`/`target_facts.py`/`effects.py`/`combat_session.py` + tests; `on-hit-counter-damage` owns `state_reactions.py` + the `_handle_damage` dispatch leg + tests; this change edits only the registry earth block, `buffs.yaml`/`state_reactions.yaml`/`status_display.yaml` earth rows, the three test files (D7), `docs/development/adding-spells.md` (one example-key re-point) and the shard manifest's last edits. Two files are touched by two changes each but strictly sequentially, never concurrently: `buffs.yaml` (terrain-marker ships zero rows; the catalog owns every row) and `state_reactions.yaml` (on-hit ships zero rules + engine; the catalog owns the one rule) — the conflict matrix is empty by schedule.

### D5 — The fissure duration split (node-table-forced, recorded decision)

`buffs.yaml` durations are row-level, so the 60 s (地裂術) and 40 s (地震術) fissure durations cannot share one definition key; the node table prices them as two durations, so the catalog authors `earth_fissure` (60 s) and `earth_fissure_quake` (40 s, identical DoT) as ordinary parallel rows — the same parallel-key pattern as `dark_corrosion`/`dark_corrosion_deep`. `earths_judgment`'s predicate lists all three fissure keys (ANY-match-once keeps one multiplier application regardless of which rung the target stands in); 大地神格's全场 apex row (90 s, −40) is its own key — the DoT rung is part of the row. If the lore owner later unifies durations, one row deletes with zero engine work.

### D6 — The synergy numeric (catalog-owned, from terrain-marker's open question)

earth.md prices 「額外 +0.6」 next to a multiplicative 4.0 coefficient; the shipped seam prices multipliers. Resolution owned here, authored now: `attack_multiplier=1.15` (4.0 × 1.15 = 4.6 == coefficient 4.0 + 0.6 on the same base — the flat +0.6 lands exactly as an 11.5 % rung on the node's own coefficient). The predicate-hit strike is 4.6-coefficient AND unconditionally defense-bypassing; the non-standing strike stays 4.0 bypassing. Recorded so implementation authors the number, not re-derives it.

### D7 — Echo-test retirement (dark-spell-catalog's exact pattern)

`skill-registry::skill-registry-contains-the-full-土-element-spell-set` REMOVED with reason (mandates the duplicated dev-era ten-row data contract — no prerequisites, no coefficients, an off-tree bind node; the ratified wave NON-GOAL rules out earth catalog/data-contract tests) and migration (delete `EARTH_SPELL_CATALOG` + its test class in `world/skills/tests/test_spell_catalogs.py`, the earth rows in the tier-correspondence table in `world/skills/tests/test_cost_tiers.py`, the obsolete traceability/freeze entries during the separately authorized main-sync; replaced by the ADDED behavioral requirement in this change's delta). `world/rules/tests/test_buffs.py`'s five earth row tests are per-row numeric pins; DECISION (explicit): the four surviving tests STRIP to load/apply/presence assertions, NO re-pinned durations/ceilings (pinning catalog data is the banned row-mirror pattern); `earth_root`'s test retires with its deleted row. The other elements' echo requirements stay untouched — earth's retirement is scoped to earth.

### D8 — Batch order

1. `terrain-marker` → `on-hit-counter-damage` — independent in content; the supervisor SEQUENCES their merges (shared `world/rules/combat.py` `_handle_damage`, disjoint hunks; terrain-marker first).
2. `earth-spell-catalog` — after BOTH merge (data over their shipped grammar).

### D9 — Verification contract, shared by the whole wave

1. **Every test is behavior on synthetic state** — synthetic skills/buffs/entities, real settlement through the action/buff/clock/combat/session/reaction stages; tests MUST fail on plausible bugs (defense ladder read-back wrong, fissure marker ticking after flee, synergy firing off-marker, counter chaining, capstone gate leak, deleted bind key resolving through an alias). Source-text, data-echo and row-mirror assertions are prohibited, including in this catalog change.
2. **The catalog change's own proof** is a disposable offline engine scenario exercising each distinct D1 composition through real casts (defense ladder at authored values/durations + expiry; dust accuracy −5 at 20 s; fissure DoT + `ice_slow` co-application + expiry + flee sweep; earthquake's 40 s variant; execution bypass vs high defense with and without marker pricing at D6's rung; devastation riders on mountain_collapse/apotheosis; carapace counter at 1.0 against a physical attacker and silence vs magic attacker; capstone's three-component settlement; two-root branch/convergence gates + two-parent capstone through the lineage engine; deleted `earth_bind`/`earth_root` rejecting as unknown keys), plus synthetic behavior tests for settlement paths not already pinned by the sibling suites in a new module `world/rules/tests/test_earth_terrain_guard.py` (marker+synergy+unconditional-bypass composed settlement; carapace counter + nonlethal floor; family prerequisite/capstone gates on earth-shaped synthetic data). No catalog-row equality, key-set, cost/tier table or skill-tree-table echo assertions anywhere (ratified NON-GOAL).
3. **Focused invocation** (each change's tasks.md): `uv run --locked evennia test --settings test_settings.py --keepdb <modules>` with `MUD_TEST_SETTINGS=1` via the tool env, NEVER a shell prefix; plus `tools.observability_lint check`, `tools.test_data_lint check`, `tools.spec_traceability check`, `openspec validate <change> --strict`. No full local suite / browser / aggregate-coverage run; no command above ten minutes.
4. **Traceability:** canonical IDs via `uv run --locked python -m tools.spec_traceability list`; `@covers_requirement` literal IDs only; the retired 土-element ID leaves the ledger with its requirement at the separately authorized main-sync.
5. **Shards:** new non-browser test modules join exactly one shard in `.github/evennia-shards.json`; this change owns the wave's last manifest edit; the ownership-contract test verifies.

## Risks / Trade-offs

- **`earth_ward` +5→+12 and `earth_dust_veil` 60→20 s re-homes**: every existing consumer asserts mechanics (presence, bounds applied, expiry); `test_buffs.py`'s numeric pins strip to load/apply assertions per D7 rather than re-home (no re-pinned catalog data).
- **`earth_carapace` is an empty-modifier mount** — its whole meaning is being detectable (the shipped marker-buff definition shape); no display regression since display rows ride buff keys.
- **Three-key fissure predicate** lists marker rungs as data; a future unified duration collapses rows, not engine.
- **The bind-node deletion is the wave's only verb removal** — no shipped item, quest, spawn or preset references `earth_bind`/`earth_root` (repo-wide census at authoring found only frozen history docs, the echo tests and the dev-era rows themselves); implementation re-runs the census before editing.
- **Execution bypass + devastation already exist at HEAD** (water change 2 / light precedent); **unconditional-bypass-with-predicate ships in this wave's `terrain-marker`** (merged before this change) — if any fails fit at implementation it is a defect fixed in the owning surface, not re-proposed here.

## Migration Plan

Nothing migrates. Registry earth block swap + rulebook row re-home/new rows + one reaction rule + echo-test retirement + display census + shard finalization; offline scenario proof; synthetic settlement tests for the compositions. Main-spec sync, ledger and freeze-list edits stay in the separately authorized workflow.

## Open Questions

None blocking. Two tensions resolved at authoring: (1) 地震術's 持續 40 秒 is the fissure mark's duration, not the damage (the node's 2.0 prices no lingering) — D5 splits the row; if the lore owner meant a lingering quake field, it is one more marker row with zero engine work. (2) The 敏捷 −3 on all three fissure rungs rides `ice_slow`'s own 60 s duration rather than each fissure's duration (the reuse is 「掛冰階梯第一 rung」 — the rung's row, ice's authority); refreshing the fissure refreshes the marker, and the ice rung expires on ice's clock — the two facts are independent by the tree's own division of labor (土讓腳下變壞，冰讓身體停下).
