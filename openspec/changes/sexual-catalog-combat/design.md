## Context

`world/skills/sexual_acts/combat.py` ships one seed row in `COMBAT_ACTS` (`sexual-act-seeds`,
already merged): `combat_tease` (挑逗, 腰腹/腰腹, `actor_pleasure_ratio=0.4`, `base_pleasure=7`,
`resistible=True`, `actor_counters=("hostile_act_count",)`, `participant_counters=()`). This is the
pattern every act in this proposal reuses: the aggressor's own `hostile_act_count` grows; the hostile
target is never credited a counter for having been targeted, unlike the symmetric crediting
`sexual-catalog-partner` (C4) uses for consensual two-party acts.

`sexual-act-catalog-design.md` §5 specifies ten 戰鬥線 acts total (the seed plus nine more). This
proposal builds eight of the nine; 搾取 (Tier 4) is deferred — D-2 below is the reason, in the same
"name the exact code, don't route around it" style established by `sexual-catalog-solo`,
`sexual-catalog-shame`, and `sexual-catalog-partner`'s own deferrals.

This document also corrects a design-reasoning mistake `sexual-catalog-partner`'s rubber-duck review
caught: an earlier draft of *that* proposal claimed a fixed `base_pleasure`/`ratio` choice could
guarantee neither of two same-tier acts on different body parts dominates the other. It cannot, once
per-body-part `sensitivity` training diverges with play history (§1.1 of the source catalog). D-3
below applies that correction from the start rather than making the same claim and retracting it.

## Goals / Non-Goals

**Goals:**
- Ship the eight buildable 戰鬥線 acts across Tiers 1, 2, 3, and 5, each a plain
  `SexualActDef`/`SkillDef` pair through `_act_family("戰鬥", ...)`.
- Keep every act's `unlock` gate readable directly off `hostile_act_count`/`climax_count`/
  `climax_extension_count`, three counters already wired by prior proposals.
- Preserve the shipped seed's asymmetric counter-crediting convention (`actor_counters` only,
  `participant_counters=()`) for all eight new acts.
- Tune Tier 3/5's two extension-capable acts so their target-side gain reliably clears
  `climax_extension_threshold` even in the worst realistic case, not merely on average.
- Leave `world/rules/action.py`, `_builder.py`, `__init__.py`, every other line module, and
  `world/rules/rulebook/combat_modifiers.yaml` byte-for-byte unchanged.

**Non-Goals:**
- Building 搾取 (D-2) — named, disclosed, and left for a future proposal.
- Wiring `resistible=True` to an actual resist-contest call site, matching every prior catalog
  proposal's disclosure that `resistible` remains declarative metadata until a wiring proposal lands.
- Authoring a new combat-modifier row. 魅惑 and 束縛愛撫 reuse
  `high_arousal_agility_accuracy_penalty` exactly as shipped.

## Decisions

### D-1: The eight acts, exactly as registered

| Key | Label | Tier | Unlock | Actor=Target part | Base | Ratio |
|---|---|---|---|---|---|---|
| `combat_tease_whisper` | 挑逗·耳語 | 1 | `hostile_act_count: 5` | 耳朵 | 10 | 0.4 |
| `combat_tease_touch` | 挑逗·觸碰 | 1 | `hostile_act_count: 5` | 腰腹 | 11 | 0.4 |
| `combat_charm` | 魅惑 | 2 | `hostile_act_count: 20` | 頸項 | 20 | 0.4 |
| `combat_bind_caress` | 束縛愛撫 | 2 | `hostile_act_count: 20` | 大腿 | 20 | 0.4 |
| `combat_forced_pleasure` | 強制快感 | 2 | `hostile_act_count: 20` | 私處 | 24 | 0.4 |
| `combat_forced_climax` | 強制絕頂 | 3 | `hostile:40, climax:30` | 私處 | 30 | 0.4 |
| `combat_relentless_torment` | 連續責め | 3 | `hostile:40, climax:30` | 臀部 | 30 | 0.6 |
| `combat_climax_domination` | 絕頂支配 | 5 | `hostile:80, climax_ext:30` | 私處 (AREA) | 30 | 0.4 |

Every act declares `actor_counters=("hostile_act_count",)`, `participant_counters=()`,
`sexual_events=()`, `resistible=True`. `combat_climax_domination` is the only `TargetSpec.AREA` row;
every other act is `TargetSpec.SINGLE`.

### D-2: 搾取 is deferred — no cross-entity resource-transfer effect exists

The source catalog describes 搾取 (`unlock={"hostile_act_count": 60, "climax_extension_count": 10}`)
as converting "a share of the target's climax SP loss" into a gain for the actor. Every effect a
`SexualActDef` can express resolves through exactly three handlers in `world/rules/action.py`:
`_handle_pleasure_effect` (adds `pleasure` to one participant, scaled by that participant's own
ratio), `_handle_sexual_counter_effect` (increments a named lifetime counter on one or more
participants), and `_handle_sexual_event` (fires a `sexual.yaml` rule by event name). None of the
three reads or writes a resource belonging to a *different* participant than the one it applies to —
there is no "read entity A's SP delta, credit a fraction of it to entity B" primitive anywhere in the
schema, and `SP` itself (a stamina/resource trait) is not a field either `SexualActDef` or
`compute_pleasure_gain` ever touches.

Building 搾取 needs a new effect shape — a transfer, not a gain — which is new capability for
`sexual-act-effects` to define, not something a catalog proposal can express by choosing different
row values. This is the same class of gap `sexual-catalog-solo` found for its three deferred
pleasure-*reduction* acts (`_act_family()` only ever adds; nothing subtracts): a missing verb in the
schema, not a missing number.

**What a follow-up needs:** a fourth effect shape (working name: `sexual_transfer:<key>`) that reads
one participant's resource delta from the same cast and credits a configured fraction to another
participant, landing in `sexual-act-effects` or a dedicated successor capability.

### D-3: No fixed base_pleasure/ratio choice claims dominance-freedom across different body parts — only same-part, same-tier pairs are checked

Every pair of same-tier acts in this catalog that share a body part *and* an unlock gate would be a
genuine "no legitimate reason to pick the worse one" problem if left unbalanced — that is the failure
mode `sexual-catalog-solo`'s rubber-duck review caught in `solo_bound_masturbation`. This proposal has
exactly one such pair, and it is deliberately avoided by construction: Tier 3's two acts
(`combat_forced_climax`, `combat_relentless_torment`) share an unlock gate but declare **different**
body parts (私處 vs 臀部), so — per `sexual-catalog-partner`'s corrected D-4 reasoning — their
relative value for any given character legitimately depends on that character's per-part
`sensitivity` training, which is the intended mechanic (§1.1), not a defect to engineer away with
numbers. Tier 2's three acts (魅惑/束縛愛撫/強制快感) are likewise all on different parts (頸項/大腿/
私處), for the same reason.

`combat_relentless_torment`'s higher `actor_pleasure_ratio` (0.6 vs `combat_forced_climax`'s 0.4,
identical `base_pleasure=30`) is the source catalog's "stronger self-gauge cost" flavour — the
intended narrative reading is that it costs the actor more. That reading is **not** a provable
numeric guarantee, and this document does not claim it as one: `combat_forced_climax`'s actor-side
gain uses the actor's 私處 sensitivity while `combat_relentless_torment`'s uses their 臀部
sensitivity — two independently-trained values (§1.1). A character with high 私處 sensitivity and
baseline 臀部 sensitivity can make `combat_forced_climax` cost *more*, not less
(e.g. `round(30×0.4×2.5×1.0×1.1)=33` against `round(30×0.6×1.0×1.0×1.1)=20`) — the opposite of the
flavour text's implication. This is exactly the same kind of claim `sexual-catalog-partner`'s D-4
warns against making for a different-body-part pair, restated here for the same reason: no fixed
`base_pleasure`/`ratio` choice can guarantee a cost ordering across two different body parts once
per-part sensitivity diverges. The ratio difference stands as flavour, not as an engineered
guarantee.

No pair in this proposal shares both a body part and an unlock tier, so the stricter same-part
dominance check (the one `_act_family()`'s design actually lets a proposal make provable) does not
apply anywhere in this proposal.

**Cross-tier same-body-part chains exist and are intentional tiered progression**, per
`sexual-catalog-partner`'s D-4 precedent, disclosed explicitly here rather than left implicit: 腰腹
(seed `combat_tease` → Tier 1 `combat_tease_touch`) and 私處 (Tier 2 `combat_forced_pleasure` →
Tier 3 `combat_forced_climax` → Tier 5 `combat_climax_domination`, a three-link chain) each have a
strictly-higher-`base_pleasure` successor once unlocked, with no compensating downside. Unlike the
sibling proposal's single-counter chains, this line's later links gate on compound thresholds
(`climax_count`, `climax_extension_count`) that progress independently of `hostile_act_count` — see
D-5 — so a character can hold `hostile_act_count >= 80` indefinitely without ever unlocking
`combat_climax_domination` if their `climax_count`/`climax_extension_count` stay low. "Outgrows the
earlier act" is not a guaranteed eventual outcome here the way a single-counter chain would make it;
it depends on the player pursuing climax-extension play specifically, not just hostile-act volume.

### D-4: Tier 3 and Tier 5's four extension-capable rows are tuned to clear the extension threshold even in the worst case

`_apply_pleasure_gain` (`action.py`) stages a climax extension when a participant already in `進行中`
receives `gain >= climax_extension_threshold` (`20`, `sexual_act_effects.yaml`), where `gain` is
`compute_pleasure_gain`'s full output — `round(base_pleasure × ratio × sensitivity_mult ×
shame_mult × crowd_mult)` — evaluated for the **target** (`ratio` fixed at `1.0` for any non-actor
participant). The lowest realistic multiplier combination a target can present is `普通` sensitivity
(`sensitivity_mult=1.0`, the floor — sensitivity never goes below baseline) and `強烈` shame
(`shame_mult=0.65`, the lowest value below `成癮`'s outlier `1.6`); `crowd_mult` is `1.1` at the
two-participant floor every `TargetSpec.SINGLE` act reaches, or higher for `combat_climax_domination`'s
`AREA` targets.

At `base_pleasure=30`, the worst case is `round(30 × 1.0 × 1.0 × 0.65 × 1.1) = round(21.45) = 21`,
which clears the threshold (`21 >= 20`) with a one-point margin even under the least favourable
inputs the live multiplier tables can produce. `combat_forced_climax`, `combat_relentless_torment`,
and `combat_climax_domination` all share this `base_pleasure=30`, so all three inherit the same
worst-case guarantee.

### D-5: Dependency-surface assumptions this proposal reads, not writes

- `sexual-counters` (B2, merged): `hostile_act_count` and its sole mutator (`record_hostile_act`) are
  unchanged.
- `climax_count` and `climax_extension_count` are both credited exclusively by the climax-settlement
  clock's own mutator calls, never by an act's `actor_counters` — Tier 3 and Tier 5's compound gates
  read them but no act in this proposal writes either directly, matching the pattern every prior
  catalog proposal established for counters no act itself can credit.
- `world/rules/rulebook/combat_modifiers.yaml`'s `high_arousal_agility_accuracy_penalty` row
  (`{field: arousal, gte: 高度} → {agility: "-20%", accuracy: -15}`) is unchanged; 魅惑/束縛愛撫's
  reuse depends on it firing exactly as shipped.
- `sexual_act_effects.yaml`'s `climax_extension_threshold: 20` and `participant_multipliers` ladder
  (`{"1": 1.0, "2": 1.1, "3+": 1.2}`) are unchanged; D-4's worst-case arithmetic depends on both.

## Risks / Trade-offs

- **[Risk]** 魅惑/束縛愛撫's "accuracy/agility debuff" flavour is delivered entirely by an existing,
  unrelated combat-modifier row keyed off absolute `arousal` level, not off casting the act itself —
  a single cast of either act may not by itself push a target from below `高度` to at/above it,
  meaning the debuff sometimes doesn't manifest from one cast in isolation. → **Mitigation:** this is
  the same shape `sexual-catalog-shame`'s 挑釁凝視 already shipped and disclosed; the proposal
  advertises the debuff as an emergent consequence of raising pleasure toward/into `高度` (which both
  acts' `base_pleasure=20` meaningfully contributes to across a fight), not a guaranteed single-cast
  trigger.
- **[Risk]** Deferring 搾取 leaves Tier 4 of the source catalog's five-tier 戰鬥線 completely
  unrepresented in `COMBAT_ACTS` — the line jumps from Tier 3 straight to Tier 5. →
  **Mitigation:** D-2 states exactly what a follow-up proposal needs; `combat_climax_domination`
  (Tier 5)'s own unlock gate (`hostile_act_count: 80, climax_extension_count: 30`) does not depend on
  搾取 ever existing, so the gap doesn't block Tier 5's own progression.
- **[Risk]** `combat_climax_domination` (`TargetSpec.AREA`) can reach `participant_count` values above
  2, raising `crowd_mult` to `1.2` — this only strengthens D-4's worst-case guarantee (more
  multiplier, not less), so it introduces no new risk to the threshold-clearing claim.

## Migration Plan

Pure content addition; no data migration. `COMBAT_ACTS` grows from 1 row to 9; every existing
consumer (`SEXUAL_ACT_REGISTRY`, `unlocked_act_keys_for`, the combat panel's category grouping) reads
the tuple structurally and requires no change.

## Open Questions

None — 搾取 is a resolved deferral (D-2), not an open question.
