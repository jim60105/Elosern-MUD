# Sexual Act Catalog — Design

**Date:** 2026-08-15
**Status:** Approved (pending final user review)
**Scope:** `world/skills/sexual_acts/solo.py`, `shame.py`, `partner.py`, `combat.py`,
`interspecies.py`.

Part of the [Sexual Act System document set](2026-08-15-sexual-act-system-overview-design.md).
Covers proposals `B8` (seeds), `C2`–`C6` (the five counter-gated lines).
The 神之秘法 line has its own document: [Divine Sexual Arts](2026-08-15-divine-sexual-arts-design.md).

Mechanics are defined in [Act Resolution](2026-08-15-sexual-act-resolution-design.md) and the
[Pleasure Model](2026-08-15-sexual-pleasure-model-design.md). This document is the content.

---

## 1. Shape of the Catalog

**62 counter-gated acts across five lines**, plus 7 divine acts in the companion document — 69 new
acts in total.

| Line | Module | Acts | Primary counters |
|---|---|---|---|
| 獨處 | `solo.py` | 17 | 自慰次數, 玩具使用次數, 忍耐次數 |
| 羞恥 | `shame.py` | 10 | 露出次數, 被觀看次數 |
| 關係 | `partner.py` | 18 | 雙人行為次數, 多人行為次數 |
| 戰鬥 | `combat.py` | 10 | 對敵行為次數, 連續高潮次數 |
| 異種 | `interspecies.py` | 7 | 異種行為次數 |

**Seven seeds** (empty `unlock`, available from the first round) span all three targeting shapes, so
every line is enterable immediately: 自撫, 揉捏胸部, 摩擦大腿, 撩起衣襬, 愛撫, 牽手交纏, 挑逗.

### 1.1 Why near-duplicate acts are not duplicates

Several acts at the same tier share mechanics and differ mainly in flavour and body part. This is
intentional, and it is **also mechanically real**: `SexualState.sensitivity` is a per-part mapping,
and the shipped `sensitivity_up_on_frequent_stimulation` rule raises only the part named by the
triggering event. Three same-tier acts on three different parts therefore train three independent
sensitivity curves, and after sustained play their effective magnitudes diverge sharply
(`普通` ×1.0 → `敏感異常` ×2.5).

Part variety is a build choice, not decoration.

### 1.2 Threshold calibration

Thresholds target roughly one tier advance per three to five hours of play on a line the player is
actively pursuing. Every number below is a `sexual_acts` module constant and trivially tunable; none
is load-bearing for correctness.

---

## 2. 獨處線 — `solo.py` (17)

Solo acts. Participants = the actor alone, so the self-limiting invariant is trivially satisfied and
every act is a pure self-gauge builder. Out of combat this is the primary progression engine; in
combat it is almost always a mistake, which is the point.

| Tier | Unlock | Act | Part |
|---|---|---|---|
| 0 | seed | 自撫 | 私處 |
| 0 | seed | 揉捏胸部 | 乳房 |
| 0 | seed | 摩擦大腿 | 大腿 |
| 1 | 自慰 ≥ 10 | 深度自慰 | 私處 |
| 1 | 自慰 ≥ 10 | 雙手併用 | 乳房 → 私處 |
| 1 | 自慰 ≥ 10 | 舔舐指尖 | 口唇 |
| 1 | 自慰 ≥ 10 | 撫弄後庭 | 後庭 |
| 1 | 自慰 ≥ 10 | 玩弄乳尖 | 乳房 |
| 2 | 自慰 ≥ 25 | 玩具自慰·振動 | 私處 |
| 2 | 自慰 ≥ 25 | 玩具自慰·夾具 | 乳房 |
| 2 | 自慰 ≥ 25 | 玩具自慰·填充 | 後庭 |
| 3 | 玩具 ≥ 15 | 高階玩具·連結 | 私處 |
| 3 | 玩具 ≥ 15 | 高階玩具·全身 | multi-part |
| 3 | 玩具 ≥ 15 | 拘束自慰 | multi-part; self `defense` penalty for high gain |
| — | 忍耐 ≥ 10 | 快感控制 | —; **reduces** own pleasure without climaxing |
| — | 忍耐 ≥ 10 | 寸止 | —; holds at the `極限` band, 忍耐次數 +2 |
| — | 忍耐 ≥ 30, 高潮 ≥ 20 | 極限忍耐 | —; large reduction plus several rounds immune to `climax_gate` |

The 玩具 tier fulfils the "masturbation count unlocks toy use" progression: 自慰次數 opens toys, and
玩具使用次數 then opens the higher toy tier. Toys are counter-gated, not inventory-gated (see §7).

The three 忍耐 acts are the **counterplay to the whole system**. They are the only way to shed
pleasure, and they are gated behind a counter earned by deliberately not climaxing — so the player
who over-uses acts cannot buy their way out, while the player who learned restraint can.

---

## 3. 羞恥線 — `shame.py` (10)

Self-targeting acts that raise the actor's own `exposure`, feeding the shipped
`shame_up_on_exposure_increase` rule and, at high exposure, the new
`high_exposure_defense_penalty` combat modifier. Their offensive payoff is a distraction debuff on
enemies who can see the actor.

| Tier | Unlock | Act | Effect shape |
|---|---|---|---|
| 0 | seed | 撩起衣襬 | small `exposure` raise |
| 1 | 露出 ≥ 5 | 半露出·胸口 | `exposure` raise |
| 1 | 露出 ≥ 5 | 半露出·下身 | `exposure` raise |
| 1 | 露出 ≥ 5 | 解開衣襟 | `exposure` raise |
| 2 | 露出 ≥ 20 | 全露出 | large `exposure` raise; heavier self `defense` cost |
| 2 | 露出 ≥ 20, 自慰 ≥ 25 | 公開自慰 | solo pleasure **and** `被觀看次數` when observed |
| 3 | 被觀看 ≥ 10 | 挑釁凝視 | `accuracy` debuff on all enemies who can see the actor |
| 3 | 被觀看 ≥ 10, 露出 ≥ 20 | 公開表演 | pleasure to **everyone present**, allies included |
| 4 | 露出 ≥ 50 | 獻身姿態 | severe self `defense` penalty; pleasure to all enemies |
| 4 | 露出 ≥ 50, 被觀看 ≥ 30 | 無恥宣言 | self-buff: several rounds treating `shame` as `成癮` (×1.6) |

This line embodies the growth arc most directly. Early exposure acts raise `shame`, which *lowers*
the pleasure multiplier — so the line makes the character worse at everything before it makes them
better. 無恥宣言 at the top is the payoff: it purchases the `成癮` multiplier temporarily, years
before the character could reach that state naturally.

---

## 4. 關係線 — `partner.py` (18)

Two-person and group acts. Every act here is resistible and consumes both parties' turns on a
comply, per [Act Resolution](2026-08-15-sexual-act-resolution-design.md) §5.

| Tier | Unlock | Act | Part / note |
|---|---|---|---|
| 0 | seed | 愛撫 | 腰腹 |
| 0 | seed | 牽手交纏 | 低 pleasure; small affinity gain — the non-coercive opener |
| 1 | 雙人 ≥ 5 | 親吻 | 口唇 |
| 1 | 雙人 ≥ 5 | 撫摸頸項 | 頸項 |
| 1 | 雙人 ≥ 5 | 揉捏胸部 | 乳房 |
| 1 | 雙人 ≥ 5 | 耳邊細語 | 耳朵 |
| 2 | 雙人 ≥ 15 | 深度愛撫 | 私處 |
| 2 | 雙人 ≥ 15 | 口舌服務 | 口唇 |
| 2 | 雙人 ≥ 15 | 乳交 | 乳房; emits `breast_sex_performed` |
| 2 | 雙人 ≥ 15 | 腿間摩擦 | 大腿 |
| 2 | 雙人 ≥ 15 | 足部服務 | 足部 |
| 3 | 雙人 ≥ 30, 高潮 ≥ 10 | 交合 | 私處; sex-dependent event, §4.1 |
| 3 | 雙人 ≥ 30, 高潮 ≥ 10 | 深度交合 | 私處; sex-dependent event, §4.1 |
| 3 | 雙人 ≥ 30, 高潮 ≥ 10 | 後庭交合 | 後庭; never breaks `virgin`, §4.1 |
| 3 | 雙人 ≥ 30, 高潮 ≥ 10 | 相互自慰 | bidirectional gain doubled |
| 4 | 雙人 ≥ 30 | 多人愛撫 | AREA |
| 4 | 多人 ≥ 15 | 多人交歡 | AREA |
| 4 | 多人 ≥ 30 | 群體服務 | AREA |

乳交 is the sole emitter of `breast_sex_performed`, a rule that has existed unemitted since the
transition rulebook landed.

牽手交纏 exists as a deliberate low-magnitude, affinity-positive opener: it lets a player raise a
companion toward the `至愛` auto-comply threshold without ever forcing anything.

### 4.1 Which acts break `virgin` (overview D-12)

`virgin` breaks **only on vaginal intercourse with an opposite-sex partner**. The rulebook already
draws this line and always has: `virginity_once` is conditioned on `first_vaginal_penetration`, while
`penetrative_sex_with_female` adds the `女女性愛` experience type and deliberately never touches
`virgin`. No rule change is needed — the branch lives here, in which event each act emits.

The branch reads the new `sex` field introduced by proposal `S1` (overview §4.2). Nothing in the
codebase carries sex data today; `CHARACTER_SCHEMA_V1` declares `age`, `apparent_age`, `race`, and
`subrace` only.

| Act | Partner | Event emitted | Breaks `virgin` |
|---|---|---|---|
| 交合 / 深度交合 | opposite sex | `first_vaginal_penetration` | **yes** |
| 交合 / 深度交合 | both female | `penetrative_sex_with_female` | no (adds `女女性愛`) |
| 交合 / 深度交合 | both male | `penetrative_sex_with_male` | no (adds `男男性愛`) |
| 交合 / 深度交合 | either party `other` / unknown | `penetrative_sex_with_female`'s shape, no virgin rule | no |
| 後庭交合 | any | no penetration event | no |
| 異種交合 | a `Monster` (always `other`) | `sexual_activity_with_nonhuman` | no |

Two consequences worth stating:

- **`virgin` breaks symmetrically.** Because acts apply to every participant, an opposite-sex 交合
  breaks it for both parties at once, which is correct and needs no extra logic.
- **The monster case falls out for free.** A `Monster` has no sex record and resolves to `other`, so
  異種交合 can never break virginity without any special-casing — the same shape as the
  `GENERIC_BODY_PART` collapse.

`penetrative_sex_with_male` and its `男男性愛` experience type do **not** exist in the shipped
`sexual.yaml`; only the female-female counterpart does. Adding that one rule row is scoped to
proposal `B3`, which already owns `sexual.yaml`, so this catalog proposal stays pure data. Without
it the table would be asymmetric — female-female recorded, male-male silently unrecorded.

---

## 5. 戰鬥線 — `combat.py` (10)

Offensive acts against hostile targets. Because they are bidirectional, sustained use degrades the
actor through the shipped `high_arousal_agility_accuracy_penalty` and eventually locks their own
actions — the attrition race that gives the line its texture.

| Tier | Unlock | Act | Effect shape |
|---|---|---|---|
| 0 | seed | 挑逗 | 腰腹; low magnitude |
| 1 | 對敵 ≥ 5 | 挑逗·耳語 | 耳朵 |
| 1 | 對敵 ≥ 5 | 挑逗·觸碰 | 腰腹 |
| 2 | 對敵 ≥ 20 | 魅惑 | high pleasure plus `accuracy` debuff |
| 2 | 對敵 ≥ 20 | 束縛愛撫 | `agility` debuff |
| 2 | 對敵 ≥ 20 | 強制快感 | highest raw pleasure at this tier |
| 3 | 對敵 ≥ 40, 高潮 ≥ 30 | 強制絕頂 | magnitude reliably above `climax_extension_threshold` |
| 3 | 對敵 ≥ 40, 高潮 ≥ 30 | 連續責め | same, with a stronger self-gauge cost |
| 4 | 對敵 ≥ 60, 連續高潮 ≥ 10 | 搾取 | a share of the target's climax SP loss transfers to the actor |
| 5 | 對敵 ≥ 80, 連續高潮 ≥ 30 | 絕頂支配 | AREA 強制絕頂 |

**強制絕頂 and 連續責め are the extension tools.** Their magnitude is tuned to clear
`climax_extension_threshold` against a typical target, making indefinite suppression achievable — at
the cost of one of the actor's turns per round and a steadily climbing self-gauge.

**搾取 changes what the line is for.** Until it unlocks, sex acts are the free fallback when
resources run dry. 搾取 turns enemy climaxes into an SP source, making the line a genuine resource
engine. That is why it sits behind two counters, one of which (連續高潮次數) can only be earned by
having already run extension chains.

---

## 6. 異種線 — `interspecies.py` (7)

Targets must be a `Monster`. No act in this line declares a `target_part` — the target side always
resolves to `GENERIC_BODY_PART`, which is enforced as a structural invariant.

The line's identity comes from monsters' actual mechanical properties, not their anatomy:
`shame` is permanently clamped to `無` (×1.0 forever, never inhibited and never amplified),
sensitivity defaults to `普通`, and there is no affinity record so compliance can never be
automatic.

**These acts carry the highest actor-side pleasure ratio in the game.** Against a flat-multiplier
target, that makes the line the fastest counter-builder available and simultaneously the fastest
route to the actor's own climax. It is an excellent out-of-combat progression accelerator and close
to self-harm inside a fight — which suits a system whose stated centre of gravity is the growth
curve.

| Tier | Unlock | Act | Actor part |
|---|---|---|---|
| 1 | 對敵 ≥ 10 | 觸碰異種 | 腰腹 |
| 1 | 對敵 ≥ 10 | 異種愛撫 | 私處 |
| 2 | 對敵 ≥ 30 | 異種纏繞 | multi-part |
| 2 | 對敵 ≥ 30 | 承受異種 | 私處; highest actor ratio in the catalog |
| 3 | 對敵 ≥ 30, 高潮 ≥ 20 | 異種交合 | 私處; emits `sexual_activity_with_nonhuman` |
| 4 | 異種 ≥ 20 | 異種支配 | multi-part |
| 4 | 異種 ≥ 20 | 異種共鳴 | multi-part |

異種交合 is the sole emitter of `sexual_activity_with_nonhuman`, whose rule
(`experience_interspecies_added` → `異種性愛`) has existed unemitted since the transition rulebook
landed.

---

## 7. Toys Are Counter-Gated, Not Inventory-Gated

The 玩具 acts gate on `玩具使用次數` and on `自慰次數`, never on possessing an item. No object is
created, equipped, or consumed.

This keeps the catalog proposals pure data and out of `world/skills/equipment.py`, which is what
allows batch 6 to run seven fully parallel tracks. Wiring toys to real inventory objects is noted as
a future seam in the [overview](2026-08-15-sexual-act-system-overview-design.md) §6 and would be its
own proposal.

---

## 8. Testing Strategy

Because the catalog is data over already-tested mechanics, per-act behaviour tests would be 62
near-identical restatements. Coverage is structural plus representative instead:

- **Structural, over the whole catalog** (the invariants in
  [Act Resolution](2026-08-15-sexual-act-resolution-design.md) §2.5): every act's parts are
  `BODY_PARTS` members; no act declares `GENERIC_BODY_PART`; no 異種 act declares a target part;
  every named counter and event exists; every act applying pleasure to others applies non-zero
  pleasure to the actor; the two registries agree on keys.
- **Per line, one representative act end-to-end**: cast through `ActionResolver`, assert the
  participant set, the pleasure applied to each participant, the counters incremented on each
  ledger, and the events emitted.
- **Per line, one unlock-boundary test**: the act is absent from `owned_keys()` one point below its
  threshold and present at it.
- **Sole-emitter tests** for the acts that are the only emitter of a shipped rule's event:
  乳交 → `breast_sex_performed`, 異種交合 → `sexual_activity_with_nonhuman`, and 交合 against an
  opposite-sex partner → `first_vaginal_penetration`.
- **Virgin branch (§4.1):** one test per table row. The load-bearing ones are that a same-sex 交合
  leaves `virgin` `True` while adding the correct experience type, that 後庭交合 never breaks it,
  that 異種交合 never breaks it with no monster special-case in the implementation, and that an
  opposite-sex 交合 breaks it for **both** participants in the same resolution.
- **Seed availability**: all seven seeds are present in `owned_keys()` for a freshly created
  character with every counter at zero.
- **Sensitivity divergence**: two same-tier acts on different parts, repeated, produce measurably
  different magnitudes — the §1.1 claim, pinned.
