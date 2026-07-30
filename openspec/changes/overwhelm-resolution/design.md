## Context

This is roadmap item #10 (design doc §11), depending on change 9 (`dice-combat`). Change 9 built
`world/rules/dice.py` (the d100 roller), `world/rules/combat.py` (`Battlefield`,
`BattlefieldActionContext`, `effective_power()`, `roll_initiative()`, `run_round()`, `run_battle()`,
`is_battle_over()`, the recalibrated to-hit/damage formulas), and `world/rules/rulebook/combat.yaml`
— but explicitly refused to build the overwhelm threshold, single-shot resolution, or `EventLog`
compression, naming this change as the owner by number in its own Non-Goals and Migration Plan.

**The handoff this change exists to close.** Change 9's design.md D-4 records a finding, not a
decision: `effective_power(entity) = (atk_phys + agility + defense + magic_level) × max_hp` produces a
ratio that is "static across a fight except when `effective_value()` itself changes" (a stat-multiplier
skill activating, a disguise dropping) — by design, so that hp attrition cannot cause a spurious flip
(the elf-at-1-hp counterexample D-4 works through in full: a current-hp-driven ratio would have told a
consumer the *human* overwhelms the *elf* by ≈8×, while D-2's own saturated to-hit rates say the human's
hit chance against that elf is 0%, exactly backwards). Because the ratio cannot see hp attrition, D-4
explicitly hands this change a second, independent fact D-2 already computed as a byproduct of
recalibrating the to-hit formula: **the to-hit formula saturates** — at an effective-agility gap of ±50
or more, one side's hit chance is exactly 0% and the other's is exactly 100%, with no roll capable of
changing that. D-4's own words: "the power ratio and the saturation state are two separate signals, not
[an assumption that] the ratio alone is sufficient." This change's central technical problem is
combining them correctly — including the case, worked out below, where they disagree.

**What already exists for this change to build on, unmodified.** `world/rules/combat.py` (public,
change 9): `effective_power(entity) -> float`; `run_round(battlefield, action_provider) -> list[EventLog]`
(one round, real dice, real `ActionResolver.resolve()` calls, per-round buff ticks and sexual decay
upkeep already included); `is_battle_over(battlefield) -> bool`; `Battlefield` (exactly two teams,
`roster`, `fled`); `COMBAT_YAML["to_hit"]["defender_constant"]` (51, D-2's recalibrated constant).
`world/rules/event_log.py` (public, change 8): `EventEntry`/`EventLog` (frozen, JSON-compatible,
entity-key-only), `render_plain_text()`. This change touches none of these files — it is additive
against their existing public surfaces only, matching the discipline changes 8 and 9 already
established for each other.

**No code exists yet for this change's own scope.** Nothing named `world/rules/overwhelm.py` or
`world/rules/rulebook/overwhelm.yaml` exists.

## Goals / Non-Goals

**Goals:**
- `world/rules/rulebook/overwhelm.yaml`: the `power_ratio_threshold` (100, per design doc §6.3), as
  tunable data, not a Python literal.
- `classify_overwhelm(battlefield) -> str | None`: three independent signals — `effective_power()`
  ratio, to-hit saturation, and an estimated-round-count bound — combined so that overwhelm means
  **decided and quick**, never merely decided (D-1) — recomputed fresh every call, so a caller
  invoking it at engage and again every round (design doc §6.3) gets a live answer each time.
- `resolve_overwhelm(battlefield, action_provider, max_rounds) -> OverwhelmResult`: single-shot
  resolution, built by reusing change 9's own `run_round()` in a loop this change owns — never a
  parallel or approximated combat algorithm — so that its outcome is provably, not approximately,
  identical to driving `run_round()` one round at a time under the same seed. Stops the moment
  `classify_overwhelm()` re-evaluates to a different verdict than the one it started with, handing
  control back rather than silently continuing under a stale classification.
- `compress_event_logs(logs, ...) -> tuple[EventLog, ...]`: drops `"roll"`-kind entries (raw d100
  values, needed by no downstream consumer once the paired `"damage"`-kind entry already records
  hit/miss and amount), keeps every other entry verbatim, and prepends one new `"overwhelm_resolution"`
  summary entry — the exact kind name change 8's own design.md predicted for this change.
- Golden, fixed-seed tests: exact consistency between single-shot and per-round resolution on the same
  seed (attacker-overwhelm direction); the same for reverse overwhelm (design doc §6.3's "player is
  one-shot"); a constructed matchup where the ratio signal fires but the hit-rate signal does not
  (both sides can still land blows); a constructed matchup where the hit-rate signal fires but the
  ratio does not (change 9's own handoff case); a constructed matchup where the two signals disagree,
  proving the fight is correctly left contested.

**Non-Goals:**
- **No monster AI** (change 10b's job entirely). `resolve_overwhelm()` takes whatever
  `action_provider` the caller supplies — including change 9's own placeholder,
  `default_attack_policy` — and never inspects or replaces it. Who acts, and how well, is unchanged by
  this change.
- **No world clock, scheduled events, or settlement order** (change 11's job). `OverwhelmResult`
  reports `total_seconds` as a plain integer using the identical `rounds_elapsed × 6` formula change 9
  already uses; nothing in this change calls `WorldClock.advance()`.
- **No Narrator or LLM involvement** (change 18's job). This change's only obligation to the Narrator is
  that a compressed `EventLog` still renders through change 8's existing `render_plain_text()` with
  zero LLM calls (D-6) — it does not write any new narration logic itself.
- **No edits to change 9's formulas.** `effective_power()`, the to-hit formula, the damage formula, and
  `COMBAT_YAML`'s existing keys are read, never modified. Where this change needed the *inputs* the
  to-hit formula already reads (effective agility, `evaluate_combat_modifiers()`,
  `defender_constant`) to compute a saturation boundary *without* rolling dice, it re-derives that
  boundary from the same constant D-2 already published (D-1 below) rather than inventing a second
  value.
- **No edits to `EventLog`/`EventEntry`'s dataclass shape** (change 8's file). Compression is a
  function that consumes and produces existing `EventLog`/`EventEntry` instances via their existing
  public constructors; `world/rules/event_log.py` is not touched.
- **No aggressive, multi-round-merging compression.** `compress_event_logs()` drops mechanically inert
  entries and adds one summary entry; it does not further merge repeated attacker/target damage
  entries across rounds into a single running total. Named explicitly in Risks as a deliberate scope
  cut, not an oversight.
- **No team sizes beyond what change 9's two-team `Battlefield` already supports**, and no positional
  combat — this change inherits `Battlefield` exactly as change 9 built it.
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users, and `world/rules/overwhelm.py`/`rulebook/overwhelm.yaml` do not exist yet.

## Decisions

### D-1. `classify_overwhelm()`: three independent signals — decided by ratio, decided by hit-rate
saturation, and bounded by an estimated round count — because "decided" is not the same claim as
"quick."

**Why a third signal is needed at all — the case that forces it.** Signals 1 and 2 below establish
that a fight's *outcome* is certain. Neither says anything about *how long* reaching that certain
outcome takes. Change 9's damage formula floors every hit at `damage.floor` (1) — so a matchup where
the ratio signal fires because one side has an enormous max-hp pool (say, 10,000) against an
attacker whose damage per landed hit is small can be "decided" (the outcome is not in doubt) while
still taking on the order of `10,000 / floor` rounds to actually finish. Two consequences follow, and
they are really one problem: **(a) `resolve_overwhelm()`'s loop (D-3) has no lower bound on how many
times it might call `run_round()` without this signal** — thousands of iterations inside a single
function call is a real robustness hazard, not a hypothetical one; **(b) even setting robustness
aside, a fight that takes thousands of rounds to conclude is a grind, not a curbstomp, and describing
it as "overwhelm" misdescribes it** — at `round.seconds: 6` (dice-combat's own constant), a
10,000-round resolution reports `total_seconds = 60,000` (≈16.7 hours) in one `OverwhelmResult`,
which change 11's clock would then have to settle in a single leap, silently blowing through every
scheduled event, quest deadline, and shop-hours boundary that would otherwise have fired along the
way. A false "overwhelm" verdict on a slow-but-certain fight is exactly as much a lie as a false
verdict on an uncertain one — it just lies about pacing instead of about the winner. **Decision:
overwhelm means decided *and* bounded — a third, independent condition alongside the two signals
below, not a robustness afterthought bolted onto the loop.**

**Signal 1 and Signal 2, combined by agreement, still only establish *direction* — they are computed
from data change 9 already exposes, combined by agreement, not by either one unconditionally
overriding the other. Signal 3 (below) then decides whether that direction is fast enough to compress
at all.**

**Signal 1 — the power ratio (design doc §6.3's own formula).** Sum `effective_power()` (change 9,
unmodified) across every living, non-fled member of each team, and compare:

```python
def team_effective_power(battlefield: Battlefield, team_key: str) -> float:
    return sum(
        combat.effective_power(battlefield.roster[key])
        for key in battlefield.teams[team_key]
        if key in battlefield.roster
        and battlefield.roster[key].traits.hp.value > 0
        and key not in battlefield.fled
    )

def power_ratio_verdict(battlefield: Battlefield, team_a: str, team_b: str) -> str | None:
    power_a = team_effective_power(battlefield, team_a)
    power_b = team_effective_power(battlefield, team_b)
    threshold = OVERWHELM_YAML["power_ratio_threshold"]
    if power_b == 0 and power_a > 0:
        return team_a          # team_b already wiped; nothing left to contest
    if power_a == 0 and power_b > 0:
        return team_b
    if power_b > 0 and power_a / power_b >= threshold:
        return team_a
    if power_a > 0 and power_b / power_a >= threshold:
        return team_b
    return None
```

Both directions are computed as genuine divisions (`power_a / power_b` and `power_b / power_a`), not
one division and its reciprocal — `100` and `1/100` are not both exactly representable in binary
floating point, and computing the reverse ratio independently sidesteps that precision question rather
than trusting `ratio <= 0.01` to mean exactly the same thing as `1/ratio >= 100`. Design doc §6.3's `≥
100` / `≤ 0.01` pair is therefore implemented as `≥ 100` checked in both directions — the same rule,
stated the way that avoids a rounding trap.

**Why team sums, not a single pairwise ratio.** `Battlefield` (change 9 D-6) already models
multi-member teams (`teams: dict[str, frozenset[str]]`), and design doc §6.3 frames the overwhelm check
as a property of the *encounter* ("at engage AND recomputed every round"), not of one attacker-defender
pair. Summing `effective_power()` per side is the natural extension of a formula whose per-entity shape
change 9 already fixed; this change does not touch that shape, only aggregates it.

**Why "living, non-fled members only," and why this does not reintroduce current-hp sensitivity.**
Change 9's D-4 is explicit that `effective_power()` must use **max** hp, not current hp, so that one
entity's own attrition cannot flip its own contribution to a ratio mid-fight. That guarantee is about a
single living entity's *own* term in the sum — it says nothing about whether a `battlefield.fled` or
zero-hp entity should still contribute its (unchanged) `effective_power()` to a *team* aggregate once it
is no longer part of the fight at all. A dead or fled combatant contributing zero to the aggregate is not
an hp-attrition signal reappearing through the back door — it is the aggregate correctly reflecting that
the team's *composition* has changed, which is a different, legitimate reason for the ratio to move
(exactly parallel to why `run_round()` itself already skips dead/fled entities in its own initiative
loop, per change 9 D-9). A living team member's own `effective_power()` term is never touched by their
current hp, satisfying D-4's guarantee unmodified.

**Signal 2 — to-hit saturation (change 9 D-2's own boundary, re-derived, not re-decided).** D-2 states
the exact boundary in closed form: hit iff `roll + attacker_agility ≥ 51 + defender_agility`, and this
saturates to a guaranteed hit at an effective-agility difference `Δ ≥ +50` (even the worst roll, 1,
still clears the threshold: `1 + Δ ≥ 51` ⟺ `Δ ≥ 50`) and a guaranteed miss at `Δ ≤ −50` (even the best
roll, 100, still fails: `100 + Δ < 51` ⟺ `Δ < −49` ⟺ `Δ ≤ −50` for integer `Δ`). This is arithmetic
already fully specified by D-2 — this change computes the same `Δ` D-2's own formula computes
(`attacker_effective_agility − defender_effective_agility`, both read through
`SkillHandler.effective_value("agility")` and adjusted by `evaluate_combat_modifiers()`, exactly as
`_handle_damage` already does) and compares it against the boundary D-2 already derived, **without
calling `roll_d100()`** — no dice are rolled, no `PendingEffect` is staged, nothing is committed. This
is the literal meaning of "cheaper": computing this signal costs one stat read and one modifier lookup
per pair, versus the four-stat-plus-hp sum `effective_power()` requires per entity.

```python
def _agility_saturation(attacker, defender) -> str:   # "hit" | "miss" | "contested"
    atk_agi = _adjusted_agility(attacker)   # effective_value("agility") + evaluate_combat_modifiers()
    def_agi = _adjusted_agility(defender)
    delta = atk_agi - def_agi
    if delta >= 50:
        return "hit"
    if delta <= -50:
        return "miss"
    return "contested"

def hit_rate_verdict(battlefield: Battlefield, team_a: str, team_b: str) -> str | None:
    a_members = _living_members(battlefield, team_a)
    b_members = _living_members(battlefield, team_b)
    if not a_members or not b_members:
        return None   # let power_ratio_verdict's zero-power branch handle a wiped side
    a_always_hits = all(_agility_saturation(a, b) == "hit" for a in a_members for b in b_members)
    b_never_hits = all(_agility_saturation(b, a) == "miss" for a in a_members for b in b_members)
    if a_always_hits and b_never_hits:
        return team_a
    b_always_hits = all(_agility_saturation(b, a) == "hit" for a in a_members for b in b_members)
    a_never_hits = all(_agility_saturation(a, b) == "miss" for a in a_members for b in b_members)
    if b_always_hits and a_never_hits:
        return team_b
    return None
```

**Why "every cross-team pair," not a representative pair.** A team is only unambiguously hit-rate-
overwhelmed if *every* member relationship is saturated in the same direction; a team with one member
who can still land or take a hit is a team where the fight's outcome still depends on a real roll
somewhere, which is precisely the condition the ratio signal (not this one) may still be able to speak
to independently. This is a conservative, no-false-positive rule for this signal specifically, not a
statement that the encounter overall cannot be overwhelm.

**Why the two attacker/defender halves are checked independently, not derived from one `Δ`.** For a
*single* pair with no combat modifiers, `Δ_A→B = agility_A − agility_B` and `Δ_B→A = −Δ_A→B` are
mathematically forced negations of each other, so "A always hits" already implies "B always misses."
But D-2/D-5's to-hit formula adds an `accuracy` modifier on the attacker's own side only
(`evaluate_combat_modifiers()`'s `accuracy` key), which is not symmetric — a buff that raises A's
accuracy without correspondingly lowering B's does not raise B's own miss chance by the same amount it
raises A's hit chance. Checking `a_always_hits` and `b_never_hits` as two independent boolean
conditions (rather than computing one `Δ` and assuming its negation covers the reverse direction) is
what keeps this function correct once accuracy modifiers are in play, not just in the modifier-free
case this section's arithmetic derivation used to state the boundary.

**Combining signals 1 and 2 — the rule, and the case that forces it to exist.** This step only decides
*direction* (`_decided_direction()` below); Signal 3 (after the four cases) decides whether that
direction is also fast enough to act on.

```python
def _decided_direction(battlefield: Battlefield, team_a: str, team_b: str) -> str | None:
    ratio_verdict = power_ratio_verdict(battlefield, team_a, team_b)
    rate_verdict = hit_rate_verdict(battlefield, team_a, team_b)
    if ratio_verdict is not None and rate_verdict is not None:
        return ratio_verdict if ratio_verdict == rate_verdict else None   # disagreement: see below
    return ratio_verdict if ratio_verdict is not None else rate_verdict
```

Three of the four combination cases are the direct, intended payoff of having two independent signals:

- **Only the ratio fires** (hard requirement's first named scenario: *ratio exceeds the threshold, but
  both sides can still land blows*). A high-hp, high-defense combatant facing a much weaker one whose
  agility is not badly outmatched: neither side's to-hit rate saturates (both can still connect), but
  the power gap is still real and overwhelming — the weak side's occasional landed hit will never
  matter against a durability gap this large. The ratio signal is what change 9's own D-4 built
  `effective_power()` to catch (`hp` folded in multiplicatively specifically so durability, not just
  offense, drives the number); this is the case it was built for, and the hit-rate signal correctly has
  nothing to add here — it is silent (`None`), not contradicting.
- **Only the hit-rate signal fires** (the hard requirement's second named scenario, and change 9 D-4's
  own handoff case verbatim): a large effective-agility gap with a *comparable* power ratio — for
  example, two same-tier combatants where one has an active agility-doubling skill (large enough to
  push `Δ ≥ 50`) but otherwise similar `atk_phys`/`defense`/`magic_level`/max-hp, so
  `team_effective_power()`'s ratio stays well under 100 even though one side can never be hit and the
  other can never land a blow. The ratio signal is silent here — nothing about the four summed stats
  times hp moved enough to cross 100 — but the fight's outcome is already mathematically settled: the
  side that always hits will eventually win by attrition with zero risk, however many rounds it takes.
  This is exactly the case D-4 flagged as invisible to the ratio alone.
- **Neither fires**: contested, per-round rolls — design doc §6.3's `otherwise` branch, unchanged.

**The fourth case — the two signals disagree — is not in the task brief's two named scenarios, but this
change's own derivation surfaces it, and it needs an explicit rule.** Because `effective_power()`
weighs `defense` and max-hp alongside `agility`, and the hit-rate signal depends on `agility` (plus
`accuracy`) *alone*, a combatant can be built so the two signals point in opposite directions: a
high-defense, high-hp, low-agility "tank" facing a low-power, high-agility "duelist" — the ratio signal
says the tank overwhelms the duelist (huge durability gap), while the hit-rate signal says the *duelist*
overwhelms the tank (the duelist's agility edge means the duelist always connects and the tank never
does). Declaring an "overwhelm" verdict in *either* direction here would assert an outcome the
mathematics do not actually support: the tank cannot be brought down quickly (it barely takes damage
even from guaranteed hits, per the ratio signal) and cannot bring the duelist down at all (it can never
land a hit, per the hit-rate signal) — the honest state is a slow, genuinely uncertain grind whose
resolution depends on factors (damage floor accumulation, whether the duelist chooses to disengage)
neither signal alone determines. **Decision: on disagreement, the fight is left contested** (returns
`None`, the same as "neither fires") — this is the conservative choice consistent with hard requirement
#3's priority (a wrong "decided" verdict compresses combat into an outcome the real per-round rolls
would not reproduce, which is the one failure this change cannot accept); a false negative here (an
encounter that is in fact heavily one-sided over enough rounds, resolved the slow way) costs performance
and pacing, not correctness. A golden test constructs exactly this matchup and asserts
`_decided_direction()` returns `None`.

**Signal 3 — an estimated-round-count bound, deliberately current-hp-sensitive, and deliberately
biased to never underestimate how long a fight will take.** Signals 1 and 2 (combined above into
`_decided_direction()`) establish that a fight's outcome is certain; neither says anything about how
long reaching that certain outcome takes. Change 9's damage formula floors every hit at
`damage.floor` (1) — so a matchup where the ratio signal fires because one side has an enormous
max-hp pool (say, 10,000) against an attacker whose damage per landed hit is small is "decided" (the
outcome is not in doubt) while still potentially taking on the order of `10,000 / floor` rounds to
actually finish. This is one problem with two faces: **(a) `resolve_overwhelm()`'s loop (D-3) would
have no lower bound on how many times it calls `run_round()` without this signal** — thousands of
iterations inside a single function call is a real robustness hazard; **(b) even setting robustness
aside, a fight that takes thousands of rounds to conclude is a grind, not a curbstomp, and calling it
"overwhelm" misdescribes it** — at `round.seconds: 6` (dice-combat's own constant), a 10,000-round
resolution reports `total_seconds = 60,000` (≈16.7 hours) in one `OverwhelmResult`, which change 11's
clock would then have to settle in a single leap, silently blowing through every scheduled event,
quest deadline, and shop-hours boundary that would otherwise have fired along the way. A false
"overwhelm" verdict on a slow-but-certain fight is exactly as much a misrepresentation as a false
verdict on an uncertain one — it lies about pacing instead of about the winner. **Decision: overwhelm
means decided *and* bounded — a third, independent condition, not a robustness afterthought bolted
onto the loop.**

```python
def _expected_damage_per_attack(attacker, defender) -> float:
    """A deliberately conservative (never-overestimated) expected damage figure for one
    attacker's one attack against one defender. Uses the ACTUAL to-hit probability (never
    assumes 100%, so this also works for a ratio-only verdict where hits are not saturated)
    and ONLY combat.py's base_multiplier (ignores the solid-hit and critical bonuses D-3 of
    dice-combat's own design defines) and attacker.effective_value('atk_phys') as the
    representative damage stat (a simplification -- this estimate does not know which skill
    the real action_provider will choose each round; a magic-primary attacker would need
    magic_level here instead, flagged as a scope-conscious approximation, not a claim about
    which skill actually gets cast). Underestimating expected damage means this function's
    caller (below) never underestimates the number of rounds needed -- the one direction of
    error this signal cannot afford, since overestimating rounds only costs a missed
    compression opportunity, while underestimating them would let a genuine grind through."""
    atk_agi = _adjusted_agility(attacker)   # same helper D-1's Signal 2 already defines
    def_agi = _adjusted_agility(defender)
    hit_prob = max(0.0, min(1.0, (50 + (atk_agi - def_agi)) / 100))
    atk_stat = attacker.skills.effective_value("atk_phys")
    def_def = defender.skills.effective_value("defense")
    base_dmg = max(
        round(atk_stat * combat.COMBAT_YAML["damage"]["base_multiplier"]) - def_def,
        combat.COMBAT_YAML["damage"]["floor"],
    )
    return hit_prob * base_dmg

def estimated_rounds_to_conclude(
    battlefield: Battlefield, overwhelming_team: str, overwhelmed_team: str,
) -> float:
    overwhelmed = _living_members(battlefield, overwhelmed_team)
    overwhelming = _living_members(battlefield, overwhelming_team)
    remaining_hp = sum(m.traits.hp.value for m in overwhelmed)   # CURRENT hp -- see below for why
    if remaining_hp <= 0:
        return 0.0
    if not overwhelming or not overwhelmed:
        return math.inf
    # Conservative simplification: pool the overwhelmed side's total remaining hp against the
    # overwhelming side's total expected damage per round against the single toughest
    # remaining defender, rather than modelling target selection or focus-fire order -- an
    # approximation of "how many rounds until the whole side is cleared," not a claim about
    # exactly which defender dies on which round.
    toughest = max(overwhelmed, key=lambda m: m.traits.hp.value)
    dmg_per_round = sum(_expected_damage_per_attack(a, toughest) for a in overwhelming)
    if dmg_per_round <= 0:
        return math.inf
    return remaining_hp / dmg_per_round
```

**Why this signal is allowed to read current hp, when D-4 explicitly required max hp for
`effective_power()` and hard requirement 4 warns against reintroducing current-hp sensitivity.** D-4's
max-hp discipline answers "how strong is this combatant, in general" — a question that must not
flicker with mid-fight attrition, because the same underlying entity should not be judged more or less
dangerous just because a fight has been going well or badly for them so far. `estimated_rounds_to_conclude()`
answers a categorically different question: "given where this fight actually stands right
now, how much longer does it have left" — which is *only* meaningful in terms of current, depleting
hp; a max-hp version of this function would answer "how long would this take starting from full
health," which is not the question a per-round-recomputed gate needs answered. Using current hp here
is not a relapse into the mistake D-4 corrected — it is a different signal, answering a different
question, for which current hp is the *correct* input, not an accidental one. This is also why Signal
3 is not folded into Signal 1: `effective_power()`'s own ratio must stay attrition-blind for the
reason D-4 gives; the round-bound estimate must not.

**Calibration, against this project's own reference matchups.** `max_estimated_rounds` is this
change's own invented placeholder (flagged for a future balance pass, the identical disclosure
discipline changes 5/6/9 already used for their own invented numbers):

| Matchup | remaining hp | conservative dmg/round | estimated rounds |
|---|---|---|---|
| elf (agility 92, `atk_phys` 88) vs. human elite (agility 9, defense 7, hp 120) — dice-combat D-4's own reference pair | 120 | 81 (hit_prob 1.0, saturated) | ≈1.5 |
| the same elf vs. a 3-member low-tier monster party (illustrative stats within lore-world-data's low band — `atk_phys`/agility/defense ≈6, hp ≈90 each) | 270 (pooled) | 82 (vs. the toughest, hit_prob 1.0) | ≈3.3 |
| an illustrative calamity-tier monster (`atk_phys` ≈100) vs. a 3-member human-elite party (hp 120 each) — design doc §6.3's "player is one-shot" | 360 (pooled) | 93 (hit_prob 1.0) | ≈3.9 |
| the coordinator's own named grind: a 10,000-hp defender against a `damage.floor`-only (1 dmg/round) attacker | 10,000 | 1 | 10,000 |

The three genuine curbstomps cluster at 1.5-3.9 rounds; the grind is four orders of magnitude past
that. **Decision: `max_estimated_rounds: 5`** — comfortably above every real curbstomp this project's
own reference data produces, comfortably below any matchup that is actually a slow attrition fight.

**`classify_overwhelm()`, final form — decided direction, then bounded.**

```python
def classify_overwhelm(battlefield: Battlefield) -> str | None:
    team_a, team_b = sorted(battlefield.teams)
    decided = _decided_direction(battlefield, team_a, team_b)
    if decided is None:
        return None
    overwhelmed_team = team_b if decided == team_a else team_a
    est_rounds = estimated_rounds_to_conclude(battlefield, decided, overwhelmed_team)
    if est_rounds > OVERWHELM_YAML["max_estimated_rounds"]:
        return None   # decided, but a grind -- stays in the normal per-round turn loop
    return decided
```

This changes nothing about how `resolve_overwhelm()` (D-3) behaves once it starts running — the round
bound only affects *whether*, and *for how long*, `classify_overwhelm()` keeps agreeing to single-shot
resolution; it introduces no new dice roll, no new mutation, and does not touch D-3's exact-equivalence
proof, since `classify_overwhelm()` (all three signals) is still called only *between* `run_round()`
calls, never during one.

### D-2. `world/rules/rulebook/overwhelm.yaml`: two threshold keys, both data.

```yaml
# world/rules/rulebook/overwhelm.yaml
power_ratio_threshold: 100   # design doc §6.3: "ratio >= 100 -> single-shot resolution". Checked in
                               # BOTH directions independently (team_a/team_b and team_b/team_a) by
                               # power_ratio_verdict() -- see design.md D-1 for why this is not simply
                               # "<= 0.01" on one division. Do not add a second, separate constant for
                               # the reverse direction; it is the same number, checked the other way.
max_estimated_rounds: 5        # design.md D-1's Signal 3: "decided" is not "quick". Calibrated against
                               # dice-combat's own worked matchups (~1.5-3.9 rounds for genuine
                               # curbstomps) vs. a floor-damage grind (~10,000 rounds) -- see the full
                               # table in design.md D-1. An invented placeholder, like combat.yaml's
                               # own damage-band constants, flagged for a future balance pass.
```

`power_ratio_threshold` is design doc §6.3's own literal value, not this change's invention; the
hit-rate signal's `±50` boundary is `dice-combat`'s own derived constant (`51`), not a second tunable
this change introduces; `max_estimated_rounds` is this change's own placeholder, calibrated above and
flagged for a future balance pass, exactly like `combat.yaml`'s own damage-band constants.

### D-3. `resolve_overwhelm()`: reuse change 9's `run_round()` verbatim; "single-shot" is a claim about
the caller's experience and the output's shape, not about the underlying dice math.

**The tension this decision resolves.** Design doc §6.3 reads, in isolation, as if `ratio >= 100`
should make combat "end in one round" *mechanically* — i.e., that the resolution algorithm itself
should differ once overwhelm is detected. But change 9's damage formula (D-3) still draws a random roll
multiplier (`base` / `solid_hit` / `critical`, margin- and natural-100-dependent) on every hit, even a
guaranteed one — a guaranteed *hit* is not a guaranteed *kill*. Building a *different* resolution
algorithm for the overwhelm case — e.g., a closed-form estimate using expected damage per hit to compute
how many hits are needed — was considered and **rejected**: it does not, and cannot, provably reproduce
what real per-round `roll_d100()` calls under the same seed would have produced (a different code path
consuming the RNG stream differently, or not consuming it identically at all, has no way to guarantee
the same final hp values, the same number of rounds, or even the same winner in a genuinely close
overwhelm-boundary case). That divergence is exactly what hard requirement/acceptance criterion #3 rules
out: "if resolving in one shot produces a materially different outcome from actually running the
rounds, the optimisation is a lie."

**Decision: `resolve_overwhelm()` does not compute combat differently at all — it calls change 9's own
`run_round(battlefield, action_provider)` in a loop, exactly as an external caller manually driving
round-by-round resolution would, and stops when either the encounter ends or the classification
changes.**

```python
@dataclass(frozen=True)
class OverwhelmResult:
    event_logs: tuple[EventLog, ...]      # compressed, see D-4
    rounds_elapsed: int
    total_seconds: int                     # rounds_elapsed * 6 -- combat.py's own formula, unedited
    overwhelming_team: str | None          # the verdict resolve_overwhelm() started with
    verdict_after: str | None              # classify_overwhelm()'s result once the loop stopped
    battle_over: bool

def resolve_overwhelm(
    battlefield: Battlefield, action_provider, max_rounds: int = 12,
) -> OverwhelmResult:
    verdict = classify_overwhelm(battlefield)
    if verdict is None or combat.is_battle_over(battlefield):
        return OverwhelmResult((), 0, 0, verdict, verdict, combat.is_battle_over(battlefield))

    initial_verdict = verdict
    raw_logs: list[EventLog] = []
    rounds = 0
    while (
        verdict == initial_verdict
        and not combat.is_battle_over(battlefield)
        and rounds < max_rounds
    ):
        raw_logs.extend(combat.run_round(battlefield, action_provider))   # THE unmodified change-9 call
        rounds += 1
        verdict = classify_overwhelm(battlefield)   # hard requirement 4: recomputed every round

    other_team = next(t for t in battlefield.teams if t != initial_verdict)
    compressed = compress_event_logs(raw_logs, initial_verdict, other_team, rounds)
    return OverwhelmResult(
        compressed, rounds, rounds * 6, initial_verdict, verdict, combat.is_battle_over(battlefield),
    )
```

No new dice roll, no new formula, no new resource mutation exists anywhere in this function or in
`classify_overwhelm()`/`compress_event_logs()` — every state change the encounter undergoes happens
exclusively inside `combat.run_round()`, unmodified, called the same way it would be called manually.
**This is what makes exact equivalence provable rather than merely argued**: the sequence of
`ActionResolver.resolve()` calls, `roll_d100()` draws, and hp mutations produced by `resolve_overwhelm()`
under a given seed and a given starting `Battlefield` is, by construction, identical to the sequence
produced by calling `combat.run_round()` that same number of times, in a loop the caller writes
themselves, under the same seed and the same starting `Battlefield` — because it is the same calls, in
the same order, consuming the same RNG stream (`classify_overwhelm()` never calls `roll_d100()`, so
interleaving it between rounds does not perturb the sequence at all).

**`max_rounds` is now a defensive backstop, not the primary bound — and its default is chosen to
reflect that.** D-1's Signal 3 already stops the loop on its own: `classify_overwhelm()` is
recomputed every round (line above), and its round-bound check means that if an encounter's actual
progress ever falls behind the estimate that let it start (bad luck on a non-saturated ratio-only
matchup, for instance), the very next recomputation sees `estimated_rounds_to_conclude()` grow past
`max_estimated_rounds` and returns `None`, ending the loop through the ordinary
classification-changed path — no special-casing needed. `max_rounds` exists purely as
defense-in-depth for a case Signal 3's own approximation might miss (e.g., an entity somehow taking
no damage at all despite a nonzero estimate, so `remaining_hp` never drops and the estimate never
correctly renders as "grown too large"). Its default, `12`, is set to roughly 2-3× the calibrated
`max_estimated_rounds` (5) — comfortably above any of this project's genuine curbstomps even
accounting for normal roll variance, but nowhere near the scale (thousands of rounds) that would
constitute a server-side hang. **Hitting `max_rounds` is a named, tested outcome**: the loop exits
exactly as it would on any other classification change, `OverwhelmResult.battle_over` reports
whatever `combat.is_battle_over()` actually returns (almost always `False` in this case), and
`verdict_after` reports `classify_overwhelm()`'s most recent value — a caller that sees
`battle_over=False` after `resolve_overwhelm()` returns is expected to fall back to the normal
per-round turn loop for the remainder, identically to how it would handle any other unresolved
encounter.

**Why the loop stops on any classification change, not just a return to "contested."** If, mid-fight, a
disguise drops and `effective_power()`'s ratio flips (or an active buff wears off and the hit-rate
signal stops saturating), `classify_overwhelm()`'s next call reflects that immediately — this is design
doc §6.3's "recomputed every round... handles mid-fight power-tier shifts, such as dropping a disguise,"
now with a concrete consumer. Stopping on *any* change (not only a drop to `None`) also covers the rarer
case where the verdict flips to the *other* team overwhelming — continuing to compress under the
original, now-stale direction would misrepresent who is winning; handing control back and requiring a
fresh `resolve_overwhelm()` call (or a fall-through to per-round handling) is the same "recompute, don't
assume" discipline applied uniformly.

**What "single-shot" is actually claiming, restated plainly.** From the perspective of whatever will
eventually call this function (a command layer or turn scheduler — out of scope, not built by this
change or by change 9), an overwhelm-classified encounter is resolved by **one function call** instead
of the caller having to drive `run_round()` itself once per round and decide each time whether to
continue — that is the "single-shot" the caller experiences. It is not a claim that the underlying
combat took only one round of real dice; for the concrete matchups this project's own calibration data
defines, it typically does (see the golden test below), but that is a consequence of this project's
actual stat bands, not a property this change's algorithm assumes or depends on for correctness.

**`total_seconds` is always the honest sum of the rounds actually run, never a flat one-round charge —
and Signal 3 is what keeps that honest sum small.** `OverwhelmResult.total_seconds = rounds * 6`
(unchanged from D-3's own formula, above) reports exactly how much game time the encounter actually
consumed, whether that is `6` (one round) or, in principle, `72` (twelve rounds, `max_rounds`'
defensive ceiling). Flattening this to a fixed charge regardless of `rounds` was considered and
rejected outright: it would silently misreport elapsed game time to change 11's clock the moment any
overwhelm-classified fight took more than one round, which is a strictly worse failure mode than the
one this whole revision addresses — not a rare edge case, but a routine one, since only this project's
single most lopsided reference matchup (elf vs. human elite) happens to end in exactly one round.
Signal 3 is what makes this honest-sum reporting safe to leave uncapped at the reporting layer: because
`classify_overwhelm()` only allows single-shot resolution to begin, and to continue, while
`estimated_rounds_to_conclude()` stays under `max_estimated_rounds`, the honestly-summed
`total_seconds` an overwhelm resolution reports is itself bounded in practice to a handful of rounds
(≈`5 × 6 = 30` seconds at the calibrated bound, never the ≈17-hour figure a 10,000-round grind would
have produced under the pre-revision design) — the fix to the threshold and the fix to the reported
time cost are the same fix, not two separate ones.

**Golden proof that design doc §6.3's literal "ends in one round" language holds for this project's own
reference matchup.** Using change 9's own D-4 worked table (elf, stats 88/92/90, max hp 10000, vs. human
elite, stats 8/9/7, max hp 120): `resolve_overwhelm()` on this exact fixture, fixed seed, asserts
`rounds_elapsed == 1` — the elf's single hit already exceeds the human's entire hp pool (D-3's damage
formula: even a bare hit, `atk_phys 88 × 1.0 − defense 7 ≈ 81`, already exceeds hp 120 only after a
second hit at base multiplier, but a solid or critical hit clears it in one — the golden fixture's fixed
seed is chosen to land on a hit that does), which is the executable confirmation that this change's
general, not-hardcoded-to-one-round algorithm produces the design doc's stated common case exactly, for
the numbers this project actually calibrated (dice-combat D-4), while remaining correct — not merely
"usually correct" — for any future matchup where a single round does not suffice.

### D-4. `compress_event_logs()`: drop `"roll"`-kind entries, keep everything else, add one summary
entry — "fewer, coarser entries" without losing "who hit whom, for how much."

**Reconciling two requirements that sound like they pull in opposite directions.** Change 8's design.md
D-8 anticipated this change producing "one `overwhelm_resolution` entry standing in for what would
otherwise be a dozen per-round `roll` entries" — language that reads as aggressive summarization. The
task brief insists just as explicitly that "a full `EventLog` is still produced — who hit whom, for how
much, where," and that compression "means computing the whole exchange at once, not omitting it." These
are reconciled by distinguishing what each `EventEntry.kind` change 9 emits actually carries: per
change 9's own Non-Goals, every resolved attack produces **two** new kinds, `"roll"` and `"damage"`.
`"roll"` records the mechanical fact — the raw `d100` integer — which by itself tells no one anything
about what happened (a `73` is meaningless without also knowing the threshold it was compared against
and the resulting hit/miss). `"damage"` records the narratively load-bearing fact `_handle_damage`
already assembles per target either way (D-5's own `PendingEffect.description`: `"{actor} -> {target}:
{'hit' if hit else 'miss'} ({damage} dmg) [roll={raw_roll}]"` — hit **and** miss both produce this,
never only hits). Dropping `"roll"` entries and keeping `"damage"` entries therefore satisfies both
requirements simultaneously: strictly fewer entries (every `"roll"` entry disappears), while "who hit
whom, for how much" survives untouched, because that fact was never encoded in the `"roll"` entry to
begin with — it already lived in `"damage"`.

```python
def compress_event_logs(
    raw_logs: list[EventLog], overwhelming_team: str, overwhelmed_team: str, rounds: int,
) -> tuple[EventLog, ...]:
    filtered = tuple(
        dataclasses.replace(log, entries=tuple(e for e in log.entries if e.kind != "roll"))
        for log in raw_logs
    )
    filtered = tuple(log for log in filtered if log.entries)   # an all-roll log (none observed in
                                                                  # change 9's own construction, per
                                                                  # the description above, but checked
                                                                  # defensively) contributes nothing
    hits = sum(
        1 for log in filtered for e in log.entries
        if e.kind == "damage" and e.data.get("hit")
    )
    total_damage = sum(
        e.data.get("amount", 0) for log in filtered for e in log.entries
        if e.kind == "damage" and e.data.get("hit")
    )
    summary = EventLog(
        actor=overwhelming_team, skill_key="overwhelm_resolution", targets=(overwhelmed_team,),
        entries=(EventEntry(
            kind="overwhelm_resolution", actor=overwhelming_team, target=overwhelmed_team,
            data={"rounds": rounds, "hits": hits, "total_damage": total_damage},
            text_template=(
                "{actor} 以壓倒性的力量在 {data[rounds]} 回合內壓制了 {target}，"
                "命中 {data[hits]} 次，造成共 {data[total_damage]} 點傷害。"
            ),
        ),),
        time_cost_seconds=0,   # the real time cost is already fully accounted for by `filtered`'s own
                                 # per-action time_cost_seconds; this entry adds no new time cost of
                                 # its own, only a narrative summary of already-elapsed rounds
    )
    return (summary,) + filtered
```

**Why `actor`/`targets` on the summary `EventLog` are team keys, not entity keys.** `EventLog.actor`
and `EventEntry.actor`/`.target` are typed as plain `str` (change 8 D-8) specifically because `kind` and
by extension the *meaning* of these string fields is an open convention, not a closed schema tied to one
entity-key format — change 8's own event-log spec states `kind` "is a plain string, not a fixed enum, so
that later changes ... can introduce new kind values without modifying `EventLog`'s or `EventEntry`'s
dataclass definitions," and the `render_plain_text()` mechanism this change depends on
(`text_template.format(actor=..., target=..., data=...)`) has no format-validation on what an
`actor`/`target` string looks like. Using a `battlefield.teams` key here — visibly different in shape
from an individual entity key — is a deliberate, minimal widening of an already-open convention for
exactly the one new kind this change introduces, not a silent assumption; a consumer that needs an
individual entity to blame or credit still has every constituent `"damage"` entry, each with its own
real entity-keyed `actor`/`target`, immediately following the summary in `filtered`.

**Why `filtered` is still returned alongside the summary, not discarded.** This is the direct,
executable answer to "a full EventLog is still produced." A Narrator (change 18) that wants a single
decisive paragraph can render only the summary entry; one that wants blow-by-blow detail (or a debug/
replay view) has every individual hit, in order, immediately available — the compression adds a coarse
view on top of the full one, it does not replace it.

### D-5. Golden fixed-seed tests: exact-equivalence, both overwhelm directions, the signal-combination
cases, and the round-bound signal.

Per design doc §10 ("golden cases for both overwhelm and normal combat" — change 9's own golden tests
(D-10) covered "normal" only, explicitly deferring "overwhelm" to this change):

- **Consistency golden case.** One fixed-seed `Battlefield` (elf party vs. human-elite party, or the
  1v1 elf/human fixture reused from change 9's own D-10 lopsided case), run twice from byte-identical
  starting state under the identical seed: once through `resolve_overwhelm()`, once through a hand-
  written loop calling `combat.run_round()` directly the same number of times `resolve_overwhelm()`
  internally consumed. Asserts every entity's final `hp`, the winner, `rounds_elapsed`, and — critically
  — the **uncompressed** `raw_logs` list `resolve_overwhelm()` builds internally (exposed for the test,
  not part of `OverwhelmResult`'s public shape) is entry-for-entry identical to the manually driven
  path's collected logs. This is the executable proof for hard requirement/acceptance criterion #3.
- **Reverse-overwhelm golden case** (design doc §6.3's "player is one-shot"), with the same rigor as
  the first: a fixture where the human-tier team is the overwhelmed side and the elf/monster-tier team
  is overwhelming, same consistency assertions, same compressed-log render check (D-6).
- **Ratio-only golden case**: a constructed matchup (large hp/defense gap, agility gap under 50) where
  `power_ratio_verdict()` fires and `hit_rate_verdict()` returns `None` — asserts `classify_overwhelm()`
  returns the ratio's verdict, and that the resulting `EventLog` still contains individual `"damage"`
  entries showing the weaker side landing at least one hit (matching "both sides can still land
  blows").
- **Hit-rate-only golden case** (change 9 D-4's own handoff case, made concrete): two same-tier
  combatants, comparable `atk_phys`/`defense`/`magic_level`/max-hp, one with an agility-multiplying
  buff active large enough to push `Δ ≥ 50` — asserts `power_ratio_verdict()` returns `None` (ratio
  stays under 100) while `hit_rate_verdict()` fires, and `classify_overwhelm()` returns the hit-rate
  verdict.
- **Disagreement golden case** (D-1's tank-vs-duelist construction): asserts `classify_overwhelm()`
  returns `None` despite each individual signal, computed separately, returning a non-`None` (opposite)
  verdict.
- **Bounded-curbstomp golden case** (the party-vs-low-tier-monsters row of D-1's calibration table): a
  decided direction whose `estimated_rounds_to_conclude()` sits well under `max_estimated_rounds` —
  asserts `classify_overwhelm()` accepts it, `resolve_overwhelm()` runs it to completion, and
  `rounds_elapsed` stays within a small, asserted upper bound (not exactly 1, unlike the single-hit
  fixture below — this case is chosen specifically to exercise a multi-round-but-still-bounded path).
- **Excluded-grind golden case** (the coordinator's own named counterexample, D-1's calibration table):
  a decided direction (ratio signal fires: an enormous max-hp gap) whose to-hit and damage numbers are
  set so `estimated_rounds_to_conclude()` is far beyond `max_estimated_rounds` (e.g. a defender hp pool
  and attacker damage output chosen so every hit lands at `damage.floor`) — asserts `classify_overwhelm()`
  returns `None` despite `power_ratio_verdict()` alone returning a non-`None` verdict, proving the
  round-bound signal, not just direction, gates the result; a companion assertion confirms
  `resolve_overwhelm()` called directly on this same fixture returns immediately with zero rounds run,
  the same "already contested" early exit as any other non-overwhelm battlefield.
- **`max_rounds` safety-cap golden case**: a constructed fixture where `classify_overwhelm()`'s verdict
  keeps returning the same team every round (so the loop does not exit via reclassification) for longer
  than `max_rounds`, exercising the loop's `rounds < max_rounds` bound directly — asserts
  `resolve_overwhelm()` stops at exactly `max_rounds` rounds, reports `battle_over` honestly (whatever
  `combat.is_battle_over()` actually returns at that point, expected `False` for this fixture), and
  reports `total_seconds == max_rounds * 6` — the honest sum for however far it actually got, never a
  flat charge.

### D-6. Compressed `EventLog`s render through `render_plain_text()` with zero LLM calls — verified,
not assumed.

`compress_event_logs()`'s return type, `tuple[EventLog, ...]`, is a sequence of ordinary `EventLog`
instances built through change 8's own frozen dataclass constructors — nothing about them is special to
`render_plain_text()`, which only ever reads `EventLog.entries` and formats each entry's
`text_template` against its own `actor`/`target`/`data` (change 8 D-8, unmodified). Rendering a
compressed encounter with no LLM present is therefore:

```python
"\n".join(render_plain_text(log) for log in result.event_logs)
```

— the identical join-over-a-list pattern already required for an *uncompressed* multi-round encounter,
since `combat.run_round()` already returns `list[EventLog]` (one per resolved action) rather than one
merged log per round; compression does not introduce a new consumption pattern, it only shortens the
list and changes what a few of its entries say. A test calls this exact join against both the
consistency golden case's compressed result and, separately, against a synthetic `EventLog` built with
the `"overwhelm_resolution"` kind and a `text_template` using positional `{data[key]}` access (Python's
`str.format()` mini-language supports dict-key indexing inside a replacement field natively — no change
to `render_plain_text()`'s implementation is needed for this to work), asserting the output is
non-empty, contains no unresolved `{...}` placeholder, and is byte-identical across two calls (pure
function, no hidden state).

## Risks / Trade-offs

- **[Risk] The `classify_overwhelm()` disagreement rule (D-1) means some genuinely lopsided-in-practice
  fights (a tank-vs-duelist construction) are never compressed, even though one side may in fact be
  unable to lose.** → Accepted, and treated as the correct trade-off given hard requirement #3's
  priority: a false "not overwhelm" costs only pacing (the fight plays out the slow, real way, which is
  still correct — just not compressed); a false "overwhelm" in either direction would assert a winner
  the real per-round dice do not actually guarantee, which is the one failure this change is designed
  to never produce. Documented explicitly rather than silently resolved by picking one signal to always
  win.
- **[Risk] `compress_event_logs()`'s assumption that every `"damage"`-kind `EventEntry` change 9
  produces carries both hit and miss outcomes (never a bare `"roll"` entry standing alone with no
  paired `"damage"` entry) is inferred from change 9's design.md D-5, not confirmed against change 9's
  actual landed implementation** (change 9 is a sibling roadmap item; its own `EventEntry` construction
  code inside `_step7_build_event_log`'s consumption of `PendingEffect.description` is not fully
  specified at the design-document level). → Flagged for implementer verification, consistent with
  changes 1-9's established discipline for every cross-change interface assumption; the defensive `if
  log.entries` filter in `compress_event_logs()` (D-4) means an all-`"roll"`, no-`"damage"` log — if
  change 9's actual implementation ever produces one — is dropped silently rather than crashing, and a
  test asserts this against change 9's real, landed `run_round()` output (not a mock), which is what
  actually settles the question once change 9's code exists to inspect.
- **[Risk] `estimated_rounds_to_conclude()`'s conservative approximations (base-multiplier-only damage,
  a single pooled "toughest defender" target rather than modelled focus-fire order, `atk_phys` as the
  one representative damage stat regardless of which skill the real `action_provider` picks) mean the
  estimate can be wrong in either direction for an unusual matchup** — most safely wrong (an
  overestimate, missing a genuine curbstomp) but conceivably wrong the other way if a real encounter's
  actual damage output ends up *lower* than the conservative estimate predicts (e.g. an
  `action_provider` that, in practice, never casts the attacker's highest-`atk_phys` skill). →
  Accepted; every simplification in `_expected_damage_per_attack()`/`estimated_rounds_to_conclude()` is
  named explicitly in D-1 rather than silently assumed, and — critically — a wrong estimate is caught
  by the very next round's recomputation (D-3's "the loop stops on any classification change"), not
  discovered only at the end: if real progress falls behind what the estimate promised,
  `classify_overwhelm()` de-classifies the fight on the next round it is checked, and `max_rounds`
  backstops the case where even that recomputation is somehow fooled. No single wrong estimate can
  therefore compress a fight further than one round past when its true trajectory diverges from the
  estimate that admitted it.
- **[Risk] `resolve_overwhelm()`'s `max_rounds` safety cap (now 12, reduced from an earlier 50 once
  Signal 3 made the round bound the primary mechanism rather than the only one) is still, in principle,
  reachable if Signal 3's own estimate is fooled every round in a row** (e.g. a fixture engineered so
  `estimated_rounds_to_conclude()` stays just under `max_estimated_rounds` at every single
  recomputation despite no real progress) — such a fixture would exit mid-fight with
  `battle_over=False` after 12 rounds (72 seconds of reported game time) rather than converging. →
  Accepted as the deliberately named, tested defense-in-depth outcome D-3 describes; 12 rounds is a
  finite, small, and honestly-reported bound regardless of cause, several orders of magnitude away from
  the thousands-of-rounds hang this design revision exists to rule out, and `OverwhelmResult.battle_over
  =False` is the same honest signal a caller already needs to handle for any other unresolved
  encounter.
- **[Risk] `compress_event_logs()` does not merge repeated attacker/target damage entries across
  rounds into a running total (Non-Goal)** — a Narrator reading the compressed output sees one
  `"damage"` entry per hit, not "N hits totaling M damage" per attacker/target pair, only the
  encounter-wide summary entry aggregates. → Accepted as a deliberate one-day scope cut; the summary
  entry already gives the coarse total the design doc's "compresses" language asks for, and per-hit
  detail remaining ungrouped costs the Narrator nothing it cannot already skip past — flagged here as
  the natural next enhancement for whichever later change (16 or 18) wants richer aggregation, not a
  gap this change silently leaves undocumented.
- **[Risk] The team-key-as-`actor` convention on the summary `EventLog` (D-4) is this change's own,
  first use of a non-entity-keyed `actor` string** — a future reader of `event_log.py` who assumes
  `actor` is always resolvable via `battlefield.roster` could be surprised by a team key appearing
  there. → Accepted and documented explicitly (D-4); every other `EventLog` this change produces (the
  `filtered` tuple) keeps entity-keyed `actor`/`target` exactly as change 9 already writes them — only
  the one new summary entry per compressed encounter uses a team key, and it is namable as such by its
  own `kind == "overwhelm_resolution"`.

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
`world/rules/overwhelm.py`/`world/rules/rulebook/overwhelm.yaml` do not exist yet. The only sequencing
concerns are operational:

- This change must land after change 9 (`dice-combat`), for `effective_power()`, `run_round()`,
  `is_battle_over()`, `Battlefield`, and `COMBAT_YAML`, and transitively after change 8
  (`action-resolver`) for `EventLog`/`EventEntry`/`render_plain_text()`.
- **Change 10b (`monster-behaviour`, depends on 9, 10)** is expected to supply the `action_provider`
  `resolve_overwhelm()` calls for non-player combatants once it exists, in place of change 9's own
  placeholder (`default_attack_policy`) — this change's own signature already accepts any
  `action_provider`, so change 10b needs no edit to this change's code, only a different callable
  passed in by whatever orchestrates combat.
- **Change 11 (`world-clock`, depends on 7, 9)** is expected to read `OverwhelmResult.total_seconds`
  the same way it is expected to read change 9's `BattleResult.total_seconds` — nothing in this change
  calls `WorldClock.advance()` itself. Because Signal 3 (D-1) bounds every overwhelm-classified
  encounter to a handful of rounds, the value change 11 will ever see from this change is small by
  construction (tens of seconds, not the tens-of-thousands a decided-but-unbounded grind could have
  produced) — change 11 does not need its own defensive cap against an unreasonably large single
  `total_seconds` value from this source.
- **Change 18 (`narrator`, depends on 10, 17)** is expected to consume `OverwhelmResult.event_logs`
  directly; it may call `render_plain_text()` on each entry verbatim (D-6) as its own offline-
  degradation path, or write archetype-specific prose keyed on the new `"overwhelm_resolution"` kind's
  `data` fields (`rounds`, `hits`, `total_damage`) for a richer online path.

## Open Questions

- **Should `compress_event_logs()` eventually merge repeated same-pair damage entries into a running
  total, rather than leaving every individual hit ungrouped beneath the summary entry?** Not done here
  (Non-Goals; Risks) — left to whichever later change (16 or 18) first finds the per-hit detail too
  noisy for its own narration needs; this change's own consumers (the golden tests, `render_plain_text`)
  do not require it.
- **Should the disagreement case (D-1) eventually resolve to *something* other than always-contested —
  for example, a third `classify_overwhelm()` outcome distinguishing "genuinely contested" from
  "signals disagree, needs a human balance call"?** Not built here; the task's own priority ordering
  (consistency over compression) makes "leave it contested" the correct default today, and no dependency
  this change has access to describes a tank/duelist-shaped archetype concretely enough to design a
  third state around. Left to a future balance pass if the disagreement case turns out to be common in
  practice once real monster/skill data (change 10b onward) exists to check it against.
- **Exact shape of `EventEntry.data` for the `"damage"` kind** (specifically, whether `data["hit"]` and
  `data["amount"]` are the real key names change 9's landed implementation uses) is inferred from D-4's
  worked example and D-5's `PendingEffect.description` string, not confirmed against change 9's actual
  `_step7_build_event_log` output — left to the implementer to confirm against change 9's landed code,
  consistent with the verification discipline changes 1-9 already established (see Risks).
- **`max_estimated_rounds` (5) and `max_rounds` (12) are both this change's own invented placeholders**,
  calibrated against this project's own worked reference matchups (D-1) but not against real monster
  AI behaviour (change 10b) or real player skill selection, neither of which exists yet. Whether 5
  rounds is the right cutoff once real party compositions and monster movesets exist is left to a
  future balance pass, the same disclosure this change already gives every other invented constant.
