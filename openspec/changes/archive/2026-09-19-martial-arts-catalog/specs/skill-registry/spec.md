## REMOVED Requirements

### Requirement: dual_blade_mastery exists as a higher-tier sibling to dual_wield_style
**Reason**: The requirement pins a dev-era single-row declaration contract (`dual_blade_mastery`, 雙刃旋舞, ACTIVE, SINGLE, SP 30, `damage:dark:physical`) for a skill this change re-keys. The move itself survives unchanged as the authored 影流 node `dual_blade_waltz`; only the stale key retires, and its `_mastery` suffix is this project's naming convention for element-mastery passives, which the move is not. The ratified scope also rules out martial data-contract tests: no key-set, node-table, cost, cap, tier or lineage-edge echo.
**Migration**: Delete `test_dual_blade_mastery_is_a_higher_tier_sibling` in `world/skills/tests/test_skill_registry.py`, move 悠花's `dual_blade_mastery` entry in `world/lore/player_presets.py` to `dual_blade_waltz`, and update the category census key set in the same file's classification test. No alias, redirect or deprecated row is left behind: a cast of the retired key rejects as an unknown skill exactly like any never-existing key. The obsolete traceability entry leaves the ledger at the separately authorized main-spec sync. Replace this requirement with the behavioral martial-progression requirement below, backed by synthetic compositions through real settlement.

## ADDED Requirements

### Requirement: Martial arts progression composes executable sword-and-shadow behavior
The martial-arts skill family SHALL provide the documented 劍術 and 影流刀術 progression as executable
skill behavior using the common effect, policy, buff, modifier, cast-condition and lineage mechanisms:
stamina-costed strike rungs settling through the shared damage pipeline at their authored
coefficients; multi-strike rungs resolving two or three independent rolls for one paid cast; an
execution rung ignoring defense subtraction entirely; a devastation rung adding the shipped
fraction-of-maximum-HP term on an area strike; a movement-impairing rider mounted on the struck
target that lowers its agility on the real agility-driven consumers for its authored duration and
then stops; a lingering-wound rider draining the struck target's HP on the shared tick cadence with
defeat credited to the striker; a self-mounted rider raising only its holder's physical attack for
its authored duration; a stance cast-condition that refuses the shadow line to an actor without the
required passive stance and admits it once owned; and two independent lineage trees whose branch
points feed their authored children and whose two-parent canopies unlock only when both parents reach
their thresholds, with tip caps derived from the shared reverse-edge map. Martial skills SHALL carry
no magic-tier label and no freeform scale ladder, and an elementless martial strike SHALL accrue
practice at the neutral affinity factor regardless of the actor's declared affinities.

#### Scenario: The strike ladder settles at its authored coefficient for its stamina price
- **WHEN** a synthetic actor resolves single-target and area martial compositions of ascending
  coefficient against equal targets under a fixed roll, with insufficient stamina on a separate attempt
- **THEN** each landing strike's damage scales by its own authored coefficient through the shared
  damage pipeline, the stamina price is deducted exactly once per resolved cast, and the
  insufficient-stamina attempt rejects before any damage or buff is committed

#### Scenario: The multi-strike rungs resolve their authored number of independent rolls
- **WHEN** a synthetic two-judgment composition and a three-judgment composition each strike one
  target under every fixed hit/miss combination, and separately cross the target's remaining HP on a
  later roll
- **THEN** exactly two and exactly three independent rolls are recorded, each landing roll carries the
  same authored coefficient, resources and practice are paid once per cast, and HP settles through the
  ordered projection with a single terminal defeat entry

#### Scenario: The execution and devastation rungs settle at their authored rungs
- **WHEN** a synthetic execution composition strikes a high-defense target and a synthetic area
  devastation composition strikes full-HP targets
- **THEN** the execution strike's damage skips defense subtraction entirely at its authored
  coefficient, and each devastation hit adds the shipped fraction-of-maximum-HP term after defense

#### Scenario: The impairing rider slows its victim on the real consumers and expires
- **WHEN** a synthetic strike carrying the impairing rider lands on one target while an untouched twin
  fights the same opponents, and the clock then advances past the rider's authored duration
- **THEN** the victim's effective agility falls by the authored flat amount on every agility-driven
  consumer for exactly that duration, the twin is unmoved, and after expiry every consumer reads base
  values with the victim's non-buff state unchanged

#### Scenario: The lingering wound drains its victim and credits the striker
- **WHEN** a synthetic strike carrying the wound rider lands on a target and the clock advances across
  several tick intervals, including past the victim's remaining HP
- **THEN** the victim loses the authored amount per tick for the authored duration, an untouched twin
  loses nothing, and a defeat caused by the drain is attributed to the striking actor

#### Scenario: The canopy's self-mounted rider arms only its holder
- **WHEN** a synthetic canopy composition resolves and the actor, its ally and its target each fight on
  afterwards, then the clock advances past the rider's authored duration
- **THEN** only the acting holder's physical attack rises by the authored flat amount, neither the ally
  nor the target reads any part of it, and the holder's attack returns to base after expiry

#### Scenario: The stance gate refuses and admits the shadow line
- **WHEN** a synthetic actor without the required passive stance attempts a gated shadow composition,
  then acquires the stance and attempts it again, while an ungated root composition is attempted in
  both states
- **THEN** the gated attempt rejects on the unmet cast condition with nothing committed, the same
  attempt resolves once the stance is owned, and the ungated root resolves in both states

#### Scenario: Two independent trees branch and each canopy gates on both parents
- **WHEN** synthetic progressions grind each tree's root chain and branch children, then attempt each
  canopy before one authored parent reaches its threshold
- **THEN** each tree progresses independently through the shared prerequisite engine with no edge
  between them, each branch point admits both of its authored children once met, each canopy rejects
  while either parent is below its threshold and admits only when both are met, and tip caps stay
  derived from the shared reverse-edge map

#### Scenario: Martial skills stay outside the magic ladders
- **WHEN** a synthetic elementless martial composition is resolved by an actor with declared elemental
  affinities and by a control actor with none, and both skills are inspected for tier labelling and
  freeform eligibility
- **THEN** neither actor's accrual differs from the neutral factor, no magic-tier label is produced for
  a stamina-costed martial skill, and no freeform scale ladder is offered for it
