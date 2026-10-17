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
|---|---|---:|---:|---:|---:|---:|---|
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
