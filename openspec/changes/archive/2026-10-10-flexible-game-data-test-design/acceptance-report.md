# Implementation acceptance evidence (package D)

Records the closure of the eight serial work packages. Every claim below is
either an observed command result recorded in this file or a commit that can be
read on `feat/flexible-game-data-test-design`; nothing here is a re-statement of
the plan.

## D.1 Package state and evidence

| Package | State | Evidence (`cargo` = the package's own commit) |
| --- | --- | --- |
| A: shared oracles and bookkeeping | complete | `454a5a07`; the deltas of `test-data-independence` and `spec-test-traceability` are in `openspec/specs/`, `AGENTS.md` and `docs/development/evennia-testing-guide.md` carry the three assertion roles |
| B: delivered monster data and representative smoke | complete | `18fff9b1`; the four monster capability deltas are in `openspec/specs/`, `docs/lore/monster-creation-guidelines.md` carries the authoring boundaries |
| C1: lore, construction, skills and lineage | complete | `6d94ab1c` plus the integration commit; `test_skill_lineage.py`'s freeform ladder now runs on a file-local synthetic ladder, `test_profession_assembly_loader.py` no longer derives its expectation from the constructor under test, `test_clock.py`'s booked-practice expectations read the declared per-hour rate and level threshold |
| C2: equipment, economy, guild hosts and restrictions | complete | `f87f3ee8`; the section-5 table, the price-scale pairs, the band endpoints and the normal-host stat tuples are gone, `docs/development/adding-items.md` carries the boundary |
| C3: church, vessel and affinity | complete | `1e42e5b5` plus `bf5a8b76`; the acceptance curve, payout band, accrual rows, vessel grace and the affinity budget/gain/penalty knobs are read from their declarations |
| C4: sexual catalogs and derived state | complete | `d5c20799`, `f82de467`, `f213bd08`; the twelve classified catalog files no longer carry per-act unlock/base/ratio tables, the state/transition/pleasure/climax suites run on fixed synthetic fixtures |
| C5: buffs, world time, wilderness and calibration | complete | `a2aa1cb2`, `553555a7`; buff durations/charges/ceilings, the defeat-recovery wake target and the calibration victory pins are gone or derived |
| D: integrated full-scope acceptance | complete | this file plus the final gate run below |

## D.1 Assertion-to-defect-to-requirement mapping

The mapping is recorded at capability-requirement-file granularity; the
per-assertion detail (removed literal, replacement, detected defect) is in the
package commits' diffs. The requirement identifiers are the canonical ones
`tools.spec_traceability list` derives from the current headings; the final
`spec traceability` run below confirms every one still has a substantiating
test execution.

| Capability (delta) | Requirement(s) touched | Test file(s) carrying the migrated association | Defect the retained assertion detects |
| --- | --- | --- | --- |
| `test-data-independence` | 1 modified + 3 added | `tests/test_spec_traceability.py`, the lint gate itself | a migrated assertion accepted on stale evidence; a contract file losing its tag/ledger agreement |
| `spec-test-traceability` | 1 added | `tests/test_spec_traceability.py` | an association kept after its assertion was replaced |
| `monster-species-registry` | 2 modified | `world/lore/tests/test_monster_species_content.py`, `world/rules/tests/test_npc_roster_validation.py` | missing/partial profile, wrong variant selection, a multiplier baked into storage |
| `monster-individual-construction` | 2 modified | `world/lore/tests/test_monster_species_content.py` | construction not applying the declared profile/kit, refill after reload |
| `monster-resource-abilities` | 10 modified | `world/rules/tests/test_crocodile_resource_skill.py`, `.../test_sway_whistle_sparrow_resource_skill.py`, `.../test_tide_lamp_crab_resource_skill.py`, `world/skills/tests/test_skill_registry/test_registry_contract.py` | wrong selection, wrong recipient, missing payment, credit on requested instead of actual loss |
| `monster-action-policy` | 3 modified | the three resource-skill modules | a creature-specific branch, a skipped ordinary fallback |
| `lore-registries` | 7 modified | `world/lore/tests/test_races.py`, `test_magic.py`, `test_titles_registry.py`, `test_npc_tiers.py`, `test_player_presets.py` | crossed power-gap bounds, a broken zero-sum/directional intent, an unresolved reference |
| `entity-trait-scales` | 3 modified | `world/rules/tests/test_race_scale.py`, `test_subrace_order.py`, `test_tier_construction.py`, `test_monster_scale.py`, `test_traits.py` | a band read from the wrong axis, order-of-application regression |
| `starting-companions` | 1 modified | `world/lore/tests/test_player_presets.py`, `world/rules/tests/test_starting_companions.py` | a companion declaration without stage headroom, a lost partner reference |
| `title-system` | 1 modified | `world/lore/tests/test_titles_registry.py` | a non-ascending clergy ladder, an 聖女 display leak |
| `skill-registry` | 3 modified | `world/skills/tests/test_skill_registry/*` | a lost species ownership, a wrong audience/hit index, a damage ability that is not selectable outside combat |
| `skill-lineage` | 8 modified | `world/rules/tests/test_skill_lineage.py`, `world/skills/tests/test_spell_catalogs.py` | a broken prerequisite edge, a ladder rung offered above the tip cap |
| `equipment-effects` | 2 modified | `world/rules/tests/test_equipment_effect_rulebook.py` | a budget violation, an unknown entry field, a non-deterministic rendering |
| `military-equipment` | 2 modified | `world/rules/tests/test_equipment_effect_rulebook.py` | a missing offer/reference, a shared-stock leak, a broken resale relation |
| `masterwork-price-band` | 2 modified | `world/lore/tests/test_economy.py`, `world/rules/tests/test_guild_config/test_item_offer_definitions.py` | a keepsake item becoming tradeable, a band relation inverted |
| `human-guild-hosts` | 1 modified | `world/rules/tests/test_npc_roster_validation.py`, `world/rules/tests/test_human_guild_hosts.py` | wrong declared base/age reaching construction, unregistered gear accepted |
| `guild-exam-restrictions` | 2 modified | `world/rules/tests/test_guild_exam_restrictions.py` | a restriction bypass, a lost lineage effect |
| `combat-modifier-table` | 9 modified | `world/rules/tests/test_combat_modifiers.py`, `..._matched.py`, `..._self_arming.py` | a matched rule not routing its declared adjustment, a merge/conferral regression |
| `church-ordination` | 4 modified | `world/rules/tests/test_church_rulebook.py`, `test_church_accrual.py`, `test_church_enrollment.py` | a gate bypass, negative discipline, a duplicated accrual |
| `saintess-vessel` | 2 modified | `world/rules/tests/test_saintess_vessel_trickle.py`, `world/lore/tests/test_saintess_vessel_grant.py` | a non-holder touched, an idle holder leaving the named band, a double-counted snapshot |
| `affinity-system`, `affinity-cap-break` | 3 modified | `world/rules/tests/test_affinity.py`, `test_affinity_config.py`, `test_party.py` | a cap applied after the gain, budget consumed on rejection, a leaked negative delta |
| `quest-reward-settlement`, `party-system` | 2 modified | `world/rules/tests/test_party.py`, `test_party_follow.py` | a non-atomic reward/leave commit, a lost companion gain |
| `sexual-catalog-*` (5), `sexual-act-effects`, `sexual-state-handler`, `sexual-transition-rulebook` | 20 modified | `world/skills/sexual_acts/tests/*` (12 classified files), `world/rules/tests/test_sexual_state.py`, `test_sexual_transitions.py`, `test_sexual_act_effects/*` | a compound gate omitted, swapped roles, observer credit while alone, a broken comparative-quality relation, a lost exactly-once counter/event credit |
| `buff-handler-integration` | 1 modified | `world/rules/tests/test_buffs.py` | a replayed tick, a lost charge, an expiry that ignores the declared duration |
| `world-clock` | 1 modified | `world/rules/tests/test_clock.py`, `world/maps/tests/test_city_movement_cost.py` | a wrong cost key, an uncharged or double-charged move |
| `wilderness-gateway`, `wilderness-monster-population` | 2 modified | `world/maps/tests/test_wilderness_population.py`, `world/lore/tests/test_wilderness_entry.py` | nondeterministic placement, a wrong density-band comparison |
| `defeat-aftermath-recovery` | 3 modified | `world/rules/tests/test_defeat_aftermath_core/*` | a wrong wake target, a rollback that leaves aftermath state behind, a lost recovery advance |

Result: `tools.spec_traceability check` reports 2077/2077 current requirements
covered, 0 uncovered, 0 errors after every package landed, and the 37 delta
capabilities were applied verbatim into `openspec/specs/` (delta block equals
main-spec block for all 37; no scenario lost).

## D.2 Scoped benign tuning (declaration perturbations, each restored)

Every perturbation was applied to the authored declaration and restored byte for
byte afterwards; no expected-data edit was needed in any run.

| Class | Perturbation | Focused run | Observed |
| --- | --- | --- | --- |
| monster profile | `grain_pecker` profile `mp` 20 → 24 | `world.lore.tests.test_monster_species_content`, `world.rules.tests.test_equipment_effect_rulebook` | 79 tests OK |
| equipment modifier | `wooden_club` `atk_phys` 3 → 4 (inside the common flat budget) | as above | 79 tests OK |
| item effect magnitude | `healing_potion` `amount` 40 → 45 | `world.rules.tests.test_shipped_item_use_regression`, `world.rules.tests.test_buffs` | 91 tests OK |
| buff duration | `dark_weaken` `duration` 15 → 25 | as above | 91 tests OK |
| price/stock | `capital_remedies` `healing_potion` `buy_copper` 100 → 120, `initial_stock` 3 → 4 (inside the potion band) | `test_shipped_item_use_regression`, `test_guild_config.test_price_scaling`, `...test_item_offer_definitions`, `...test_assortment_shop_rules` | 67 tests OK |
| affinity budget/gain | `daily_interaction_cap` 5 → 6, `quest_completion_gain` 2 → 3 | `world.rules.tests.test_affinity`, `test_affinity_config`, `test_party` | 87 tests OK |
| skill cost/magnitude | `tide_devouring_bite` `mp` 10 → 12, drain `fixed:10` → `fixed:12` | `test_crocodile_resource_skill`, `world.skills.sexual_acts.tests.test_solo_catalog`, `world.skills.tests.test_skill_registry` | 74 tests OK |
| unlock threshold | `solo_deep_touch` `masturbation_count` 10 → 12 | as above | 74 tests OK |

Restoration was verified by reading each declaration back (all eight needles
matched) and by the clean `git status` for those paths.

## D.3 Scoped broken perturbations (each restored, with the failing assertion recorded)

| Perturbation | Observed failure |
| --- | --- |
| `grain_pecker` kit pointed at a missing skill key | `MonsterConstructionError: unknown active skill 'grain_shaking_peck_missing'` raised by `construct_species_individual`, and `test_no_registry_string_names_a_skill_behaviour_or_combat_trait` failed on the kit-reference equality |
| crocodile `allowed_species` flipped to the sparrow | `MonsterConstructionError: monster not eligible for skill 'tide_devouring_bite'` in the drain smoke, and `test_tide_devouring_bite_data_contract` failed on the declared species tuple |
| sparrow rider audience flipped `ENEMIES` → `SELF` | `test_grain_shaking_peck_data_contract` failed: `self.effect_policies[1].audience` is `SELF`, not `ENEMIES` |
| crocodile rider `requires_hit_from` set to an out-of-range index 5 | the registry refused to load: `ValueError: skill 'tide_devouring_bite' requires_hit_from index 5 out of range (total effects: 2)` |

The restored fixtures then passed: `test_monster_species_content`,
`test_crocodile_resource_skill`, `test_sway_whistle_sparrow_resource_skill` and
`test_registry_contract` green again after restoration.

Not exercised in this run, with the reason: engine-level payment-skip,
partial-transfer, post-write rollback, post-claim release and persistence-lost
perturbations would require temporarily editing the deterministic engine, which
is outside this change's approved test-design scope. The retained synthetic and
transactional suites for those properties (`test_effect_potency`,
`test_gauge_transfer`, `test_effect_audiences`, `test_item_use`,
`test_progression`, `test_defeat_aftermath_core`, `test_defeat_aftermath_violation`)
are green in the focused runs recorded for packages A and C5.

## D.4 Final gates

| Gate | Observed |
| --- | --- |
| `openspec validate flexible-game-data-test-design --strict` | valid |
| `openspec validate --specs --strict` | 311 passed, 0 failed |
| `openspec validate --all --strict` | 315 passed, 3 failed — the three not-yet-implemented monster proposals, whose own monster-species-registry MODIFIED blocks predate this change's sync (report-only, see below) |
| `uv run --locked python -m tools.contract_gate` | passed: traceability, observability, test-data, shards and contracts (18 contract tests OK) |
| `uv run --locked python -m tools.spec_traceability check` | 2077 requirements, 8470 associations, 2077 covered, 0 uncovered, 0 errors |
| `uv run --locked python -m tools.test_data_lint check` | scanned 1244, flagged 96, quantity-pins 10, violations 0 (unchanged from the baseline) |
| focused changed-suite runs | every module whose assertions were migrated in this change was run green; the per-run counts are in the package commit messages and the three slice reports. `world/maps/tests/test_city_movement_cost.py` appears in the mapping as an unchanged, already declaration-driven file and has no separately recorded focused run |
| aggregate branch-coverage gate | CI-owned: the exact-root ≥80% gate combines the non-browser Evennia, managed-browser and top-level evidence files, and `tools.spec_traceability verify --evidence` is CI-only per AGENTS.md; no local substitute was fabricated |

## D.5 Reported, not waived

- The three active monster proposals (`ridge-burrow-hare-resource-skill`,
  `rock-echo-goat-resource-skill`, `fog-mane-lynx-resource-skill`) fail
  `openspec validate <change> --strict` because their own
  `monster-species-registry` MODIFIED blocks omit scenarios the synced current
  spec now carries. `design.md` declares this as a report-only conflict; the
  exact missing scenario text is recorded in the hand-off report for those
  proposals' owners. This change does not edit them.
- `defeat-aftermath-violation-sequence` is a RETAIN capability in
  `scope-inventory.md` and is not in the change's Modified Capabilities list, so
  the violation-sequence archetype magnitudes (`landed_deltas`,
  `victory_pleasure_delta`, `attempt_duration_seconds`, `attempt_cap`) were left
  as they are. They are the same class of duplicate expectation and would need a
  scope decision before they are touched.
- `world/rules/tests/test_combat_session_recovery.py` carries two wake-fraction
  expectations but is not in this change's inventory
  (`scope-inventory.md` / `test-migration.md`); it was left untouched and is
  reported here.
- `tools/test_data_lint_seed.json` still lists flat module paths
  (`test_defeat_aftermath_core.py`, `test_defeat_aftermath_violation.py`,
  `test_sexual_act_effects.py`, `test_city_movement_cost.py`) from before those
  suites became packages. The lint's stale-path check only covers
  `debt_set | contract_paths`, so nothing fails; the entries are unvalidated
  bookkeeping and pruning them is a separate seed-debt change, not this one.

## D.6 Post-implementation critique and dispositions

An independent critique ran over the finished change (all package commits plus
the three parallel slices). It raised one blocking finding and four
non-blocking observations; every one is dispositioned below, and every fix was
re-verified with a focused run (`test_combat_modifiers` +
`test_human_combat_calibration`, 99 tests OK).

| Finding | Severity | Disposition |
| --- | --- | --- |
| `test_combat_modifiers.py` built percent expectations with `f"{value}%"` while production formats `f"{value:+g}%"`; an integral or positive tuned sum would have failed falsely | blocking | FIXED: all three expectations now use `f"{value:+g}%"`; the earlier partial critique's seven findings were checked again and remain fixed |
| the martial-blessing test selected its church accrual row with an unanchored "first row with a magnitude", which dictionary order would decide once a second such row exists | non-blocking | FIXED without naming the shipped row id (the test-data lint rejects both the row id and a catalog symbol reference): the candidates are collected and their uniqueness is asserted, so a second magnitude-bearing row fails loudly |
| the rewritten calibration probes no longer record the spec's "round medians" | non-blocking | FIXED: `_assert_probe_evidence` now records a round median and asserts only that it is inside the same 1..200 bound as the individual probes, never at a balance target |
| this report overclaimed focused runs and did not mention the stale flat `seedDebtPaths` entries | non-blocking | FIXED here: the focused-run row names the exception (`test_city_movement_cost.py` is unchanged), and the stale seed entries are recorded in D.5 |
| residual literal pins remain in `test_combat_session_recovery.py` and `test_defeat_aftermath_violation/test_archetype_and_rendering.py`, both outside this change's inventory | non-blocking | accepted, no change: they are pre-existing, disclosed in D.5, and are not regressions; they belong to whichever change next touches those capabilities |
