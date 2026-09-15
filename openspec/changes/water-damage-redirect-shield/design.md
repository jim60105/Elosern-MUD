## Context

Delivers 水膜護身 (water_shield node) of `docs/lore/skill-trees/water.md`: "受擊時以 MP 代扣 30 % 的打擊量（代扣總量上限 30 MP，或持續 60 秒後失效）". Predecessor: `water-mp-depletion-reaction` shipped `world/rules/mp_flow.py` and the wave's MP-event semantics. Current damage math (`_handle_damage` in `world/rules/combat.py`): attack × multiplier × coefficient (pre-defense potency) → matched multiplier → − defense (or bypass) → devastation rider → floor → scale; one staged HP `PendingEffect` per target; step 7 projects HP for defeat entries. The dev-era `water_shield` buffs.yaml row is `bounds {target: defense, ceiling: 5}` — inert placeholder from `spell-catalog-water` (2026-08-13), to be wholesale removed here.

## Goals / Non-Goals

**Goals:** One authored divert profile that a damage-bearing strike consults at the existing post-defense point; the divert paid from the owner's gauge through the canonical writer inside the same atomic commit; a per-instance lifetime budget (cap) and bounded duration both enforced by data.

**Non-Goals:** No new damage stages, no new scheduler, no absorb-then-release pool, no healing, no MP-shield-vs-transfer interaction rules beyond the writer, no catalog node data (change 4), no replacement of `bounds` defense buffs generally (earth/ice/light wards keep theirs), no water-key branch in generic code, no data-contract tests.

## Decisions

### D1 — Profile shape and where it lives
`modifiers: {divert: {target: mp, fraction: 0.3, cap: 30}}` on a normal duration buff. Loader validation is fail-closed like `rate`: `target` ∈ `GAUGE_KEYS`, `fraction` finite in (0,1], `cap` positive int, duration required (a permanent divert with a cap is meaningless — cap exhaustion would silently end it; the loader rejects `duration: null` on divert rows). `divert` coexists with `rate`/`bounds`/`decay` per the widened vocabulary; a row declaring both `divert` and `recovery` is refused (recovery stays hp-only per its own rule). The profile is read by the damage owner (combat.py), mirroring how `bounds` is read by the traits surface and `rate` by the tick — no buff-engine callback into damage.

### D2 — Placement in the formula and the accounting
Divert runs AFTER the full authored amount pipeline (coefficient, conditional multiplier, defense/bypass, devastation rider, scale) and BEFORE staging: `amount` is what a hit would cost the owner; the shield then converts part of it. `diverted = min(round(amount × fraction), cap − consumed, owner_current_mp)`; staged HP amount becomes `amount − diverted` (floor semantics preserved: a fully diverted hit still lands ≥ 0 but never negative); one staged `PendingEffect` on the payer's gauge routes through `apply_mp_change(-diverted, source=<owner of shield? no: source = the buff's grant-time source, tier carried>)` — attribution per the wave: the divert is the shield owner's own MP decrease caused by the shield's author, so source_skill is the casting source persisted at grant time (same cache field `_handle_buff_apply` already persists for damaging rates), tier the grant-time tier. The consumed budget lives in the buff instance cache (`divert_consumed`) updated at COMMIT time inside the same staged effect, so a rolled-back hit restores it; a REFRESH replaces duration but KEEPS consumed progress only if the re-applier omits budget data (same retain-vs-replace posture as `source_pk` reapplication) — a fresh cast's `apply_buff` resets the instance, which matches "護的是人" per-cast semantics: each cast buys a new 30-MP film.

### D3 — Selection among multiple active diverts
Deterministic, load-order-independent: when several divert profiles are active, apply them in a stable order — by `(definition key ascending)` — each seeing the residual after the previous (fraction of the RESIDUAL, cap vs own budget). Two synthetic profiles of different keys prove the ordering; authored water ships exactly one. This rule replaces any "first wins" ambiguity that would make combat nondeterministic.

### D4 — Interaction with the wave's MP fact
A divert that empties the payer's MP crosses zero via a decrease → the canonical writer dispatches `mp_zero` with the persisted grant-time source. Whether that ever punishes is rule-layer data (water's suffocation row is qualified to the drowning node only, so a shield-payer never suffocates from its own shield). A miss/zero-amount hit stages nothing and consumes nothing; `hp_loss` feedback sees `amount − diverted` only (no phantom HP loss); step 7's projected-HP defeat logic reads the reduced staged amount unchanged.

### D5 — Replace the inert row without alias
Delete the `water_shield` bounds buff row and its display entry in this change (the node's real binding ships as `water_film` here; change 4 re-points the registry row's `buff_apply:` from the deleted key to `water_film` — the catalog change owns the registry line). The status display entry moves key (`水膜` label kept). **Accepted window:** between this change and the catalog change, master carries the old registry row still binding `buff_apply:water_shield` while the buff row is gone — casting the old 水盾術 in that window rejects at staging. Zero users, two commits apart; explicitly accepted rather than papered with an alias. `test_buffs.py`'s dev-era `test_buff_water_shield` shape test is updated to the new synthetic-shape posture (per-key authored-row correspondence tests were already retired in the light wave; only what exists stays truthful).

### D6 — Interface ownership
| Interface | Owner | Consumers |
|---|---|---|
| `divert` profile (loader validation + cache budget) | this change | catalog data (水膜護身's row), any future resource-divert node |
| divert stage in the damage pipeline (ordered, multi-profile rule) | this change | none yet; light's stages run strictly before it |
| `water_film` buff key | this change | change 4 registry binding `buff_apply:water_film` |

## Risks / Trade-offs

- Divert reading the payer's stored MP at STAGE time vs commit time: choose stage-time clamp plus commit-time writer clamp — the writer's own clamp is the correctness backstop if MP moved mid-commit, and the staged cache-budget update stays consistent because it derives from the writer's actual delta.
- Fraction-of-residual vs fraction-of-original for stacked diverts is a genuine design point; residual-order is chosen so totals can never exceed the incoming amount (a fraction-of-original stack could over-divert past 100 %).
- The 30-MP cap is per cast lifetime, not per 60 s window — the duration row and the cap bound the same instance, matching both lore failure clauses ("上限 30 MP，或持續 60 秒後失效").

## Migration Plan

Loader → damage stage → rows/display swap → synthetic tests, task-grouped. Registry binding changes only in the catalog change. No aliases.

## Verification contract

Synthetic-only behavior tests that fail on plausible bugs: divert applied pre-defense instead of post (compare identical rolls with nonzero defense), cap double-counted after rollback, refresh wiping consumed budget when it should retain (per D2's posture) or vice versa, missed hit consuming budget, `hp_loss` feedback seeing pre-divert amount, multi-profile order nondeterminism, permanent-divert authoring accepted, divert bypassing the canonical writer (assert the depletion event fires with grant-time attribution). Focused invocation in tasks.md; `MUD_TEST_SETTINGS=1` via tool env.
