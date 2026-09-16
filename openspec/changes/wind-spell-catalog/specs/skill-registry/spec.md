## REMOVED Requirements

### Requirement: SKILL_REGISTRY contains the full 風-element spell set
**Reason**: The old requirement mandates a duplicated dev-era ten-row data contract (the 2026-08-12 set — no prerequisites beyond a partial chain, no coefficients, a display-only `bounds`-ceiling mobility illusion with no settlement consumer, no knockback/multi-strike/devastation/execution behavior). The ratified wave NON-GOAL rules out wind catalog/data-contract tests: no key-set equality, no row mirroring, no MP-cost/cap/tier table assertions, no echo of the wind.md table.
**Migration**: Delete `WIND_SPELL_CATALOG` and the echo methods of `WindSpellCatalogTests` in `world/skills/tests/test_spell_catalogs.py` (builder-shape/parse-dispatch MECHANIC tests relocate beside the remaining builder users the fire way), the wind tier-label echo row in `world/skills/tests/test_cost_tiers.py`, and the obsolete traceability/freeze entries during the separately authorized main-sync; the retired dev-era buff keys' `test_buffs.py` numeric pins (`wind_haste`, `wind_haste_domain`) retire with the rows (per D6, stripped to load/apply/presence — never re-pinned, no row mirroring added). Replace this requirement with the behavioral wind-progression requirement below, backed by synthetic compositions through real settlement.

## ADDED Requirements

### Requirement: Wind spell progression composes executable speed-and-knockback behavior
The wind spell family SHALL provide the documented 動作與閃避 progression as executable skill behavior using the common effect, audience, policy, buff, modifier, and lineage mechanisms: timed self/ally agility ladder rungs mounted as detectable buffs and settled through the shared merged combat-modifier bundle so the authored flat agility adjustments move the real agility-driven consumers (to-hit both poles, overwhelm estimation, resist scoring, flee contest) for exactly the authored durations and then stop; a same-axis bipolar rung whose mount raises its holder's agility while lowering its holder's attack accuracy through one validated modifier rule; an area ally rung whose agility adjustment lands on allies only, its defender-side term acting as evasion against incoming single-target strikes; knockback area rungs mounting the positional-marker rows at their authored world-second durations on enemy audiences through the same-settlement effect component (never a reflected or delayed reaction rule), with the shipped cross-primitive ground-marker sweep and the impossible-recipient refusals observing through the real casts; an unconditional two-roll single-target rung settling two independent strikes for one paid cast through the shared ordered-projection settlement; a 處決級 execution rung ignoring defense subtraction; devastation rungs at the shipped fraction magnitude; and the two-root branching lineage gating every rung through the shared prerequisite engine with the two-parent canopy unlocking only at both authored thresholds.

#### Scenario: The agility ladder speeds its holder on the real consumers and expires
- **WHEN** a synthetic self-cast composition mounts the authored ladder rung and the holder resolves physical exchanges and a flee contest against a control twin, then the clock advances past the authored duration
- **THEN** the holder's effective agility adjustment equals the authored flat rung on every agility-driven consumer for exactly the authored duration, the control twin without the mount is unmoved, and after expiry every consumer reads base values with the holder's non-buff state unchanged

#### Scenario: The bipolar rung trades accuracy for speed on its holder alone
- **WHEN** a synthetic carrier of the authored bipolar mount attacks and is attacked while a control twin fights the same opponents under fixed rolls
- **THEN** the carrier's own strikes carry the authored accuracy penalty while its defender-side agility raises its dodge threshold, the control twin shows neither pole, and the mount's non-holder state is untouched

#### Scenario: The ally domain speeds allies and skips enemies
- **WHEN** a synthetic area ally composition mounts its authored agility rung on a mixed battlefield of allies and enemies
- **THEN** every ally holder reads the authored flat agility adjustment on the merged bundle, no enemy reads any part of it, and an enemy's incoming single-target strikes against the allies resolve against the raised dodge thresholds

#### Scenario: The knockback storms hurl enemies out of position and sweep their footing
- **WHEN** a synthetic knockback area composition lands on enemies — one carrying a live ground-marker hazard and an ordinary buff, one defeated mid-settlement, and allied targets — and afterwards a displaced victim's ally attempts a single-target physical strike on it while a magic cast at it resolves
- **THEN** each living enemy target carries the authored positional row at its authored world-second duration with the out-of-position fact true, the ground-marker victim's hazard instance is swept at mount while its ordinary buff persists, the defeated recipient is refused, allies carry nothing, the follow-up melee strike against the displaced victim is gated, and the magic cast lands normally

#### Scenario: The unconditional flurry resolves two independent strikes for one cast
- **WHEN** a synthetic 連續兩次判定 composition strikes one target under each fixed roll pair (hit-hit, miss-hit, hit-miss, miss-miss) and separately crosses the target's remaining HP on the second roll
- **THEN** exactly two independent rolls are recorded with the authored coefficient on each landing strike, resources and practice are paid once, HP settles through the ordered projection with a single terminal defeat entry, and a policy-free single-strike control on the same target still rolls once

#### Scenario: The execution and devastation rungs settle at their authored rungs
- **WHEN** a synthetic 處決級 composition strikes a high-defense target and separately the authored devastation composition strikes a full-HP target under the shipped fraction rung
- **THEN** the execution strike's damage skips defense subtraction entirely at the authored coefficient, and the devastation strike adds the authored fraction-of-max term exactly like the shipped devastation rungs

#### Scenario: The two roots branch and the canopy gates on both parents
- **WHEN** synthetic progressions grind the mobility root chain and the destruction root's branch chains, then attempt the canopy before one authored parent reaches its threshold
- **THEN** each root progresses independently through the shared prerequisite engine, the branch point admits both authored children once met, the canopy rejects while either authored parent is below its threshold and admits only when both are met, and prerequisite caps stay derived from the shared reverse-edge map with leaves at the shared tip cap

#### Scenario: Retired dev-era keys resolve as ordinary rejections
- **WHEN** a caller casts a never-existing wind key through the ordinary cast surface after replacement, or applies the retired dev-era mobility buff keys
- **THEN** each rejects with the existing unknown-skill or unknown-definition reason exactly like any never-existing key, and no alias, redirect or deprecated row exists that any cast or buff path could land on
