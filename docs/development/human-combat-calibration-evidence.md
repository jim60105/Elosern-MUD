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
under test. The matrix's synthetic weapon rows declare `adjustments={}`, so they isolate
the `weapon_multiplier` term alone; weapon gear-stat composition (the flat `atk_phys` and
`agility` bundles) is measured by the parity probe's real authored weapons below.

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

Compound budgets, each per-strike magnitude expressed against case 1's 40:

- Case 8: coefficient 2 x critical 2 x weapon 1.5 = 6x, so 240 per strike and 480 over
  the two strikes the policy declares.
- Case 12: coefficient 2 x critical 2 x matched conditional 2 x weapon 1.5 = 12x
  (480), then the 10-point rider is added before the authored scale
  (`(480 + 10) x 2 = 980` per strike, 1960 over the two strikes). The rider rides
  pre-scale, so it contributes 20 to the scaled strike, not 10.

Case 9 pins the ordering: the authored scale is applied before the 0.35 Defend reduction
(`floor(30 x 0.65) = 19`); the reverse composition (`floor(60 x 0.65) = 39`, then the 0.5
scale) records 20, and the test asserts both literals so a reordering cannot pass.

The six invariant controls, added once: an unchecked recipient receives no Dodge roll
while another roster key's declaration is active; per-recipient AREA Dodge differs by
declaration (the declared dodger misses on the same face that lands on its neighbour); a
damaging upkeep tick ignores Defend (a declared defender still takes the full 10);
explicit bypass ignores Defend; the nonlethal projection follows the final direct amount;
and literal base traits, `skill_proficiency`, `affinity_elements` and strike count are
unchanged across the whole matrix.

### Estimator-versus-settlement parity

Backend: Evennia test runner on SQLite (`server/db/evennia-test.sqlite3`); Python
3.13.14; measured revision `d5862c29` (re-verified unchanged at the branch tip); no seed
(fixed faces, no live services). The parity probe equips the authored `plain_sword` and
`military_s_sword` through the ordinary `add_item`/`toggle_equipment` rules and compares
the two paths on the same fixed matchup (monster attack 40 base, target hp 500 /
defense 10 / agility 20, defender threshold 71, retention 0.8):

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

## Combined player/enemy encounter calibration

`party-combat-encounter-calibration` (change 19 of the party-combat batch) measures the
bounded combined player/enemy encounter set: exactly **eight human-only cells × seeds
0-3**, i.e. 32 encounter trials, under the same 200-round bound the preceding probes
used. No new species, elf/beastfolk target or calamity cell is added, and the
calibration-only high probes stay unshipped.

Backend: Evennia test runner on SQLite (`server/db/evennia-test.sqlite3`); Python
3.13.14; measured revision `169e7299`, re-confirmed row for row at the branch tip
`4bc68a1e`; deterministic per trial (each trial seeds `random` with its cell's seed,
one trial per cell/seed pair). Focused label:
`uv run --locked --env-file=<file> evennia test --settings test_settings.py --keepdb
world.rules.tests.test_human_combat_calibration.EncounterCalibrationTests`.

### How one trial is driven

Each cell builds real humans — the F-rank creation kit build, or the rank's restricted
senior constructed from the real authored profile and equipped with its real weapon,
armor and accessory through the ordinary inventory/equipment rows, with its exam
restriction activated — plus the cell's monster (a real species individual, or the
existing synthetic `high_lower`/`high_upper` probe). Each ally's selection is submitted
through the real persistent-draft facade (`submit_player_action()`,
`submit_player_item_use()`, or the tactical entry kind via `confirm_actor_command()`),
so an ally acts only from a submitted command and an omitted command leaves the round
unresolved (asserted separately: the missing-command probe resolves nothing and neither
side's HP moves). Every resolved round carries the simulation marker, and each trial
asserts that ordinary growth, unlocks and reward state are unchanged. The enemy keeps
its shipped defensive and evasive skills.

The scripts are explicit and bounded. A single-member cell selects the first affordable
permitted attack from its own chain (`true_sword_saint`, `blade_saint_arts`,
`thousand_blade_art`, `tendon_sever`, `flowing_strikes`, `basic_swordplay`, default
`basic_attack`). The three-member D party additionally declares `defend` (member 0,
round 2), `dodge` (member 1, round 3) and `taunt` (member 2, round 4) as round-start
tactical entries, makes member 1's attack selection explicit on its non-tactical third
rounds (behaviourally the same chain fall-through the other members use, since its
round-3 slot is its own Dodge declaration), and offers member 2's own-inventory
`healing_potion` on rounds 2 and 5 to the party's most wounded living member. Each
selection is checked against the same public preflight the facade enforces, so an
invalid action is never silently replaced; every trial records its rejections and all 32
trials recorded zero.

The 32 trials run twice: a baseline pass and the same 32-trial selected-value pass. The
selected-value pass records the balance values it consumes through their real consumer
sources and reproduces the baseline taxonomy and round counts exactly.

### Selected values: every eligible value retained

The tuning evaluation compared the 32 measured baseline trials against the finite
eligible surface. No observed combined result identified an overbudget authored
magnitude, so every eligible value is **retained**, and the selected-value pass measures
the same values:

| Surface value | Initial | Selected | Observed effect on the 32 trials |
|---|---:|---:|---|
| `damage.mitigation_k` | 40 | **40 (kept)** | Every cell resolved within its bound; no cell unfinished, all rejections zero |
| `tactics.defend_reduction` | 0.35 | **0.35 (kept)** | The D party's round-2 Defend resolved with no rejected selection |
| `tactics.dodge_threshold_bonus` | 25 | **25 (kept)** | The D party's round-3 Dodge resolved with no rejected selection |
| realistic weapon factors in force | `1.05` common / `1.10` uncommon / `1.15` rare / `1.25` legendary | **kept** | Measured per cell: F `plain_sword` 1.05, E `military_e_sword` 1.05, D/C `military_d_sword`/`military_c_sword` 1.10, B `military_b_sword` 1.15, S `military_s_sword` 1.25 |

The finite surface also admits at most the two existing physical skill definitions the
preceding factor-budget evidence used as its conditional and multi-strike probe cases.
Recorded keys: **`flowing_strikes`** (coefficient 1.4, one extra strike — the
two-strike case; it is the D cell's measured selection) for the multi-strike probe, and
**`blade_saint_arts`** (coefficient 4.0, `bypass_defense=True`) for the conditional
probe. Both were **considered and unchanged**. One qualification is recorded rather than
glossed: `blade_saint_arts` declares an *empty* predicate, so it is an unconditional
bypass, not a matched conditional multiplier; every shipped skill that declares a
non-empty matched predicate (`light_arrow`, `penitent_touch`, `judgment_strike`,
`heavens_judgment_light`, `crystal_shatter`, `earths_judgment`) carries a **magic**
damage effect, which no cell's physical chain selects and which the physical weapon
factor never touches. It is therefore the nearest shipped physical analogue of the
conditional probe case, recorded as such. No cell's observed results would have been
changed by either key, and neither was changed.

### Measured eight-cell outcomes (seeds 0-3, baseline and selected-value passes)

Rounds are the executed rounds per seed; medians are over the four seeds. The selected
pass reproduced every count, HP and rejection exactly.

| Cell | Rounds (seed 0/1/2/3) | Median | Monster defeats | Retreats | Human losses | All standing | Unfinished | Rejects | Final human HP |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| F creation kit vs grain pecker | 8 / 7 / 12 / 6 | 7.5 | 4/4 | 0 | 0 | 4/4 | 0 | 0 | 159 / 150 / 157 / 157 |
| E restricted senior vs E ordinary | 6 / 4 / 6 / 4 | 5.0 | 4/4 | 0 | 0 | 4/4 | 0 | 0 | 96 / 88 / 88 / 92 |
| D restricted party (3) vs D ordinary | 5 / 3 / 5 / 2 | 4.0 | 4/4 | 0 | 0 | 4/4 | 0 | 0 | 82,110,110 / 110,110,110 / 82,110,110 / 96,110,110 |
| C restricted senior vs C ordinary (real policy) | 8 / 6 / 13 / 6 | 7.0 | 4/4 | 0 | 0 | 4/4 | 0 | 0 | 85 / 48 / 88 / 85 |
| B restricted senior vs B ordinary | 2 / 2 / 3 / 2 | 2.0 | 4/4 | 0 | 0 | 4/4 | 0 | 0 | 132 / 132 / 106 / 132 |
| B restricted senior vs high-lower probe | 11 / 5 / 12 / 10 | 10.5 | 2/4 | 0 | 2/4 | 2/4 | 0 | 0 | 34 / 59 / 0 / 0 |
| B restricted senior vs high-upper probe | 12 / 5 / 11 / 7 | 9.0 | 0/4 | 0 | 4/4 | 0/4 | 0 | 0 | 0 / 0 / 0 / 0 |
| S restricted senior vs high-upper probe | 2 / 2 / 5 / 2 | 2.0 | 4/4 | 0 | 0 | 4/4 | 0 | 0 | 200 / 200 / 183 / 200 |

The B-vs-high-upper losses leave the probe at 391 / 583 / 489 / 502 of its 700 HP, so the
upper-tier cell remains a real boundary rather than a defeat that never damages its
opponent. The high-upper probe is a calibration-only, unshipped reference: the S cell's
sampled 4/4 result promises neither universal S-tier victory nor any all-standing
A-tier party safety, and no calamity cell is measured here.

The harness bound is 200 rounds, as the calibration boundary requires; the engine's own
session cap (`combat.yaml` declares no `max_rounds`, so the shipped default of 100
applies) is lower, so a trial that neither side could finish would settle as that cap
and be reported as `unfinished`. No measured cell is unfinished: every trial reached a
terminal outcome, and the longest is the 13-round C trial.

### Diagnosis: measured divergences from the historical projected table

The historical table above is pre-cutover projected evidence and is deliberately not
re-measured. Every divergence in the new measurement is diagnosed here rather than
absorbed:

- **C cell (historical 1/4 defeats + 3/4 retreats; measured 4/4 defeats, 0 retreats).**
  The cell does resolve through the shipped `monster_behaviour_policy` — the recorded
  per-trial enemy-policy provenance shows real-policy decisions only for this cell and
  deterministic stand-and-fight decisions only for the others — so the cliff stepper was
  free to flee. It did not reach its flee condition under these seeds: the C senior's
  measured selection (`tendon_sever` with the authored `military_c_sword` factor 1.10)
  closes the fight in 6-13 rounds. Defeat and retreat remain separately reported and an
  escape is never recorded as a zero-HP defeat.
- **B senior vs high-lower probe (historical 4/4 defeats ≈14 rounds; measured 2/4
  defeats + 2/4 human losses, median 10.5).** The historical row predates the authored
  weapon factors; the B senior's measured selection is `thousand_blade_art` with
  `military_b_sword` 1.15 against a 320-HP probe, so the matchup is now a race that
  splits 2/4 across these seeds. The loss rows leave the probe at 55 and 81 HP, i.e. a
  bounded near-loss, not a mis-equipped kit. No authored value was changed: nothing in
  the eligible surface would change this cell without a global weakening, and the
  observed split is a recorded high-tier boundary outcome rather than a defect.
- **S senior vs high-upper probe (historical 3/4 defeats ≈54 rounds; measured 4/4
  defeats, median 2).** The S senior's measured selection is `true_sword_saint`
  (coefficient 5.5, defense bypass) landing 330-619 per round against the 700-HP probe,
  so that probe no longer challenges the strongest restricted senior. Recorded as a
  measured magnitude observation for the later tier-balance work: `true_sword_saint`
  is not on this change's eligible surface, and lowering `K`, the tactical constants or
  the weapon factors to lengthen this cell would be exactly the unsupported global
  weakening the batch contract forbids. No value was changed.
- **F/E/D/B-ordinary cells.** Same outcomes as the historical table (defeat, all
  standing, zero rejects); the medians are smaller because the authored weapon factors
  now apply, which is a measured effect of the previous slice rather than a regression.

### Diagnosis: real-kit restriction mismatch resolved during the run

The three-member D party's restricted members cap **effective max HP at 110** (the
rank's authored reducing ceiling) while the underlying `hp` trait base stays 200. The
supporter's first inventory-item selection was therefore rejected `hp_full` at 110/200,
because the script's wounded test used the trait base instead of the restricted
ceiling. Diagnosed and fixed in this change by gating the item turn on the same public
item preflight the facade itself enforces: the selection is now a legal use of the real
consumable on the party's most wounded living member, and all 32 trials record zero
rejections. The diagnosis changed no approved value; the restricted ceiling and the
consumable's own declaration are untouched.

### Qualification: probe combat policy

The probes patch the session's combat policy to the simulated marker so that no ordinary
growth, unlock or reward occurs. That same marker suppresses the hostile session's
per-entity `nonlethal_keys`, which normally floors allied companions at 1 HP and marks
them knocked out; the party cells are therefore measured under stricter-than-shipped
companion lethality, and the D cell's all-standing result is the stricter measurement.

### Traceability

The three discoverable tests that substantively establish this change's added
`human-combat-calibration` requirement ("Real party encounter evidence records selected
values and bounded outcomes") are
`EncounterCalibrationTests.test_eight_encounter_cells_run_explicit_draft_commands_over_four_seeds`,
`EncounterCalibrationTests.test_selected_values_reproduce_the_measured_encounter_outcomes`
and
`EncounterCalibrationTests.test_an_ally_without_a_submitted_command_never_auto_attacks`.
They carry the change's own canonical annotation once the delta spec is synced into
`openspec/specs/`, which is the first gate that can resolve that identifier; until then
they carry the existing `human-combat-calibration` requirement IDs they also establish.
Shard ownership is unchanged: the module keeps its single existing entry in
`.github/evennia-shards.json`, and no test module was added, moved or renamed.
