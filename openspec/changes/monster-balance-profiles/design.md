## Context

See proposal.md — Why. Three facts shape the approach:

- The balance slots, their all-or-nothing record, and their validation already exist
  (`world/lore/monster_species.py`, requirements R3 and R6 of `monster-species-registry`); this change
  fills them and adds one invariant, rather than introducing a new data path.
- The consumer already exists: `world/rules/traits.py::initial_trait_config_for_variant` branches on
  `variant.combat_profile` and returns `(values, NUMERIC_SOURCE_APPROVED_PROFILE)` when it is populated,
  `(tier band, NUMERIC_SOURCE_INTERIM_TIER_BAND)` when it is not. `world/rules/monster_individual.py` is
  the only construction entry point, and the ambient, site, and acceptance-provisioning owners all build
  through it. No caller change is therefore needed for the numbers to take effect.
- The tier model (`world/lore/monsters.py`) already declares exactly the bands this approval is judged
  against: `hp_band`, a shared physical band on `atk_phys`/`agility`/`defense`, a `magic_power` band that
  is `(0, 0)` for every tier, and `guild_rank_range`. Nothing validated a rating against them.

## Goals / Non-Goals

**Goals:** the twelve approved rows land as literals; band and rank-range membership becomes a
construction-time invariant; the approval is recorded in the design document and bestiary without
rewriting an approved boundary; the frozen "no numbers" contracts are updated in the same change; the
numeric-source flip is pinned by a test rather than by editing callers.

**Non-Goals:** no re-derivation, re-tuning, or rounding of any approved value; no MP/SP/`magic_power`
invention for the six unregistered abilities; no skill, behaviour profile, or combat trait for them; no
change to damage, combat, or progression rules; no hunt publication (the two dependent changes own
that); no migration or rescaling of already-persisted individuals; no new capability.

## The approved values and the accepted rationale

The twelve rows of the proposal's table are the approval record. The accepted design rules behind them,
as approved:

- Every value lies inside the variant's declared tier band (low: HP 50–150, physical 3–8, magic `(0,0)`;
  mid: HP 200–400, physical 12–20, magic `(0,0)`).
- The ordinary variant takes the lower end of its tier's `guild_rank_range` and the stronger variant the
  upper end: low `F`/`E`, mid `D`/`C`.
- Low HP sits at the bottom of its band because a creation-budget character's per-hit damage against
  defense 3–8 is small, so the approved HP is what keeps a low-tier clear finite without making the
  individual trivial.
- Mid values are calibrated so a creation-budget character can only chip them — defense 12–20 against
  such a character's attack — which is what "a party of ordinary adventurers" means for the mid tier.
- `mp`, `sp`, and `magic_power` stay 0: monster magic is documented nowhere, every tier's magic band is
  deliberately `(0, 0)`, and the six special abilities have no executable mechanics, so a resource pool
  would have no consumer.

Calibration evidence (read, not restated as new data):

| Evidence | What it shows |
| --- | --- |
| `world/rules/combat/damage.py:239-244` | damage is `attack_part - defense` with a documented floor, so a mid-tier defense of 12–20 against a creation-budget attack yields only floor damage |
| `world/rules/rulebook/guild_economy.yaml` `exam_profiles` | the guild's own opponent ladder — E `hp 100 / atk 8 / agi 8 / def 7` through S `hp 200 / atk 20 / agi 20 / def 19` — brackets "ordinary adventurer" and shows that a mid variant's 12–20 defense sits above a low-rank opponent's attack |
| `world/rules/rulebook/combat.yaml` | the combat coefficients the damage formula above consumes |
| `world/rules/character_creation.py` + `world/lore/player_presets/` | creation allocates inside race bands and a fixed budget, so a fresh character's physical axes are at the low end of the human band, not near the mid band |
| `world/rules/rulebook/progression.yaml` | levelling grants skill proficiency and freeform scales only — no stat growth — so a character closes the mid-tier defense gap with equipment and skills, exactly as the design says |
| `world/lore/monsters.py:45-66` | the tier bands and `guild_rank_range` values the approval is judged against |

## Decisions

**D-B1 The twelve rows land as literal `MonsterCombatProfile` values and literal grades.** No consumer
computes them, no test recomputes them from a formula, and the diff is a data diff. `mp` and `sp` are
authored zeros, not omissions: the record is all-or-nothing, so a zero must be written to exist.

**D-B2 Band membership becomes a construction-time invariant with an injectable tier face.**
`validate_monster_species_registry` grows the same shape as its existing habitat/tier/grade faces: a
`tier_band_face` defaulting to `MONSTER_TIER_REGISTRY`. Shipped construction therefore fails at import on
an out-of-band rating, and behavior tests can exercise every rejection with invented bands. Alternative
rejected: a standalone new validator — it would let a future author call one and not the other, and the
module's own discipline is that one function validates everything before publication.

**D-B3 MP and SP are deliberately not band-checked.** The tier model declares bands for HP, the three
physical axes, and `magic_power`; it declares no pool band, so there is no tier truth to compare a pool
against. Inventing a pool band to make the invariant look symmetrical would be new balance content
nobody approved. The spec states this gap explicitly so it cannot be mistaken for an oversight.

**D-B4 Already-persisted individuals are never rescaled.** The design forbids silently re-scaling the
abilities of existing individuals when registry data changes. Individuals built before this change keep
their interim tier-band traits; individuals built after it carry the approved values and record
`approved_profile` as their numeric source. No migration, no rebuild pass, no database rewrite — the
divergence is bounded, visible through the construction boundary event, and converges as individuals are
recreated through their own owners.

**D-B5 The approved values are pinned by the existing registered data-contract module.** Behavior tests
stay on synthetic variants; the twelve literals are asserted in `world/lore/tests/test_monster_species_content.py`
(the module already holds this change's slot for shipped content and is already registered in
`tools/test_data_freeze.json`), which keeps `tools/test_data_lint check` honest: no behavior test names a
shipped species, variant, or number. A second, unregistered behavior module exercises the new invariant
with invented bands.

**D-B6 The approval is recorded by appended amendment, never by rewriting an approved boundary.** The
design document's own §8 gained an appended "提案交付" section after proposals were produced, precisely so
later facts do not rewrite §1–§7; this change appends a "平衡核准落地" subsection in that idiom, quoting
the approval scope (twelve variants plus the hunts the two dependent changes publish) and the values. The
bestiary's usage boundary currently states that numbered commissions are unpublished and that the numeric
and grade fields stay explicitly empty; the same appended-subsection idiom corrects that stale sentence.
The registry stays the runtime source of truth — the documents are the approval record, and no consumer
reads a number out of prose.

**D-B7 The invariant is about the tier's truth, not about the approval.** Band membership proves a rating
is not absurd; it does not prove it was approved. That is why the invariant and the literal pin are two
requirements: a later edit could move a value to a different in-band number and pass the band check, and
only the literal pin catches it.

## Risks / Trade-offs

- Low-tier fights become longer than the interim band values implied (HP at the bottom of the band with
  defense 3–8 and a creation-budget attack). This is the approved calibration, not a defect; the evidence
  table above is the record of it, and any future change to it is a new balance approval.
- An existing development database mixes interim-band individuals with approved-profile ones →
  documented and deliberate (D-B4); a reset or the owners' own recreation converges the population, and
  the construction boundary event names the numeric source for each individual.
- The band invariant makes any future authored rating fail loudly at import → that is the point; the
  error names the variant, the axis, the value, and the band it left.

## Design document amendment (applied by this change's implementation)

Appended to `docs/superpowers/specs/2026-10-05-monster-data-model-design.md` §8 as a new subsection
after "提案交付", and to `docs/lore/bestiary.md` as a new subsection after "提案交付對應":

```markdown
### 平衡核准落地（2026-10-06）

本節於平衡核准後追加，不修改上文任何已核准邊界與使用邊界。

§8 外部前置條件（一）「使用者平衡核准」——各變體完整能力數值（HP、MP、SP、物理戰鬥力、敏捷、
防禦、魔力）與最終公會危險評級——已於 2026-10-06 由使用者核准，範圍限於首批十二個變體，以及據此
發布的正式狩獵委託。核准數值逐字登錄於 `world/lore/monster_species.py` 的變體登錄
（`monster-balance-profiles`），並由登錄建構期不變式檢查落在該變體宣告的層級區間內。

核准判準（設計理由，非再次推導）：每個數值都落在該變體宣告的層級區間；普通變體取該層級
`guild_rank_range` 下緣、較強變體取上緣；低階 HP 取區間下緣，因為創造預算角色的單次傷害面對
防禦 3–8 很小；中階數值調整為創造預算角色只能微量削血（防禦 12–20 對上該角色的攻擊），這正是
「一支普通冒險者隊伍」的意思；MP、SP 與 `magic_power` 維持 0，因為魔物魔法在任何地方都沒有文件，
每個層級的魔法區間刻意為 `(0,0)`，而六項特殊能力尚無可執行機制，資源池沒有消費者。

（一）的剩餘部分——據此發布含數值的正式狩獵委託——由 `monster-regional-species-hunts`（四個有環境
配置地區的區域狩獵）與 `monster-site-clear-out-hunts`（三處明訂據點的綁定清剿）承接；東南海岸沒有
環境配置，因此不發布區域狩獵。個體危險評級不會成為任何委託的階級。前置條件（二）特殊能力機制與
（三）官方圖片套裝維持未滿足。
```

The bestiary copy states the same scope and adds: the numbers and grades of other species remain
unapproved and their slots stay explicitly empty; the commission background examples still do not
constitute published commissions, because rank, rating rationale, and structured objectives are authored
separately by the two hunt changes; the six abilities remain unimplemented.

## Open Questions

None. The remaining external prerequisites (ability mechanics, official artwork package) stay owned by
other work; no decision here depends on them.
