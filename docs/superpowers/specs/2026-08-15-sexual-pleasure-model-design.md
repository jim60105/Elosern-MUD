# Sexual Pleasure Model — Design

**Date:** 2026-08-15
**Status:** Approved (pending final user review)
**Scope:** `world/rules/sexual_state.py`, `world/rules/sexual_transitions.py`,
`world/rules/rulebook/sexual.yaml`, new `world/rules/rulebook/sexual_pleasure.yaml`,
`world/rules/rulebook/combat_modifiers.yaml`, `world/rules/combat.py`, `world/rules/clock.py`.

Part of the [Sexual Act System document set](2026-08-15-sexual-act-system-overview-design.md).
Covers proposals `B1` (gauge), `B2` (counters), `B3` (climax settlement), `B7` (combat modifiers).

---

## 1. The Pleasure Gauge

### 1.1 Why the existing five levels are insufficient

`arousal` is an `OrderedLevelTrait` over `("平靜", "微興奮", "中等", "高度", "極限")`, and
`arousal_up_on_stimulus` applies `+1..+2`. Three stimuli reach the top. That resolution cannot
express 69 acts of differing magnitude, cannot carry a sensitivity multiplier, and cannot support a
meaningful extension threshold.

### 1.2 The change

`pleasure` becomes the authoritative quantity: an integer `0..100` stored as a counter trait in
`SexualState`'s existing `sexual_traits` `TraitHandler`, beside `climax_today`.

`arousal` becomes a **derived, still-comparable** ordered-level view over `pleasure`. It keeps its
`OrderedLevelTrait` comparison surface (`.level`, `==`, `>=`, `<`, …) so that every existing reader
continues to work unchanged. Writing to `arousal` directly is no longer a supported path; the four
rules that did so are rewritten to target `pleasure` (§1.4).

The band table lives in a new `world/rules/rulebook/sexual_pleasure.yaml`, loaded through the shared
rule loader, so balance is data:

| `pleasure` | `arousal` |
|---|---|
| 0–14 | 平靜 |
| 15–34 | 微興奮 |
| 35–59 | 中等 |
| 60–84 | 高度 |
| 85–100 | 極限 |

The band boundaries are validated at load: exactly five contiguous ascending bands covering `0..100`
with no gap and no overlap, one per `AROUSAL_LEVELS` entry in order.

### 1.3 What this deliberately does not touch

Because `arousal` stays comparable against its vocabulary, **three files need no edit at all**:

- `world/rules/rulebook/combat_modifiers.yaml` — `high_arousal_agility_accuracy_penalty`
  (`{field: arousal, gte: 高度}`) keeps working verbatim.
- `world/rules/overwhelm.py` — reads effective stats, unaffected.
- `world/rules/rulebook/status_display.yaml` — displays the level name, unaffected.

This is the decision that keeps `B7` in the same parallel batch as `B1` (overview §4.3) and keeps
the whole combat-modifier surface off the dependency chain.

### 1.4 Rules rewritten in `sexual.yaml`

Four rules currently write `arousal`. Each keeps its `id` — the structural test
`test_every_rule_id_has_a_test()` pairs ids to tests, so preserving ids preserves the pairing.

| Rule id | Before | After |
|---|---|---|
| `arousal_up_on_stimulus` | `{field: arousal, delta: "+1..+2"}` | `{field: pleasure, delta: "+8..+14"}` |
| `arousal_up_on_sustained_stimulus` | `{field: arousal, delta: "+1"}` | `{field: pleasure, delta: "+6"}` |
| `arousal_extreme_stimulus_to_max` | `{field: arousal, set: 極限}` | `{field: pleasure, set: 100}` |
| `arousal_reset_after_climax` | `{field: arousal, set: 微興奮}` | `{field: pleasure, set: 15}` |

`FIELD_KINDS` in `sexual_transitions.py` gains `pleasure` and loses `arousal`. The existing
`test_field_kinds_covers_every_targetable_field()` structural check enforces that this stays exact.

`wetness_follows_arousal` (`{field_changed: arousal, direction: up}`) is **not** rewritten. It
continues to fire on the derived level's ordinal changing, which is the correct behaviour: wetness
tracks the visible arousal step, not every point of the gauge. This requires `apply_event()`'s
pass-start snapshot to capture the derived `arousal` ordinal, which it does — it snapshots the
readable field values, and `arousal` remains readable.

### 1.5 The gain formula

The magnitude a single act applies to a single participant:

```
gain = round( act.base_pleasure
              × sensitivity_multiplier( participant.sensitivity[ resolved_part ] )
              × shame_multiplier( participant.shame )
              × participant_count_multiplier( len(participants) ) )
```

All three multiplier tables live in `sexual_pleasure.yaml`.

**Sensitivity** — the payoff for repeated stimulation of one part:

| Level | Multiplier |
|---|---|
| 普通 | ×1.0 |
| 高 | ×1.4 |
| 極高 | ×1.8 |
| 敏感異常 | ×2.5 |

The existing rule `sensitivity_up_on_frequent_stimulation` already raises the sensitivity of the
body part named by the triggering event. Acts therefore train the parts they target, and a
well-trained part accelerates every later act on it. This build-up mechanic requires **no new rule**
— only that acts supply `part` in their event context, which the existing rule already demands
(it raises rather than defaulting when `part` is absent).

**Shame** — inhibition that inverts at the top:

| Level | Multiplier |
|---|---|
| 無 | ×1.0 |
| 輕微 | ×0.9 |
| 中等 | ×0.8 |
| 強烈 | ×0.65 |
| 成癮 | ×1.6 |

This curve carries the growth arc the whole system is built around. Bold acts raise shame through
the existing `shame_up_on_exposure_increase` and `shame_up_on_watched` rules, so early boldness
makes a character *worse* at it — a trough that must be pushed through before 成癮 flips inhibition
into amplification. Shame decays (`DECAY_CONFIG` interval 1800 s), so the trough is escapable rather
than a trap.

Monsters sit permanently at `無` (×1.0) because `SexualState.__init__` clamps their `shame` bounds
to a single point. They are neither inhibited nor ever amplified.

**Participant count** — a mild bonus for multi-participant acts, declared in the same table.

---

## 2. Counters (proposal `B2`)

Eleven cumulative lifetime counters, stored as counter traits in the same `sexual_traits`
`TraitHandler` as `climax_today`, each with exactly one sanctioned mutator method on `SexualState`,
following the `record_climax()` precedent. No rule and no effect handler may reach
`SexualState._traits` directly — the existing `sexual-transition-rulebook` requirement already
forbids that pattern for `climax_today` and its structural test already inspects
`sexual_transitions.py` for leading-underscore access.

| Axis | Counter | Incremented when |
|---|---|---|
| 獨處 | `自慰次數` | a solo act resolves |
| | `玩具使用次數` | an act declaring a toy resolves |
| 羞恥 | `露出次數` | an act that raises the actor's own `exposure` resolves |
| | `被觀看次數` | any act resolves with a third party present |
| 關係 | `雙人行為次數` | participants number exactly two (both sides increment) |
| | `多人行為次數` | participants number three or more (all increment) |
| 戰鬥 | `對敵行為次數` | an act resolves against a hostile target (actor side only) |
| | `忍耐次數` | the entity ends a round in the `極限` band without having entered `進行中` |
| 異種 | `異種行為次數` | an act resolves against a `Monster` |
| 高潮 | `高潮次數` | `climax_ends` fires |
| | `連續高潮次數` | `climax_extended` fires (once per extension turn) |

`露出次數` and `被觀看次數` are deliberately separate axes: one measures how much clothing came off,
the other whether anyone was watching. They gate different halves of the 羞恥線 and correspond to
the two distinct existing events `public_exposure` and `watched_during_activity`.

`忍耐次數` is the only counter earned by *not* doing something. It rewards holding at maximum
pleasure without tipping into climax — the most valuable and most dangerous position in combat — and
gates the control techniques that are the counterplay to over-using acts.

Each act declares **role-scoped** counter grants (`actor_counters` / `participant_counters`), so
performing an act and receiving it are recorded on different ledgers.

---

## 3. Climax Settlement (proposal `B3`)

### 3.1 The bug being fixed

`_VALID_CLIMAX_TRANSITIONS` permits `進行中 → 餘韻` only. The only rule producing that transition,
`climax_phase_ends_to_afterglow`, is conditioned on the `climax_ends` event. **No production code
emits `climax_ends`.** `DECAY_CONFIG["climax_phase"]` declares `only_from: 餘韻`, so decay cannot
reach `進行中` either. Combined with `climax_in_progress_locks_actions` (`actions_per_turn: 0`), an
entity reaching `進行中` is locked out of acting permanently.

The bug is currently unreachable — nothing raises `arousal` to `極限` — and becomes reachable the
moment acts exist. Fixing it is therefore load-bearing scope, not opportunistic cleanup.

### 3.2 The loop

```
pleasure reaches the 極限 band (≥85)
  → climax_gate                         未達 → 接近          [existing rule]
next stimulus while 接近
  → climax_phase_critical_point_to_in_progress   接近 → 進行中 [existing rule]
  → actions_per_turn: 0                                       [existing modifier]
end-of-round upkeep, entity in 進行中:
  ├ a qualifying extension stimulus landed this round
  │   → emit climax_extended                                  [new]
  │     ├ sp  -15..-10   (half of sp_cost_on_climax)
  │     ├ remain in 進行中 — another locked round
  │     └ 連續高潮次數 +1
  └ otherwise
      → emit climax_ends                                      [existing rules, newly emitted]
        ├ sp -30..-20                    sp_cost_on_climax
        ├ pleasure → 15                  arousal_reset_after_climax (rewritten §1.4)
        ├ wetness → 泛濫                 wetness_max_on_climax
        ├ climax_today +1                climax_today_increment_on_climax
        ├ 高潮次數 +1                     [new]
        └ climax_phase → 餘韻            climax_phase_ends_to_afterglow
餘韻, 300 s later → 未達                 [existing decay]
```

### 3.2a One added rule row: `penetrative_sex_with_male`

`sexual.yaml` ships `experience_lesbian_added` (`penetrative_sex_with_female` → `女女性愛`) with no
male-male counterpart. Overview D-12 makes same-sex intercourse a real branch in the act catalog, so
the asymmetry becomes visible: a female-female act would record an experience type while a male-male
act recorded nothing.

`B3` adds one row, `experience_gay_added` (`penetrative_sex_with_male` → `男男性愛`), because `B3`
already owns `sexual.yaml` and the catalog proposals are deliberately kept to pure data. It carries
its own `test_rule_<id>` function, as the shipped structural check
`test_every_rule_id_has_a_test()` requires.

Neither same-sex rule touches `virgin`; only `virginity_once`, conditioned on
`first_vaginal_penetration`, does. That separation is shipped behaviour and is not modified.

### 3.3 Emission sites

`climax_ends` and `climax_extended` are emitted from the **two call sites that already invoke
`decay_tick`**, so no scheduler and no new settlement stage is introduced:

- `world/rules/combat.py::_end_of_round_upkeep` — once per combat round (6 s).
- `world/rules/clock.py::_settle_buffs_and_decay` — out of combat, per settlement quantum.

This respects `sexual_state.py`'s existing constraint that it must not encode settlement ordering:
the emission lives at the call sites, which already own ordering, not inside the state module.

### 3.4 The extension trigger reads the *computed* gain

An entity in `進行中` sits at `pleasure` 85–100, so further gain is clamped at the ceiling and the
**applied delta is frequently zero**. The extension trigger therefore compares
`climax_extension_threshold` against the **computed** gain from §1.5, before clamping. Using the
applied delta would make the mechanic fire almost never.

Two pieces of transient state support this, both in `SexualState` and both covered by the `sexual`
rollback surface that the effect handlers declare:

- `climax_turns` — how many consecutive rounds the entity has been in `進行中`. Reset to 0 on
  leaving `進行中`.
- `pending_climax_extension` — an **integer count**, not a boolean. The pleasure effect handler sets
  it to 1 when a computed gain meets the threshold; upkeep consumes one and emits `climax_extended`.
  It is an integer so that 時姦 ([Divine Sexual Arts](2026-08-15-divine-sexual-arts-design.md) §2)
  can buy several rounds of extension with a single action without needing a field of its own.

### 3.5 No extension cap; a resist opening instead

Extension is **deliberately unbounded**. Indefinite suppression is a designed threat, not an
oversight.

The escape valve is a resist opening rather than a hard cap: for the first five climax turns the
resist contest short-circuits to compliance (an entity with `actions_per_turn: 0` cannot meaningfully
struggle), and **from the sixth climax turn onward the ordinary contest applies again**. A successful
resist wastes the actor's turn, no extension lands, upkeep emits `climax_ends`, and the chain breaks
into 餘韻 — which does not lock actions, so the target acts on the following round.

This composes with an existing modifier for free: an entity in `進行中` is necessarily in the `極限`
band, so `high_arousal_agility_accuracy_penalty`'s `agility: -20%` is already applied to the
effective agility the contest reads. "Someone mid-climax struggles to break free" is emergent, not
authored. Contest mechanics are specified in
[Act Resolution](2026-08-15-sexual-act-resolution-design.md) §4.

### 3.6 Soft-lock analysis

The self-limiting invariant (overview D-4 — every act also raises the actor's own gauge) breaks a
chain reliably when a **player** suppresses a monster: the player's own pleasure climbs until they
climax and lose their turn.

In the reverse direction it is weaker, because a monster's multipliers are flat (`shame` pinned at
`無` = ×1.0; sensitivity defaults to `普通` = ×1.0) while a trained player's are not. A monster could
in principle out-pace a player and suppress indefinitely.

Two things contain this in the current scope:

1. **Monster policy does not select sex acts.** `monster_behaviour_policy()` is explicitly out of
   scope for this document set (overview §6). Monsters are targets, not initiators, so the reverse
   direction is not reachable yet.
2. **The sixth-turn resist opening** bounds it probabilistically if and when monsters do initiate.

Any future proposal that lets monsters initiate must revisit this section before landing.

### 3.7 SP never goes negative

Both `sp_cost_on_climax` and the new half-cost extension write through `entity.traits.sp.current`,
whose `GaugeTrait` bound floors it. The `sexual-transition-rulebook` spec already pins this with a
scenario ("The stamina cost respects the gauge's own floor"). Climax at zero SP therefore continues
normally and costs nothing further — **no new logic is required** for the "SP may reach zero and the
climax still continues" requirement.

---

## 4. Combat Modifier Rows (proposal `B7`)

One new row in `combat_modifiers.yaml`, in the same table as poison, paralysis, and the existing two
sexual rows:

```yaml
- id: high_exposure_defense_penalty
  when: {field: exposure, gte: 高}
  then: {defense: "-20%"}
```

Exposure is the 羞恥線's self-inflicted cost. Its offensive payoff is delivered by act effects
(distraction debuffs applied to enemies), not by a modifier on the exposed entity, so one defensive
row is the complete modifier-table surface.

This proposal is independent of `B1`, `B2`, and `B3` — it reads `exposure`, which no part of this
document set changes — which is why it can be implemented in parallel batch 1.

---

## 5. Testing Strategy

- **Band table:** load-time validation of contiguity and coverage; a parametrised test asserting
  every `pleasure` value in `0..100` maps to the documented level, and that the boundary values
  (14/15, 34/35, 59/60, 84/85) fall on the documented side.
- **Derived arousal:** `arousal` remains comparable — `>=`, `<`, `==` against vocabulary strings and
  against another `OrderedLevelTrait` — and `combat_modifiers.yaml`'s existing arousal row still
  fires at the same threshold with no change to that file. This is the regression that protects
  §1.3.
- **Rewritten rules:** each of the four keeps its `test_rule_<id>` function, retargeted to
  `pleasure`. `test_field_kinds_covers_every_targetable_field()` and
  `test_every_rule_id_has_a_test()` must stay green throughout.
- **Counters:** one behaviour test per counter proving it increments on its trigger and on no other;
  a structural test that every counter has exactly one public mutator and that
  `sexual_transitions.py` contains no leading-underscore access to `SexualState` internals.
- **Climax loop:** an end-to-end test driving an entity from `平靜` through `極限`, `接近`, `進行中`,
  extension, and `climax_ends` to `餘韻` and back to `未達`, asserting the SP cost each step and that
  actions are locked exactly during `進行中`.
- **The dead-end regression:** a test asserting an entity that reaches `進行中` returns to `未達`
  without external intervention. This is the §3.1 bug, pinned.
- **Extension threshold:** a test proving the trigger fires on a computed gain that clamps to a zero
  applied delta — the §3.4 subtlety, pinned.
- **Resist opening:** a test proving climax turns 1–5 short-circuit to compliance and turn 6 rolls.
- **SP floor:** climax and extension at `sp = 0` leave `sp` at `0` and complete normally.
- All random deltas and contests take an injectable RNG, matching the existing `rng=` seam.
