# Human Combat Calibration Runtime Evidence

This document records runtime measurements from bounded resolver probes using real Evennia objects, registered equipment, and persisted restriction overlays.

## Historical Projected Evidence vs. Runtime Measurements

Historical exploration executed 1,554 trials under projected equipment adjustments. Those outcomes established encounter bounds but did not validate persistent hosts or equipment wear restrictions. The real-runtime calibration probes below exercise the authoritative Evennia objects, `ActionResolver`, initiative, `run_round`, and `monster_behaviour_policy`.

### Summary of Sampled Real Matchups (Seeds 0–3, 200-Round Bound)

These matchup counts are **pre-cutover historical evidence**: they were recorded before
`equipment-growth-runtime-calibration` authored the shipped physical weapon factors
described below, so they describe the resolver as it stood then. They remain the
encounter-level reference and are not re-measured here; encounter tuning belongs to
`party-combat-encounter-calibration`.

| Tier / Variant | Human Reference / Policy | Monster Defeats | Retreats | Losses | All Standing | Median Rounds | Notes |
|---|---|---:|---:|---:|---:|---|---|
| **F** / Grain pecker | F 224-pt creation build (plains kit: 7/5/9) | 4/4 | 0 | 0 | 4/4 | ~15 | Stand-and-fight, 0 rejects |
| **E** / Shore walker | E restricted senior (military E pair, limit ring) | 4/4 | 0 | 0 | 4/4 | ~8 | Stand-and-fight, 0 rejects |
| **D** / Wood stalker | 3× D restricted party | 4/4 | 0 | 0 | 4/4 | ~5 | Party clear, all standing |
| **C** / Cliff stepper | C restricted (real monster policy) | 1/4 | 3/4 | 0 | 4/4 | ~6 | Retreats reported separately from defeats |
| **B** / Bank lurker | Restricted B senior (military B pair) | 4/4 | 0 | 0 | 4/4 | ~2 | Clear progression |
| **High Lower** probe | Restricted B senior | 4/4 | 0 | 0 | 4/4 | ~14 | Matches lower high-tier boundary |
| **High Upper** probe | Restricted B senior | 0/4 | 0 | 4/4 | 0/4 | — | Confirms high-upper boundary challenge |
| **High Upper** probe | S senior (military S pair, domain) | 3/4 | 0 | 1/4 | 3/4 | ~54 | Upper challenge; not a comfortable guarantee |
| **Calamity Lower** probe | S senior | 0/4 | 0 | 4/4 | 0/4 | — | Calamity tier exceeds lone human |

### Simulation Discipline
- All trials resolved with `simulated=True` and action context marker `simulated: True`.
- Skill practice XP and unlock progression were strictly frozen (verified against unsimulated control).
- No ordinary defeat rewards or quest kill credits were awarded.

### Attribute Parity
- E vs. Reef warden seed 0 evaluated under Evennia SQLite database test runner matches expected deterministic victory, zero rejected actions, and round termination.

## Equipment growth: authored weapon factors

`equipment-growth-runtime-calibration` selected the shipped physical weapon factors and
the per-rarity `weapon_multiplier` ceilings in `world/rules/rulebook/equipment_effects.yaml`.
They are loaded authored data: no runtime path infers a factor from rarity or progression
(rarity is a load-time budget check only), and every factor is validated against its own
rarity ceiling by the closed loader. The selection is a balance-authoring deliverable;
the probe numbers below are measurements, not balance claims, and no factor is asserted
to be balanced.

| Rarity | Selected ceiling | Initial ceiling | Selected weapon factors (initial `1.0` for every entry) |
|---|---:|---:|---|
| common | 1.10 | 1.0 | `military_e_sword` 1.05, `plain_sword` 1.05, `wooden_club` 1.05, `iron_dagger` 1.05, `hunting_throwing_axe` 1.05 |
| uncommon | 1.15 | 1.0 | `military_d_sword` 1.10, `military_c_sword` 1.10, `hunters_longbow` 1.10, `ashen_scimitar` 1.10, `gilded_saber` 1.10, `steel_fang_dagger` 1.10, `beastfolk_repeating_bow` 1.10, `beastfolk_war_spear` 1.10, `beastfolk_twin_claws` 1.10, `beastfolk_warhammer` 1.10, `great_axe` 1.12, `knight_blade` 1.12 |
| rare | 1.25 | 1.0 | `military_b_sword` 1.15 |
| epic | 1.30 | 1.0 | `military_a_sword` 1.20, `elven_longbow` 1.20, `magic_sword` 1.20, `rose_crest_rapier` 1.20, `dragon_lair_trophy_blade` 1.22 |
| legendary | 1.35 | 1.0 | `military_s_sword` 1.25, `shadow_blade_echo` 1.25, `shadow_blade` 1.28 |

Neutral declarations (explicit `1.0`) are the weapon-slot entries with no physical attack
bonus: `apprentice_focus_staff` (uncommon casting tool), `beastfolk_spirit_wand`
(uncommon casting tool) and `iron_shield` (common defensive off-hand, which in the main
hand would block the off-hand fallback anyway).

### Committed reload growth probe

Engine revision `9979c2ab`; backend: Evennia test runner on SQLite
(`server/db/evennia-test.sqlite3`); Python 3.13.14; deterministic: no seed, one fixed
d100 roll of 60 (a landed base hit, multiplier 1.0) on every staged strike.
Construction and setup: real `PlayerCharacter` objects, ordinary `add_item` grants,
ordinary `toggle_equipment` equips, then `save()`, a **forced** idmapper eviction of both
`ObjectDB` (`flush_instance_cache(force=True)`; an NAttribute-holding object refuses the
soft flush) and `Attribute` (equipment, inventory and traits live in Attribute rows with
their own cache), and a fresh fetch by primary key — every number is read from a newly
loaded instance, never from the handler that wrote it. The probe class runs under Django's
`TransactionTestCase`, not `TestCase`: the latter's enclosing atomic block is rolled back,
which would leave it unproven whether the reads came from committed storage at all. It
also pins the numbers below as literals, so a settlement regression that stopped
consuming the factor cannot pass on ordering alone, and any authored retune must
re-measure this record. True stats: attacker
`hp 200 / mp 100 / sp 100 / atk_phys 20 / agility 10 / defense 40 / magic_power 30`;
defender the same shape with `atk_phys 1`. Adjusted attacks below include the weapon's
flat `atk_phys`, and every adjusted attack (20 / 22 / 32) stays at or below the
defender's defense 40, where the retired subtraction engine dealt nothing at all.

| State (committed, re-read) | Item keys | Factor | Adjusted attack | Successful hit |
|---|---|---:|---:|---:|
| Unarmed baseline | none | 1.0 | 20 | 10 |
| Initial weapon | `plain_sword` | 1.05 | 22 (20 + 2) | 11 |
| Selected upgrade | `military_s_sword` | 1.25 | 32 (20 + 12) | 20 |

The marginal growth is strictly positive (10 → 11 → 20) and the selected factor is the
loaded declaration itself, while base traits, `skill_proficiency`, affinity elements and
owned skills are unchanged across grant/equip/persist. State held only in the writer's
process (an `ndb` entry) is absent from the next freshly loaded instance while the
committed upgrade is still reported, so the record distinguishes committed storage from
in-memory state. A real armor progression on the defender measured monotonic reduction —
no armor (defense 40) 20, `leather_armor`
(defense 44) 19, `military_s_armor` (defense 52) 17 — while the armored defender's own
factor stays the neutral default (armor contributes defense, never a multiplier) and the
attacker's selected factor is untouched by it.

### Independent synthetic arithmetic controls

Fixed literals evaluated on the scalar stage, establishing placement separately from the
registry values above: with `K = 40`, rounded pre-mitigation attack 60 and defense 20 the
strike is 40; the same strike under Defend records 26 (35% reduction, floored); the
declared physical factor 1.5 on the attack term records 60; and below the retired
subtraction threshold (attack 20, defense 30) the strike records 11, growing to 14 with a
1.25 factor. Magic and healing never consume the physical factor: with the same fixed roll
the staged magic strike measured 15 with and without `military_s_sword`, and the skill heal
magnitude measured 30 in both states. Externally attributed physical damage, multi-strike
and critical composition, and main/off-hand precedence with the nonweapon-main-hand
exception keep their existing independent coverage in `world/rules/tests/test_damage_bands.py`
and `world/rules/tests/test_equipment_combat_wiring.py`.

## Combined damage factor budget matrix

`party-combat-factor-budget-calibration` (change 18 of the party-combat batch) records
the finite combined damage factor budget before any selected encounter tuning. The
bounded set is exactly 30 cases: the 12 listed factor combinations run with the actor
sides exchanged (player attacker and enemy attacker, 24 base cases) plus six invariant
controls added once. Encounter outcome selection stays with
`party-combat-encounter-calibration`; nothing here is a balance claim.

Fixed inputs unless a case says otherwise: rounded attack 60, mitigation K 40, defense 20,
both sides' agility 10, and one fixed d100 face (80, a landing base hit; 100 for the
critical controls). The default strike is therefore `round(60) x 40 / (40 + 20) = 40`.
Every expected amount is an independently hand-derived literal evaluated in
`world/rules/tests/test_human_combat_calibration.py::CombatFactorBudgetTests`, against
real `PlayerCharacter`/`Monster` actors with `roll_d100` and the combat modifier bundle
patched to the fixed literals; no expected value is obtained by calling the calculator
under test.

| # | Case (both directions observed) | Inputs that change | Outcome |
|---|---|---|---|
| 1 | physical basic | coefficient 1, weapon 1 | 40 |
| 2 | physical weapon factor | `weapon_multiplier` 1.5 | 60 (counterfactual 40) |
| 3 | magic neutral control | weapon 1.5 declared, magic school | 40 (factor never consumed) |
| 4 | explicit bypass | `unconditional_defense_bypass`, defense 60 | 60 (counterfactual 24) |
| 5 | matched conditional | predicate matched, `attack_multiplier` 2 | 80 (counterfactual 40) |
| 6 | max-HP rider | `max_hp_fraction` 0.1 on HP 100 | 50 (counterfactual 40) |
| 7 | authored scale + rider | scale 0.5 with the rider | 25 (counterfactual 20) |
| 8 | compound A | coefficient 2 x critical 2 x weapon 1.5 x two strikes | 240 per strike, 480 total |
| 9 | Defend ordering | weapon 1.5, scale 0.5, Defend | 19 (counterfactual 30) |
| 10 | Dodge | defender agility 20, declared Dodge | 0 (counterfactual 40) |
| 11 | raw-100 miss | fixed face 100, defender agility 60 | 0 (critical never lands) |
| 12 | compound B | predicate 2 x coefficient 2 x weapon 1.5 x critical 2 x rider 0.1 x scale 2 x two strikes | 980 per strike, 1960 total |

Compound budgets: case 8 composes a 2 x 2 x 1.5 = 6x factor over two existing strikes
(240 = 6 x the case-1 40, 480 total); case 12 composes a 2 x 2 x 1.5 x 2 = 24x factor
plus the 10-point rider over two strikes (980 per strike, 1960 total). Case 9 pins the
ordering: the authored scale is applied before the 0.35 Defend reduction
(floor(30 x 0.65) = 19; reducing before scaling would read 20).

The six invariant controls, added once: an unchecked recipient receives no Dodge roll
while another roster key's declaration is active; per-recipient AREA Dodge differs by
declaration (the declared dodger misses on the same face that lands on its neighbour); a
damaging upkeep tick ignores Defend (a declared defender still takes the full 10);
explicit bypass ignores Defend; the nonlethal projection follows the final direct amount;
and literal base traits, `skill_proficiency`, `affinity_elements` and strike count are
unchanged across the whole matrix.

### Estimator-versus-settlement parity

Backend: Evennia test runner on SQLite (`server/db/evennia-test.sqlite3`); Python
3.13.14; feature tip `d5862c29`; no seed (fixed faces, no live services). The parity
probe equips the authored `plain_sword` and `military_s_sword` through the ordinary
`add_item`/`toggle_equipment` rules and compares the two paths on the same fixed matchup
(monster attack 40 base, target hp 500 / defense 10 / agility 20, defender threshold 71,
retention 0.8):

| State | Adjusted attack | Factor | Settled average over 100 faces | Estimator projection |
|---|---|---:|---:|---:|
| unarmed | 40 | 1.0 | 13.12 | 13.12 |
| authored initial `plain_sword` | 42 (+2 atk) | 1.05 | 14.35 | 14.35 |
| authored selected `military_s_sword` | 52 (+12 atk, +4 agility) | 1.25 | 24.18 | 24.18 |

The selected row's solid band shifts with the weapon's +4 agility (adjusted agility 14,
margin `roll - 57`), so faces 57..96 land 52, 97..99 land 78 and the raw-100 critical
lands 104: `(40 x 52 + 3 x 78 + 104) / 100 = 24.18`. The estimator's own read path
(`DecisionReads.weapon_multiplier`) reports exactly the declaration the settlement read
path (`equipment_weapon_multiplier`) consumes, so the factor has one authored source and
no duplicated balance constant; the analytic all-face projection and the settled average
agree in every state.

Shard ownership: the extended module
`world/rules/tests/test_human_combat_calibration.py` keeps its single existing entry in
`.github/evennia-shards.json`; no module was added, moved or renamed.
