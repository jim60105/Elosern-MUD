## Context

Final data-only integration of the water wave: the 14-node tree of `docs/lore/skill-trees/water.md` authored into `world/skills/registry.py` over the vocabulary the three behavior changes ship. This design.md is the wave's single integration contract (the light wave's pattern): the interface-ownership matrix, the batch order, the shared verification contract, and the per-node mechanic coverage table below govern ALL water changes; behavior changes defer to it on interface names and land first. Pre-audited engine gaps and the user-ratified givens (recorded here verbatim where they bind):

- **NON-GOAL — game-data contracts.** No water catalog/data-contract tests: no key-set equality, no row mirroring, no MP-cost/cap/tier table assertions, no echo tests of the water.md table. All verification is BEHAVIOR contracts on synthetic skills/state transitions (the light wave's convention: program-behavior tests exercising mechanics; authored data lives only in registry rows + docs).
- **MP-depletion is an engine-level global fact.** "Entity MP reached zero via a decrease" is dispatched once by ONE canonical MP-decrease writer, payload carries source + tier (same convention as `hp_loss`'s source-tier in `state_reactions.yaml`). Cast-cost payment, buff rate ticks (潮退 DoT), and all future MP transfer effects route through that writer. Whether zeroing suffocates is filtered at the RULE layer by source conditions (skill_qualified-style), never by not-dispatching.
- **No-silent-window ordering.** The MP-depletion-reaction change lands BEFORE any 潮退 buffs.yaml row goes live; the DoT rows ship inside/after that change.
- **No second rules engine / no water-key branches in generic code** (inherited from the light design doc): new primitives are declarative vocabulary extensions to existing surfaces — typed effect classes in `world/skills/effects.py` `parse_effect`, `state_reactions.yaml` when/then vocabulary, `buffs.yaml` rate/recovery/divert profiles, `combat_modifiers.yaml`.
- **Zero users: no migrations, no aliases, no back-compat.** The dev-era water rows are wholesale replaced; old `water_*` buff keys are re-homed or removed without aliasing.
- **Serialization:** the light wave is FULLY ARCHIVED (all 10 changes incl. light-spell-catalog 2026-09-15; skill-taxonomy-consolidation archived same day, taxonomy at six categories). `openspec list --json` returned an empty change set at water authoring time — the water proposals apply to the post-archive master snapshot; no active-change file conflicts exist, so no cross-change serialization gate applies this wave (unlike Phase B).

## Goals / Non-Goals

**Goals:** Registry data for all 14 nodes; every lore clause delivered by some primitive the wave owns (coverage table); old rows gone without trace; echo tests retired the light way; wave-wide integration contract stated once.

**Non-Goals:** No new behavior code in this change (anything missing is a defect in the behavior changes, to be fixed there, not bolted on here); no main-spec sync, no freeze-list pre-editing, no command-surface work; no data-contract tests (given above); `water.md` and `tests/test_command_docs.py` untouched; `magic-system.md` §3 untouched unless implementation finds a real contradiction (none found at authoring: the section's water identity IS this tree).

## Decisions

### D1 — Node coverage table (all 14 nodes × delivering primitive)

| Node (key) | 節點數據 (water.md) | Delivered by |
|---|---|---|
| 潮引術 `tide_pull` | 單體 11MP；命中 −5 MP，施法者回收一半，cap 3 | `gauge_transfer:mp:drain:fixed:5` + `GaugeTransferPolicy(caster_recovery_share=0.5)`; cap = reverse-edge derivation (existing); prerequisite root |
| 潮退侵蝕 `ebbing_blight` | 術師 24MP；附加潮退 −5/10 s 60 s，流失不回收 | damage component + `buff_apply:ebbing` (rate {mp,−5} row from change 1); no share (流失量不回收 = no policy) |
| 水膜護身 `water_shield` | 術師 22MP 單體(自)；受擊 MP 代扣 30 %、上限 30、60 s | `self_buff_apply:water_film` (divert {mp,0.3,cap 30} row from change 3; inert bounds row deleted there) |
| 回流之環 `ring_of_reflux` | 大師 42MP 單體(友)；恢復 MP 40（`mana_restore` 量級）＋施法者每層潮退 +10 | `gauge_transfer:mp:restore:fixed:40` + `GaugeTransferPolicy(restore_bonus_per_stack=(ebbing 三 tier keys, +10))` (change 2 caster-side count) |
| 溺潮 `drowned_surging` | 賢者 78MP 單體；潮退 −18/10 s 60 s；歸零→窒息 40 s；MP 上限為零→等值水傷 | `buff_apply:ebbing_maelstrom` (change 1 row) + suffocation reaction rule (change 1: `mp_zero` event + `event_source_skill` qualification to this node — the row's authored home; the rule layer, not dispatch, filters source per the global-fact given) + max-zero redirect: `damage:water:magic` component gated by change 2's `audience_condition: mp_max_zero` — **placement: cast/effect composition side, NOT the reaction engine** |
| 枯海之印 `sigil_of_the_barren_sea` | 主宰 135MP；4.0 處決級（無視防禦）＋移除全部 MP＋60 s 無法恢復 MP | `damage:water:magic` coefficient 4.0 + `DamagePolicy(bypass_defense=True, predicate=())` (unconditional execution bypass shipped change 2) + `gauge_transfer:mp:drain:all` + `buff_apply:mp_regen_lock` (change 2 regen-scale-0 row) |
| 深淵潮汛 `abyssal_surge` | 賢者 82MP 範圍(友)；我方全體 +25 MP，各附著「回流」60 s：其後潮引系命中敵方額外回收 10 % | `gauge_transfer:mp:restore:fixed:25` (ALLY audience) + `buff_apply:mana_reflux` (change 2 `recovery_share_bonus: 0.1` bundle row; family scope is DATA — only share-authoring nodes consume the value) |
| 水箭術 `water_bolt` | 學徒 12MP；1.0 | `damage:water:magic` coefficient 1.0 (root; existing damage stage) |
| 深流刺 `deep_current_spike` | 術師 24MP；1.4 | coefficient 1.4 |
| 深海漩渦 `abyssal_whirlpool` | 大師 50MP 範圍；1.4＋潮退 −12/10 s 60 s＋束縛 | coefficient 1.4 + `buff_apply:ebbing_deep` + `buff_apply:water_bind` (bind → `actions_per_turn: 0` lock row shipped change 1; key re-homed, no alias) |
| 深淵巨口 `abyssal_maw` | 賢者 80MP；2.8，命中吸取目標現有 MP 20 % 轉入施法者 | coefficient 2.8 + `gauge_transfer:mp:drain:fraction:0.2` + policy share 1.0 (轉入施法者 = full actual amount returned) |
| 海嘯術 `tsunami` | 賢者 95MP 範圍；2.0 | coefficient 2.0 |
| 深淵巨潮 `abyssal_tide` | 主宰 145MP 範圍；2.8 毀滅級 | coefficient 2.8 + `DamagePolicy(max_hp_fraction=0.10)` (existing devastation rider) |
| 深海神格 `abyssal_heart` | 主宰(神格) 230MP；對敵 3.8 毀滅級＋抽乾全體敵方全部 MP；我方全體以 abyssal_surge 全量歸還（取予同源） | take-and-give composite: ENEMIES audience `damage:water:magic` 3.8 + devastation policy + `gauge_transfer:mp:drain:all`; ALLIES audience `gauge_transfer:mp:restore:fixed:25` (= abyssal_surge 全量, per 節點設計「灌滿」= surge's authored 25, the tree's own cross-reference). Two prerequisites (sigil Lv.10 + tide Lv.10) ride the existing n-ary DAG + capstone gate. Prerequisite note: the tree draws abyssal_surge as a convergence feeder, but the node table's 前置條件 column lists only 枯海之印＋深淵巨潮 — the data column is authority for edges |

cap column → existing reverse-edge tip-cap derivation (light's pattern; this change authors no cap field). 位階 labels are display grouping per the existing tier derivation; MP bands match.

### D2 — Wholesale replacement, key census
Old→new: `water_bolt` kept-but-reauthored (coefficients/prereq added); `water_shield` node kept with new effect binding (`buff_apply:water_shield`→`self_buff_apply:water_film`, self-target per the node table); `abyssal_whirlpool`/`tsunami`/`abyssal_tide` re-authored under tree data; the five HP-heal keys (`minor_heal`, `healing_spring`, `wellspring_of_life`, `tidal_revival`, `sea_of_life`) DELETED (healing belongs to light; the 假貨市場 seam in water.md §接縫 is the lore justification, already in docs). Grep census at implementation must show: registry block, `test_spell_catalogs.py`/`test_cost_tiers.py` echo tables (retired here), and the 2026-08-12 design doc table (frozen history, NOT edited — the superseding authority is water.md per AGENTS.md node-data rule; a pointer note MAY be added to §11-style roadmap sections only if the light precedent row exists). No typeclass/preset/scene references to the five keys exist (verified at authoring) — deletion must leave zero dangling imports.

### D3 — Wave interface-ownership matrix (integration contract for all water changes)

| Interface | First owner | Consumers |
|---|---|---|
| `world/rules/mp_flow.py` `apply_mp_change`/`remove_mp`; `mp_zero` event; `event_source_skill` when key | water-mp-depletion-reaction | gauge-transfer (mp legs; hp leg rides the existing hp-loss path), divert shield (payment), catalog suffocation rule |
| 潮退 tier rows `ebbing`/`ebbing_deep`/`ebbing_maelstrom`; per-key active-stack count query | water-mp-depletion-reaction (rows) / water-mana-transfer (count query) | catalog (節點綁定), ring_of_reflux bonus |
| `suffocated` marker + `actions_per_turn: 0` rows (suffocation + bind) | water-mp-depletion-reaction | catalog (溺潮/漩渦 data), combat gate consumers |
| `gauge_transfer:` family + `GaugeTransferPolicy`; `audience_condition`; unconditional bypass relaxation; `mana_reflux` + `recovery_share_bonus`; `mp_regen_lock` + `{gauge}_regen_scale` | water-mana-transfer | catalog authoring only |
| `divert` buff profile + damage-stage consumption + `water_film` key | water-damage-redirect-shield | catalog (`self_buff_apply:water_film`) |
| 14-node registry block + echo-test retirement + shard manifest final state | water-spell-catalog | — |

Shared-file schedule (all three behavior changes touch `buffs.yaml`/`.github/evennia-shards.json`/`action.py`): changes land strictly in batch order, each owning its additions; the catalog change edits only the registry water block + the two echo-test files.

### D4 — Verification contract, shared by the whole wave
1. **Every test is behavior on synthetic state** — synthetic skills/entities (the existing `_entity()` no-create fixture posture), real settlement through the action/clock/combat stages; tests MUST fail on plausible bugs (wrong order, double-dispatch, share-on-requested, cap bypass, audience misroute, half-applied rollback). Source-text, data-echo and row-mirror assertions are prohibited, including in this catalog change.
2. **The catalog change's own proof** is a disposable offline engine scenario exercising each distinct composition in D1 through real casts (drain+share, DoT ladder to zero→suffocation lock, divert exhaust, regen lock, max-zero redirect, composite take-and-give, capstone gate), plus synthetic behavior tests for the wave mechanics not already pinned by the sibling changes' suites (mixed-audience water composite settlement; prerequisite edges settle through the shared lineage engine).
3. **Focused invocation** (each change's tasks.md): `uv run --locked evennia test --settings test_settings.py --keepdb <modules>` with `MUD_TEST_SETTINGS=1` via the tool env, NEVER a shell prefix; plus `tools.observability_lint check` (state/event paths), `tools.test_data_lint check`, `tools.spec_traceability check`, `openspec validate <change> --strict`. No full local suite / browser / aggregate-coverage run; no command above ten minutes.
4. **Traceability:** canonical IDs come from `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-sync; `@covers_requirement` carries literal IDs only.
5. **Shards:** new non-browser test modules join exactly one shard in `.github/evennia-shards.json`; ownership-contract test verifies.

### D5 — Requirement retirement (light-spell-catalog's exact pattern)
`skill-registry::skill-registry-contains-the-full-水-element-spell-set` REMOVED with reason (duplicated ten-row data contract superseded by a 14-node tree + the ratified no-data-contract-tests given) and migration (delete `WATER_SPELL_CATALOG` + `WaterSpellCatalogTests`, tier-table water rows, ledger/freeze hygiene in the authorized sync; replaced by the ADDED behavioral requirement in this change's delta). The remaining five elements' echo requirements stay untouched — water's retirement is scoped to water.

## Risks / Trade-offs

- MP-cost bands: node costs (11…230) sit within the existing tier bands by construction (checked against `spell_tier_for` at implementation; a mismatch is resolved by water.md's column, which is authority — the tier derivation, not the cost, decides grouping today).
- 神格 tier: 深海神格's 位階 is 神格 while `spell_tier_for` bands by MP cost; light's capstone precedent shows the derivation already tolerates the top rung (bliss_apotheosis at 230-adjacent cost) — implementation verifies, and if the band is missing the catalog change adds the one authored tier label row (existing vocabulary), not a new mechanism.
- Suffocation rule → node key coupling (change 1 ships the row keyed to `drowned_surging` before the node exists): inert-but-valid per change 1's D5; the catalog change's offline scenario is the first real end-to-end proof of that arrow.

## Migration Plan

Nothing migrates. One commit: registry water block swap + buff re-home confirmation + echo-test retirement + shard finalization; offline scenario proof; synthetic settlement tests for the composite path. Main-spec sync, ledger and freeze-list edits stay in the separately authorized workflow.

## Open Questions

None blocking: the surge-vs-heart restore amount (25, the surge's authored全量) is fixed by the node table's own cross-reference "以 `abyssal_surge` 全量歸還".
