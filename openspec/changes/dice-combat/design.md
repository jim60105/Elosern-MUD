## Context

This is roadmap item #9 (design doc §11), depending on change 8 (`action-resolver`). Change 8 built
`ActionResolver.resolve()`, the eight-step pipeline, `EventLog`, the `ActionContext` protocol, and an
open effect-handler registry — but left three things for this change to close, by name:

1. **`damage:*` rejects with `UNKNOWN_EFFECT_ID`.** Change 8's own Non-Goals state this is "the
   correct state until change 9 registers a handler for that prefix, not a bug this change needs to
   work around." No skill whose `effects` list contains a `damage:*`-prefixed ID (`fire_ball`,
   `wind_blade`, and every weapon-art skill in change 5's seed set) can resolve until this change lands.
2. **`BattlefieldActionContext` is declared, not built.** Change 8's `ActionContext` protocol
   (`battlefield`, `is_present()`, `relation_to()`, `is_in_range()`) has one concrete implementation
   today, `RoomActionContext` (out-of-combat). This change supplies the second.
3. **`is_in_range()` is named, explicitly, as this change's job** ("Owner: change 9 (`dice-combat`)"),
   with the caveat that change 12 (`map-anchor-grid`) is what eventually supplies real coordinates.
   Change 8's own `RoomActionContext.is_in_range()` returns `True` unconditionally and says so
   honestly; this change inherits that seam rather than rediscovering it.

**The calibration problem.** Design doc §6.3 fixes the to-hit formula as:

```
to-hit   d100 + attacker agility   vs   60 + defender agility
```

The `60` was chosen when the design doc's own author believed human physical stats sat in the 60-90
range. Changes 2 and 3 have since pinned down the real bands (`world/lore/races.py`,
`STATIC_TIER_REGISTRY`): human 1-22 (elite tier 7-14, e.g. Lidzia 8/9/7), elf 70-95 (e.g. Yuka
88/92/90, Elosia 70/70/95), monster tiers 3-8/12-20/22-35/60-150+. Because `rulebook/combat.yaml` is
this change's own file, re-deriving that constant against the real numbers — rather than carrying it
forward unexamined — is this change's job, not a future balance pass's.

No code exists yet for this change's scope. `world/rules/` currently holds `traits.py` (change 3),
`rulebook/schema.py`/`combat_modifiers.py`/`buffs.py` (change 6), and `action.py`/`targeting.py`/
`event_log.py` (change 8, once landed). Nothing named `dice.py` or `combat.py` exists, and
`rulebook/combat.yaml` does not exist.

## Goals / Non-Goals

**Goals:**
- `world/rules/dice.py`: a thin, seedable wrapper over `evennia.contrib.rpg.dice.roll()` for the d100
  roller (§4: "Use directly").
- **Recalibrate the to-hit formula** against changes 2/3's real stat bands, with the reasoning recorded
  in `rulebook/combat.yaml` and this document, so a future reader finds a calibrated decision, not an
  unexamined constant.
- `effective_power(entity) = f(atk_phys, agility, defense, magic_level, hp)`, reading every stat
  through change 5's `SkillHandler.effective_value()`, for change 10's overwhelm threshold to consume.
- Register `damage:*` effect handlers into change 8's registry via `register_effect_handler()`,
  declaring `surfaces=frozenset({"traits"})`.
- `world/rules/combat.py`: `Battlefield`, `BattlefieldActionContext` (satisfying change 8's
  `ActionContext` protocol), initiative ordering, the turn loop (including per-round buff ticks and a
  self-arming sexual-decay hook), and end-of-encounter detection.
- A real, if coarse, `is_in_range()` for the battlefield — engaged-vs-not, not coordinates.
- Round-based time reporting (`rounds × 6s`) as a plain integer, never a `WorldClock` call.
- Fixed-seed golden tests: one normal (same-tier) exchange, one lopsided (cross-race) exchange.

**Non-Goals:**
- **No overwhelm threshold, single-shot resolution, or `EventLog` compression** — change 10's job
  entirely. This change builds `effective_power()` as a pure function change 10 calls; it does not
  itself decide what ratio counts as "overwhelming" or short-circuit any fight.
- **No world clock, scheduled events, or settlement order** — change 11's job. `run_battle()` returns
  a plain `total_seconds: int`; nothing in this change calls `WorldClock.advance()` or assumes a
  settlement order relative to regen/sexual decay outside combat's own per-round upkeep.
- **No Narrator or LLM involvement** — change 18's job. This change only produces `EventLog`s using
  change 8's existing shape plus two new `kind` values (`"roll"`, `"damage"`, per change 8's own
  stated expectation) and one combat-specific bookkeeping kind (`"action_skipped"`).
- **No coordinate-based positional combat.** Change 12 (`map-anchor-grid`) has not landed; this
  change's `is_in_range()` is explicitly scoped to what a coordinate-free battlefield roster can
  express (see D-7), not a distance model.
- **No AI behaviour tree.** `Monster.behaviour_tree` (change 3's declared, unbuilt seam) does not
  exist. This change's turn loop needs *some* action for a non-player combatant to take each round; it
  supplies a minimal, explicitly-labeled placeholder policy, not a real AI (see D-9).
- **No changes to `SkillDef`, `ActionResolver`, `targeting.py`, or `event_log.py`.** This change adds
  no field to change 5's `SkillDef` and no branch to change 8's resolver/targeting modules — every
  combat-specific behavior (agility/accuracy modifier interpretation, `actions_per_turn` gating, the
  to-hit/damage roll) lives in `world/rules/combat.py`, satisfying change 8's own no-combat-branching
  tripwire by construction (this change never touches the scanned files).
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users, and `world/rules/dice.py`/`combat.py`/`rulebook/combat.yaml` do not exist yet.

## Decisions

### D-1. `world/rules/dice.py`: a seedable wrapper, nothing more.

```python
# world/rules/dice.py
"""d100 roller for this project's linear combat math. Wraps
evennia.contrib.rpg.dice.roll() directly (design doc §4: "Use directly" —
this is NOT evadventure's d20 roller, which is reference-only per §4).
"""
from evennia.contrib.rpg.dice import roll as _evennia_roll

def roll_d100() -> int:
    """Returns a single d100 result in [1, 100]. Delegates to the contrib
    roller (`roll("1d100")` or the equivalent (1, 100) call form — exact
    call signature flagged for implementer verification against the
    installed Evennia 6.1.0 package, consistent with this project's
    established discipline for every other contrib-API assumption)."""
    ...
```

**Determinism (§10).** `evennia.contrib.rpg.dice.roll()` is expected to accept a way to inject a
seeded RNG (a `random_generator` argument or equivalent — flagged for implementer verification, since
this design was authored without a locally installed Evennia package to confirm the exact signature).
This module's own tests seed Python's `random` module directly (`random.seed(N)`) around calls to
`roll_d100()` if the contrib has no first-class seed parameter, rather than inventing a parallel RNG —
the golden tests (D-10) need *a* reproducible sequence, not necessarily one routed through a contrib
parameter that may not exist.

### D-2. Recalibrating the to-hit formula: keep the linear-difference shape, replace `60` with `51`.

**Step 1 — state the formula precisely.** "d100 + attacker agility ≥ 60 + defender agility" is a hit.
Rearranged: hit iff `roll ≥ 60 + defender_agility − attacker_agility`. Let `Δ = attacker_agility −
defender_agility` (the attacker's relative agility advantage) and `C` be the defender-side constant
(currently 60). Since `roll` is uniform over the 100 integers `1..100`:

```
hit_rate(Δ) = clamp( (101 − C + Δ) / 100 ,  0.0 ,  1.0 )
```

This is the whole formula's behavior in one line: **only the difference in agility matters, never
either side's absolute value.** This is the first thing worth naming explicitly, because it means the
original mistaken belief ("human agility sits at 60-90") could not, by itself, have miscalibrated
*same-race* combat — a duel between two humans depends only on their agility *gap* (typically 2-15
points within one `STATIC_TIER_REGISTRY` tier), regardless of whether the species baseline is 9 or 90.
What the constant *does* control is two things that have nothing to do with absolute stat magnitude:

- **The hit rate at exact parity** (`Δ = 0`): `(101 − C)/100`. For `C = 60`, that's **41%**.
- **The saturation width** — how large `Δ` must be before the formula pins to a guaranteed hit or
  guaranteed miss. For `C = 60`: guaranteed miss at `Δ ≤ −41`, guaranteed hit at `Δ ≥ 59`. This is an
  **asymmetric** 41-vs-59 window with no design rationale behind the asymmetry — it falls out of `C`
  not being 50.

**Step 2 — compute the seven required matchups at the current `C = 60`**, using the exact reference
values `STATIC_TIER_REGISTRY`/`world_info.md` supply (Lidzia agility 9 for human elite, Yuka agility
92 and Elosia agility 70 for the two elf reference points, task-specified bounds for the others):

| Matchup | Δ range | hit_rate range (attacker → defender) |
|---|---|---|
| human elite (9) vs human elite (9) | 0 | **41%** |
| human novice (6) vs low monster (3–8) | +3 to −2 | 39%–44% |
| human elite (9) vs mid monster (12–20) | −3 to −11 | 30%–38% |
| human sword-master (18–22) vs high monster (22–35) | −17 to 0 | 24%–41% |
| elf (Yuka, 92) vs human elite (9) | +83 | **100%** (saturated — `Δ ≥ 59`) |
| human elite (9) vs elf (Yuka, 92) | −83 | **0%** (saturated — `Δ ≤ −41`) |
| elf (Yuka, 92) vs elf (Elosia, 70) | +22 | 63% (reverse direction: 19%) |

**Step 3 — diagnose what this actually shows.** Every same-tier or adjacent-tier matchup (human vs
human, human vs a monster tier one step up, elf vs elf) lands in a **19%–63% band** — none of them are
degenerate, all of them are "interesting dice." Every cross-race matchup (human vs elf) is fully
saturated, at `Δ = ±83`, which vastly exceeds either saturation bound (`−41`/`+59`). **This means the
formula's *qualitative* behavior — genuinely uncertain within a race/tier, mathematically settled
across the elf/human divide — already matches the design intent, and it does so for a structural
reason that has nothing to do with the mistaken 60-90 belief**: `world_info.md`'s own "world-common
absolute scale" puts the human/elf agility gap at 48-94 points (human ceiling 22 to elf floor 70, up to
human floor 1 to elf-prodigy territory above 95), while every within-race or adjacent-tier gap this
change's seven matchups exercise is 30 points or less. A d100 roll has 100 discrete outcomes; a gap
that large saturates against *any* constant in a plausible range, and a gap that small never fully
saturates against any constant in a plausible range either. The constant was never actually coupled to
the wrong belief in the way the belief implied — **the belief was wrong, but it happened not to be
load-bearing for whether the formula works**, because the formula was always difference-based, not
scale-based.

**Step 4 — what *is* genuinely wrong, and the fix.** The specific value `60` produces two artifacts
with no remaining justification once the "human is 60-90" premise is gone:
1. A **41% parity hit rate** — equally matched combatants miss more often than not, for no stated
   reason. There is nothing in `world_info.md`, the design doc, or any lore registry that says an
   evenly-matched duel should lean toward missing.
2. An **asymmetric saturation window** (`−41` / `+59`) — an attacker's own agility edge saturates to a
   guaranteed hit 18 points "sooner" than a defender's agility edge saturates to a guaranteed miss.
   Nothing in the setting motivates attackers being structurally favored this way; it is purely an
   artifact of `60 ≠ 50`.

**Decision: replace `60` with `51`**, keeping the identical shape and comparator
(`roll + attacker_agility ≥ 51 + defender_agility`). `51`, not `50`, because the roll space `1..100` is
inclusive and even-cardinality: `hit_rate(0) = (101 − C)/100`, which equals exactly `0.50` only at
`C = 51` (at `C = 50` parity would be 51%, a smaller but still real asymmetry). This yields:

```
hit_rate(Δ) = clamp( (50 + Δ) / 100 ,  0.0 ,  1.0 )
```

— exact 50% at parity, and **symmetric** saturation at `Δ ≤ −50` (guaranteed miss) / `Δ ≥ +50`
(guaranteed hit). Recomputing the seven matchups at `C = 51`:

| Matchup | Δ range | hit_rate range |
|---|---|---|
| human elite (9) vs human elite (9) | 0 | **50%** |
| human novice (6) vs low monster (3–8) | +3 to −2 | 48%–53% |
| human elite (9) vs mid monster (12–20) | −3 to −11 | 39%–47% |
| human sword-master (18–22) vs high monster (22–35) | −17 to 0 | 33%–50% |
| elf (Yuka, 92) vs human elite (9) | +83 | **100%** (saturated) |
| human elite (9) vs elf (Yuka, 92) | −83 | **0%** (saturated) |
| elf (Yuka, 92) vs elf (Elosia, 70) | +22 | 72% (reverse: 28%) |

Same-tier and adjacent-tier fights now center on a genuine coin flip and range 28%–53% depending on the
real agility gap; the two racial matchups remain fully, deliberately absolute — this is now a
calibrated consequence (parity is a fair fight; a 48+ point gap, which is smaller than the smallest
possible human-elf gap in the source bands, is unwinnable in either direction) rather than an
inherited artifact.

**No natural-roll auto-hit/auto-fumble override.** Considered and rejected: a common percentile-dice
convention is "roll 100 always hits, roll 1 always misses," regardless of the threshold. Adding it here
would reintroduce exactly the kind of accident this recalibration exists to remove — a 1% chance for a
human to land a hit on an elf (or for an elf to whiff against a human) that has no basis in
`world_info.md` and directly contradicts the design doc's own stated acceptance that some matchups
should be mathematically absolute. A natural `100` still matters for damage magnitude (D-3), which is a
separate axis from whether the attack landed at all.

**Where this lives.** `rulebook/combat.yaml`:

```yaml
to_hit:
  defender_constant: 51   # see design.md D-2 for the full derivation. NOT 50 or 60 — 51 is what
                            # makes exact agility parity a genuine 50% hit chance given d100's
                            # inclusive 1..100 range. Do not "simplify" this back to a round 50.
```

### D-3. Damage: `(effective atk_phys × roll multiplier) − effective defense, floor 1`; roll multiplier
is margin-of-success banded, with a natural-100 critical override that affects magnitude only.

Design doc §6.3 names the shape but not what "roll multiplier" means. This change defines it as a
function of **margin of success** — how far the (already-computed) attack score cleared the to-hit
threshold — plus one special case for a natural roll of 100:

```
margin = (roll + attacker_agility + accuracy_modifier) − (51 + defender_agility)   # only meaningful
                                                                                       # when margin ≥ 0
                                                                                       # (a hit occurred)
roll_multiplier =
    2.0   if the raw, unmodified d100 roll == 100          (critical — magnitude only, never
                                                              overrides a miss determined above)
    1.5   elif margin ≥ 40                                  (solid hit)
    1.0   otherwise                                          (bare hit)
```

```yaml
# rulebook/combat.yaml
damage:
  crit_multiplier: 2.0
  solid_hit_margin: 40
  solid_hit_multiplier: 1.5
  base_multiplier: 1.0
  floor: 1
```

These specific numbers (`40`, `1.5`, `2.0`) are this change's own invented placeholders, sourced from
no `world_info.md` table — flagged explicitly for change 10/16's eventual balance pass, the identical
disclosure discipline changes 5 (D-4) and 6 (D-3) already used for their own invented numbers. The
*shape* (margin-banded, crit-on-natural-100-but-magnitude-only) is this change's real contribution;
the exact band edges are not.

`effective defense` and `effective atk_phys`/`magic_level` are read through change 5's
`SkillHandler.effective_value()`, never `entity.traits.<key>.value` directly — this is what makes a
body-enhancement skill's ×100/×1000 apply at resolution time rather than needing to be baked into a
stored stat (hard requirement 3).

### D-4. `effective_power(entity) = (atk_phys + agility + defense + magic_level) × max_hp`, every stat
read through `effective_value()`, `hp` read as the entity's **race/tier maximum**, not current.

Design doc §5.1 is explicit about why `hp` must be an input: elves scale ~100× in vital pools but only
~10× in static combat stats, so a stat-only ratio would show "only" a 10× gap and fail to flag an
elf-vs-human fight as the mismatch it actually is — the human's own tiny hp pool means it dies in one
or two hits regardless of how the stat ratio alone reads.

```python
def effective_power(entity) -> float:
    stats = sum(
        entity.skills.effective_value(key)
        for key in ("atk_phys", "agility", "defense", "magic_level")
    )
    max_hp = max(entity.traits.hp.max, 0)
    return stats * max_hp
```

**Worked check against the task's own reference points**, confirming the function does what §5.1
requires:

| Entity | stats sum (via `effective_value`) | hp (max) | `effective_power` |
|---|---|---|---|
| human elite (Lidzia 8/9/7, magic ~40) | 64 | 120 | 7,680 |
| elf (Yuka 88/92/90, magic ~250) | 520 | 10,000 | 5,200,000 |
| **ratio (elf / human)** | | | **≈ 677** |
| mid-tier monster (~16/16/16, magic 0) | 48 | 300 | 14,400 |
| **ratio (mid monster / human elite)** | | | **≈ 1.9** |
| high-tier monster (~28/28/28, magic 0) | 84 | 550 | 46,200 |
| human sword-master (~20/20/20, magic 0, hp 150) | 60 | 150 | 9,000 |
| **ratio (high monster / sword-master)** | | | **≈ 5.1** |

The elf/human ratio (≈677) is an order of magnitude past design doc §6.3's own `≥100` overwhelm
threshold — exactly the "cannot flag this without hp" failure mode §5.1 warns about, now correctly
flagged. The mid-tier-monster/human-elite ratio (≈1.9) and high-tier-monster/sword-master ratio (≈5.1)
stay well below any plausible overwhelm cutoff, matching `world_info.md`'s own framing ("needs a
party," "matches or exceeds the human ceiling") — a hard fight, not a mathematical impossibility. These
numbers are illustrative of the function's *shape*, not a claim about where change 10 should actually
set its threshold — **this change does not implement the overwhelm check itself** (Non-Goal); it only
proves `effective_power()` produces ratios that a `≥100`/`≤0.01` threshold can meaningfully act on.

**Why `hp` is multiplied in, not added.** Addition would let a high-stat, near-death entity still read
as powerful right up until it drops to zero — exactly the "can't flag the mismatch" problem restated.
Multiplication means a fighter's contribution to the ratio is genuinely bounded by their own
durability, not just their offense.

**Why max hp, not current hp — corrected during review, and the failure case that forced the
correction.** An earlier draft of this function used **current** `entity.traits.hp.value`, reasoning
that design doc §6.3's "recomputed every round" language meant the ratio should track live combat
state, including hp attrition. That reading does not survive contact with this change's own
recalibrated to-hit formula (D-2), and the counterexample is exact: take an elf reduced to 1 current hp
against a full-health human elite. Current-hp `effective_power` gives the elf `(88+92+90+250) × 1 =
520` and the human `(8+9+7+10) × 120 = 4,080` — a ratio that says the *human* overwhelms the *elf* by
roughly 8×. But D-2's own saturation analysis says that human's hit rate against that elf is **0%,
fully saturated** — the human cannot land a single blow, ever, regardless of the elf's hp. A
current-hp-driven ratio would hand change 10 a signal telling it to resolve the fight, in one shot, in
favor of the one combatant mathematically incapable of connecting. That is not a corner case this
function can wave away; it is the direct, mechanical consequence of letting a *depleting* resource
drive a *power* comparison symmetrically in both directions.

**What §6.3's "recomputed every round" actually protects, and why max hp still serves it.** The design
doc's own example is not hp attrition — it is "such as dropping a disguise," i.e. a combatant's
`effective_value()` output changing because a stat-multiplier skill (×100 身體強化, ×1000 身體超強化)
activates or a disguise is dropped mid-fight. `effective_power()` is already fully sensitive to that:
every stat in the sum is read through `effective_value()` at call time, so a mid-fight multiplier
change is picked up on the very next recomputation with no additional mechanism needed. **Attrition is
already represented elsewhere** — by the turn loop's own death check (`entity.traits.hp.value <= 0`)
and by the hp gauge itself, which the to-hit/damage math (D-2/D-3) already consumes directly. It does
not need a second representation inside a power-tier scalar, and folding it in there actively breaks
that scalar the way the elf-at-1-hp case shows. `entity.traits.hp.max` (a race/tier-scaled ceiling
change 2/3 already establish, not something this function invents) is therefore the correct durability
term: it answers "how much punishment can this combatant's *kind* of body take," which is the
100×-vs-10× asymmetry §5.1 actually asks `effective_power()` to encode, without being contaminated by
how the current round happens to be going.

**A finding for change 10, not a decision this change makes.** Because `effective_power()`'s ratio is
now static across a fight except when `effective_value()` itself changes (a multiplier activating, a
disguise dropping), it cannot by itself detect "this fight is already decided because one side is
nearly dead but neither side's underlying stats changed." D-2's saturated hit rates (0%/100% at a ±50
agility gap) are a second, independent, and cheaper signal of exactly that condition — no ratio
computation needed, just the to-hit formula's own boundary. **Change 10's author should treat the power
ratio and the saturation state as two separate signals, not assume the ratio alone is sufficient** —
this change hands over the finding and the saturation-boundary numbers (D-2); it does not decide how
change 10 should combine them, since designing the overwhelm threshold itself is explicitly out of this
change's scope (Non-Goals).

**Why a flat sum of the four stats, not a weighted combination.** No source document weights
`atk_phys`/`agility`/`defense`/`magic_level` against each other — `world_info.md`'s own "此三項為全世界
共通的絕對尺度" language treats the three physical stats as directly comparable to begin with, and
`magic_level`'s cap (30/90/900) already sits on roughly the same order as the physical stats' upper
bands (34/22/95) for the two races that share the "static tier" framing. A flat sum is the least
speculative combination available and is flagged, like the damage bands (D-3), as a placeholder for
change 10/16's eventual tuning — this change's job is proving the four-input, hp-multiplied shape
works, not finding the perfectly weighted formula.

### D-5. `damage:*` effect handler: registered with `surfaces=frozenset({"traits"})`, computing the
roll and the hit/miss/magnitude decision inside the handler (step 5), never inside `apply()`.

```python
# world/rules/combat.py
def _handle_damage(actor, targets, effect_id, event_context) -> list["PendingEffect"]:
    """effect_id shape: 'damage:<school>[:<element>]' where school is 'physical' or 'magic'.
    This is this change's own convention for the 'damage:*' prefix change 8 declared and
    refused to guess at -- change 8's own illustrative example ('damage:fire:magic') was not
    authoritative; this is the actual, defined shape.

    The to-hit roll and the resulting hit/miss/damage number are computed HERE, in the pure
    staging step -- not inside the PendingEffect.apply() thunk -- per change 8's D-1: step 5
    stages, it does not mutate, and 'what the pending effect represents' must be knowable
    before commit. Rolling dice is a pure computation (it advances the RNG stream but touches
    no entity state), so doing it here is compatible with that boundary; only entity.traits.hp
    ever gets WRITTEN, and only inside apply().
    """
    school, *element = effect_id.split(":")[1:]
    stat_key = "atk_phys" if school == "physical" else "magic_level"
    pending = []
    for target in targets:
        raw_roll = dice.roll_d100()
        atk_agi = actor.skills.effective_value("agility")
        def_agi = target.skills.effective_value("agility")
        atk_mods = evaluate_combat_modifiers(actor)
        def_mods = evaluate_combat_modifiers(target)
        atk_agi = _apply_percent_mod(atk_agi, atk_mods.get("agility"))
        def_agi = _apply_percent_mod(def_agi, def_mods.get("agility"))
        accuracy = atk_mods.get("accuracy", 0)
        attack_score = raw_roll + atk_agi + accuracy
        threshold = COMBAT_YAML["to_hit"]["defender_constant"] + def_agi
        hit = attack_score >= threshold
        damage = 0
        if hit:
            multiplier = _roll_multiplier(raw_roll, attack_score - threshold)
            atk_stat = actor.skills.effective_value(stat_key)
            def_def = target.skills.effective_value("defense")
            damage = max(round(atk_stat * multiplier) - def_def, COMBAT_YAML["damage"]["floor"])
        pending.append(PendingEffect(
            entity=target,
            description=f"{actor.key} -> {target.key}: {'hit' if hit else 'miss'} ({damage} dmg)"
                        f" [roll={raw_roll}]",
            surfaces=frozenset(),   # stamped by register_effect_handler()'s caller (change 8 D-7)
            apply=(lambda t=target, d=damage: _apply_hp_delta(t, -d)) if hit else (lambda: None),
        ))
    return pending

register_effect_handler("damage", _handle_damage, surfaces=frozenset({"traits"}))
```

`_apply_hp_delta(entity, delta)` writes through `entity.traits.hp.value += delta` — the same public
accessor path every other change's mutator uses, so change 8's generic `_snapshot_entity_state()`
(which already walks `entity.traits.all()`) covers it with no `SNAPSHOTTED_SURFACES` extension needed.
This is the first real occupant of change 8's `damage:*` extension point; no edit to `action.py` is
required — `register_effect_handler()` is a public function change 8 built exactly for this.

**A determinism note for the golden tests (D-10).** Because the roll happens at step 5, a request that
is later rejected at step 6/7/8 (e.g. a malformed time-cost override) has already consumed one `roll_d100()`
call from the RNG stream even though no damage was ever applied. This is a correctness non-issue (no
entity state changed, per change 8's atomicity guarantee) but a *test-authoring* note: a fixed-seed
golden test must account for every `roll_d100()` call in sequence, not just the ones whose effects
committed.

### D-6. `BattlefieldActionContext`: two named teams, no positions, `relation_to()` derived from team
membership.

```python
# world/rules/combat.py
@dataclass
class Battlefield:
    teams: dict[str, frozenset[str]]      # e.g. {"party": {...}, "enemies": {...}} — entity keys
    roster: dict[str, "LivingEntity"]     # entity key -> live reference; Battlefield is the one
                                            # place in this change holding live references, mirroring
                                            # EventLog's own key-only discipline (change 8 D-8) for
                                            # everything that gets serialized
    fled: set[str] = field(default_factory=set)   # D-7

    def team_of(self, key: str) -> str | None:
        return next((t for t, members in self.teams.items() if key in members), None)

class BattlefieldActionContext:
    def __init__(self, battlefield: Battlefield):
        self.battlefield = battlefield

    def is_present(self, actor, target) -> bool:
        return target.key in self.battlefield.roster and target.key not in self.battlefield.fled

    def relation_to(self, actor, target) -> Relation:
        if actor is target:
            return Relation.SELF
        return (
            Relation.ALLY
            if self.battlefield.team_of(actor.key) == self.battlefield.team_of(target.key)
            else Relation.ENEMY
        )

    def is_in_range(self, actor, target, skill) -> bool:
        ...  # D-7
```

Two teams, not a general N-team model — every combat encounter design doc §6.2/§6.3 describes is
adventurer(s)-versus-monster(s); a richer faction graph (three-way fights, environmental hazards as a
"team") is not asked for anywhere in this change's dependency chain and would be speculative scope
addition. `expand_target_shorthand()`'s `"all-enemies"`/`"all-allies"`/`"all"` (change 8, already
built) read `battlefield.teams` through exactly this structure — no change to `targeting.py` is needed;
it already expects `context.battlefield` to expose *some* roster, and this is that roster's concrete
shape.

### D-7. `is_in_range()`: "engaged" (still an active roster member) is implementable today; melee-vs-
ranged genuinely is not, and is named as the reason why.

**What's implementable without coordinates.** A battlefield-level, coordinate-free notion of "still in
this fight" — an entity that has fled (design doc §6.3's "end (wipe / flee / special condition)") is
removed from being a valid target for anyone, even though the encounter as a whole may continue against
its remaining side. This is a real, if coarse, distinction — target validity now depends on live
battlefield state (`battlefield.fled`), not a blanket constant:

```python
def is_in_range(self, actor, target, skill) -> bool:
    """Battlefield-level range check: is the target still an active combatant in
    this encounter? This is the ONE real, coordinate-free constraint a roster
    (no position data) can express. It does NOT distinguish melee from ranged --
    see design.md D-7 for why that's a genuinely separate gap, not an oversight,
    and who closes it (change 12, plus possibly a SkillDef amendment neither this
    change nor change 12 owns yet)."""
    return target.key not in self.battlefield.fled
```

**What genuinely must wait, and why it isn't faked here.** Design doc §4/change 8's D-5 both name the
real distinction combat eventually needs: "melee versus 弓術 versus 瞬影步's burst movement." Building
that requires two things this change does not have:
1. **A way to know a skill's engagement range at all.** `SkillDef` (change 5, frozen for this change —
   editing another change's artifacts is out of scope) carries no field for it. `element` was
   considered as a proxy (`element is None` → physical/melee, `element is not None` → magical/ranged)
   and **rejected**: it is not what the field means (a touch-range curse still has an `element`; an
   archery skill would have `element=None` yet be plainly ranged), and inferring a mechanic from a
   field defined for something else is exactly the kind of guessed-at data model this project's
   design docs consistently warn against (e.g. change 2's D-2b explicitly rejecting deriving one
   scaled quantity from another that measures something different).
2. **Actual distance.** Even with a melee/ranged flag, "in range" for a ranged skill still needs some
   notion of how far apart combatants are, which change 12 is the one dependency that supplies.

**Decision**: ship the "still active in the encounter" check above as the complete implementation
today, and record explicitly — not silently — that melee-vs-ranged is unbuilt because the data it
needs does not exist in any dependency this change has access to. This mirrors change 8's own treatment
of `RoomActionContext.is_in_range()` exactly: a named, tested, honest no-op is preferable to an
unconditional constant that looks the same but was never examined. **Owner going forward**: change 12
for coordinates; whoever proposes the melee/ranged distinction (a `SkillDef` amendment, most likely, if
change 5's own author or a coordinator revisits it) for the classification itself. A test constructs a
battlefield with one fled combatant and asserts targeting rejects with `TARGET_OUT_OF_RANGE` against
that combatant specifically, proving the one real rule this function enforces is genuinely wired, not
decorative.

### D-8. Initiative: `agility × 10 + d100`, `agility` read through `effective_value()`.

```yaml
# rulebook/combat.yaml
initiative:
  agility_weight: 10
```

```python
def roll_initiative(battlefield: Battlefield) -> list[str]:
    """Returns roster keys ordered to act this round, highest score first."""
    scores = {
        key: entity.skills.effective_value("agility") * COMBAT_YAML["initiative"]["agility_weight"]
             + dice.roll_d100()
        for key, entity in battlefield.roster.items()
    }
    return sorted(scores, key=scores.__getitem__, reverse=True)
```

Design doc §6.3 calls for "agility-dominant + d100 jitter," not a pure agility sort and not a pure
roll. `agility_weight = 10` is the concrete meaning of "dominant": any two combatants whose
`effective_value("agility")` differs by 10 or more are ordered by agility with **certainty** (the
maximum possible jitter spread, roll 1 vs roll 100, is 99 — smaller than the deterministic 100-point
gap a 10-point agility difference produces), while combatants within a smaller gap (the common case
within one `STATIC_TIER_REGISTRY` tier) can have their order flipped by the roll — genuine jitter where
agility alone would otherwise decide every fight identically round after round. This is this change's
own judgment call (no source document specifies a weight), flagged the same way the damage-band
constants (D-3) are, for a later balance pass.

### D-9. Turn loop: per-round upkeep calls change 6's `tick_buffs()` directly (hard dependency) and a
self-arming hook for sexual decay (not a hard dependency); `actions_per_turn: 0` is read from the
combat-modifier bundle at the turn-loop level, not inside `ActionResolver`.

```python
ROUND_SECONDS = 6   # design doc §6.3

def run_round(battlefield: Battlefield, action_provider) -> list[EventLog]:
    logs = []
    for key in roll_initiative(battlefield):
        entity = battlefield.roster.get(key)
        if entity is None or entity.traits.hp.value <= 0 or key in battlefield.fled:
            continue
        mods = evaluate_combat_modifiers(entity)   # change 6's pure query — the ONE place this
                                                     # change interprets the adjustment bundle for
                                                     # a gating (not a math) purpose
        if mods.get("actions_per_turn", 1) == 0:
            logs.append(_action_skipped_event_log(entity))   # kind="action_skipped" — a new, open
                                                                # EventEntry kind (change 8 D-8:
                                                                # "kind is an open string convention")
            continue
        request = action_provider(entity, battlefield)   # player input queue, or D-9's placeholder
        if request is None:
            continue
        result = ActionResolver.resolve(request)          # change 8 — combat's ONLY entry point
                                                             # into effect resolution, identical to
                                                             # the out-of-combat CmdCast call
        if result.outcome == "success":
            logs.append(result.event_log)
    _end_of_round_upkeep(battlefield)
    return logs

def _end_of_round_upkeep(battlefield: Battlefield) -> None:
    for entity in battlefield.roster.values():
        if entity.traits.hp.value <= 0:
            continue
        tick_buffs(entity)              # change 6's seam — HARD dependency (6 is transitively
                                          # required via change 8's own dependency on 6), called
                                          # directly, no self-arming needed
        _try_sexual_decay(entity)       # self-arming — see below

def _try_sexual_decay(entity) -> None:
    """Sexual state decay/transitions are NOT a hard dependency of this change (design doc §11
    lists this change's only dependency as change 8, and 7/7b are not transitively required by
    8 either — change 8 itself self-arms around sexual_transitions for the identical reason).
    Mirrors change 8's own sexual_event:* handler exactly: lazy import, degrade to a no-op
    (not a crash) while world.rules.sexual_transitions doesn't exist, self-arm once it does."""
    try:
        from world.rules.sexual_transitions import decay_tick
    except ImportError:
        return
    decay_tick(entity)
```

**Why `actions_per_turn: 0` is read here and not inside `ActionResolver`.** Change 6's
`blocks_action(entity)` (a small, explicit `BLOCKING_BUFF_KEYS` set) already gates step 4 of
`ActionResolver.resolve()` for *any* caller, combat or not — that mechanism is untouched and still
runs. `combat_modifiers.yaml`'s `actions_per_turn` key is a *different*, combat-specific concept: a
per-round adjustment bundle that also carries `agility`/`accuracy` numbers this change already has to
interpret for the to-hit roll (D-5). Reading `actions_per_turn` from that same bundle, in the same
place the bundle is already being read, and skipping the *entire turn* before `ActionResolver` is even
called (rather than calling it and letting some hypothetical new `RejectReason` fire) keeps this
change's only combat-specific interpretation of the bundle in one function, `run_round()`, on the same
data change 6 already promised ("change 9 interprets these against its own to-hit/damage formula") —
not a new special-case branch on *which* rule produced the adjustment, since the code never inspects
rule IDs or origins, only the bundle's output keys.

**Placeholder action policy for non-player combatants.** `action_provider` is this change's seam for
"player waits for input / AI runs behaviour tree" (design doc §6.3). `Monster.behaviour_tree` (change
3's declared, unbuilt seam) does not exist yet, so this change supplies exactly one concrete
`action_provider`: `default_attack_policy(entity, battlefield)`, which selects a living, non-fled enemy
(the lowest-hp one, for a deterministic and testable choice) and returns an `ActionRequest` for
whichever `damage:*`-effect skill the entity owns, or `None` if it owns none. This is explicitly a
placeholder, not an AI — real monster behaviour is now owned by change 10b (`monster-behaviour`,
depends on 9, 10), added to the roadmap specifically to replace it; this function exists only so the
turn loop has *something* concrete to call and this change's own tests can exercise a full round
without a human at the keyboard.

### D-10. Golden fixed-seed tests: one normal exchange, one lopsided exchange.

Per design doc §10 ("Dice and combat: Fixed seed, deterministic assertions; golden cases for both
overwhelm and normal combat" — overwhelm itself is change 10's job, so this change's golden cases cover
the "normal" half plus a lopsided-but-not-overwhelm-compressed case, since this change never invokes any
overwhelm short-circuit):

- **Golden case 1 — normal exchange.** Two human-elite-tier combatants (agility 9 vs 9, matching D-2's
  parity case), fixed seed, three rounds. Asserts the exact sequence of hit/miss outcomes and damage
  numbers `roll_d100()` produces under that seed, and that `EventLog` entries reflect them precisely —
  a regression test that fails loudly if `D-2`'s constant, `D-3`'s bands, or `D-8`'s initiative weight
  are ever edited without updating the fixture.
- **Golden case 2 — lopsided exchange.** Elf (Yuka-tier, agility 92) vs human elite (agility 9), fixed
  seed, confirming every attack from the elf lands (D-2's saturated 100%) and every attack from the
  human misses (saturated 0%) for the entire fixture, regardless of the seed's specific roll sequence —
  this is the direct, executable proof that D-2's recalibration produces the deliberate, documented
  absolute outcome design doc §6.3 explicitly permits.

Both fixtures assert `run_battle()`'s reported `total_seconds` equals `rounds_elapsed × 6` exactly (D-9)
and that no call to anything resembling `WorldClock.advance()` occurs anywhere in this change's code
(a grep-based check, mirroring change 8's own task 8.x discipline).

## Risks / Trade-offs

- **[Risk] `51` (not `60`, not a round `50`) is a value a future reader could "simplify" back to `50`
  on the reasoning that they look equivalent.** → Mitigation: D-2 documents the exact reason `51` is
  the correct integer (exact 50% parity given d100's inclusive `1..100` range), and the golden test
  (D-10, case 1) asserts the literal parity hit rate a same-agility fixture produces, which would fail
  if the constant drifted to `50`.
- **[Risk] `effective_power()`'s flat-sum-times-max-hp shape and D-3's damage-band constants are both
  this change's own invented placeholders, not sourced from `world_info.md`.** → Documented explicitly
  in D-3/D-4 as judgment calls, flagged for change 10/16's eventual balance pass — the same disclosure
  discipline changes 5 (D-4) and 6 (D-3) already established for their own invented numbers.
- **[Risk] `effective_power()`'s ratio alone is not a sufficient signal for change 10's overwhelm
  threshold** — using max hp (corrected in D-4 from an earlier current-hp draft) means the ratio is
  static across a fight except when `effective_value()` itself changes, so it cannot by itself detect a
  fight that is already decided purely because one side is nearly dead. → Not this change's to fix
  (designing the threshold is change 10's job, Non-Goals) — handed to change 10 as an explicit finding
  in D-4: the power ratio and D-2's saturated to-hit rates are two independent signals, and change 10's
  author should consider both rather than the ratio alone.
- **[Risk] `is_in_range()`'s "still active in the encounter" check (D-7) is a real improvement over an
  unconditional `True`, but it still does not distinguish melee from ranged, meaning a `弓術` skill and
  a dagger both have identical range semantics today.** → Accepted and named explicitly: the data
  needed (a `SkillDef` range/reach classification) does not exist in any dependency this change can
  edit, and inventing one outside `SkillDef` was considered and rejected as guessing at a mechanic the
  source data doesn't encode. Change 12 (coordinates) and whoever eventually amends `SkillDef` are the
  two named owners of the real gap.
- **[Risk] The placeholder `default_attack_policy` (D-9) is not a real AI and always targets the
  lowest-hp living enemy — a predictable, exploitable pattern if it were ever mistaken for production
  monster behaviour.** → Accepted and named explicitly as a placeholder. `Monster.behaviour_tree`
  remains an open seam (change 3's own unbuilt declaration); the coordinator has since added change 10b
  (`monster-behaviour`, depends on 9, 10) to the roadmap as its named owner — not something this change
  resolves.
- **[Risk] Rolling dice inside the effect handler (step 5) rather than inside `apply()` (D-5) means a
  request rejected at a later step still consumes a `roll_d100()` call from the RNG stream.** →
  Accepted; no entity state is affected (change 8's atomicity guarantee is untouched), and this is
  called out explicitly as a test-authoring note (D-5, D-10) rather than a correctness bug.
- **[Risk] `evennia.contrib.rpg.dice.roll()`'s exact call signature and seed-injection mechanism are
  unverified against a locally installed Evennia 6.1.0 package.** → Flagged for implementer
  verification (D-1), consistent with changes 1-8's identical discipline for every other contrib-API
  assumption; the golden tests (D-10) fall back to seeding Python's own `random` module directly if the
  contrib exposes no first-class seed parameter.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/rules/dice.py`, `world/rules/combat.py`, and `rulebook/combat.yaml` do not exist yet. The only
sequencing concerns are operational:

- This change must land after change 8 (needs `ActionResolver.resolve()`, `ActionContext`,
  `register_effect_handler()`, `PendingEffect`, `SNAPSHOTTED_SURFACES`) and, transitively through
  change 8, changes 5 (`SkillHandler.effective_value()`) and 6 (`evaluate_combat_modifiers()`,
  `tick_buffs()`, `blocks_action()`).
- **Change 5's seed skills whose `effects` reference an as-yet-undefined `damage:*`-shaped ID**
  (`fire_ball`, `wind_blade`, every weapon-art skill) now resolve against this change's concrete
  convention (`damage:<school>[:<element>]`, D-5) with zero edit to change 5's own artifacts — this is
  the identical "declare here, populate a real registration later" split change 8 itself used for the
  registry as a whole.
- Change 10 (`overwhelm-resolution`) is expected to call this change's `effective_power()` for its own
  threshold check and to compress the multi-round `EventLog`s `run_battle()` produces. **Per D-4's
  finding**: the power ratio should not be change 10's only signal — D-2's saturated to-hit rates are a
  second, independent, and cheaper indicator that a fight is already decided; this change hands over
  the finding and the saturation-boundary numbers, not an implementation.
- Change 11 (`world-clock`) is expected to read `BattleResult.total_seconds` and decide how to advance;
  nothing in this change calls `WorldClock.advance()` itself.
- Change 12 (`map-anchor-grid`) is expected to supply the coordinates that let `is_in_range()` (D-7)
  become a real positional check; this change's `Battlefield`/`BattlefieldActionContext` do not assume
  any particular shape for that future coordinate data.

## Open Questions

- **Should a `SkillDef` range/reach classification (melee/ranged/burst-movement) be added at all, and
  if so, by whom?** Named in D-7 as a genuine gap this change cannot close (editing change 5's frozen
  artifacts is out of scope). Left for a future coordinator decision, most plausibly alongside change
  12 once coordinates exist and there is something concrete for a range classification to be checked
  against.
- **Exact `evennia.contrib.rpg.dice.roll()` signature and seed-injection mechanism** — left to the
  implementer to confirm against the installed Evennia 6.1.0 package, consistent with the verification
  discipline changes 1-8 already established; the golden tests' fallback (seeding `random` directly)
  does not depend on the answer.
- **Resolved: change 10b (`monster-behaviour`, depends on 9, 10) owns replacing `default_attack_policy`
  with real monster AI.** No longer unclaimed — the coordinator added change 10b to the roadmap
  specifically because `Monster.behaviour_tree` has been an unbuilt seam since change 3, and the
  change-16 milestone's "complete playable game" claim needs better than "always attack the lowest-hp
  enemy." Whether change 10b replaces `default_attack_policy` outright or keeps it as a "no behaviour
  tree assigned" fallback for entities it doesn't cover is change 10b's own design decision, not fixed
  here.
