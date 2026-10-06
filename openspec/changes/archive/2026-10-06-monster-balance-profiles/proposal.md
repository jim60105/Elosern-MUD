## Batch:

- depends-on: monster-species-registry, monster-identity-construction, monster-site-placement, monster-quest-objectives (all landed and archived 2026-10-06). This change fills the balance-gated slots the registry change declared, flips the numeric source the construction change reads, and is the prerequisite the placement and quest changes' own proposals named for publishing numbered content. This is the `monster-balance-profiles` change that `monster-species-registry`'s proposal records as "a separate balance-approval content change will populate them".
- conflicts: file-level, serialized after this change: `monster-regional-species-hunts` and `monster-site-clear-out-hunts` both depend on the numbers and on the amended design document; they touch no file this change edits except `docs/superpowers/specs/2026-10-05-monster-data-model-design.md` (read-only citations there). `world/lore/monster_species.py`, its test module and `tools/test_data_freeze.json` are touched by this change only within this batch. `.github/evennia-shards.json` is not touched by this change (the existing `world.lore` package label already owns every `world/lore/**/test*.py` module).
- external-prerequisite: user balance approval — **GRANTED 2026-10-06 for the twelve first-batch variants and for the hunts published by the two dependent changes**. The numbers and grades below are the user's decision; this change encodes them literally and does not re-derive, re-tune, or re-round them.
- external-prerequisite: the six special abilities (風吹落穀、擬燈發光、壓土築埂、接觸吸取魔力、聚霧亂向、敲岩共鳴) still have no executable mechanics and remain an external prerequisite owned by other work. This change registers no skill, behaviour profile, or mechanic for them and authors no MP/SP/`magic_power` value on their behalf; the approved profiles carry `mp = 0` and `sp = 0` as authored literals, and `magic_power = 0` because every threat tier's magic band is deliberately `(0, 0)`.

## Why

`docs/superpowers/specs/2026-10-05-monster-data-model-design.md` §8 lists three external prerequisites; prerequisite (一) — user balance approval for each variant's complete numeric profile and final guild danger grade — was unmet when the four monster changes landed. Every shipped variant therefore carries `combat_profile=None` and `danger_grade=None`, every species-backed individual is built through the interim tier-band rule (`NUMERIC_SOURCE_INTERIM_TIER_BAND`), and no hunt that names a species and a number can lawfully publish. The approval has now been granted, so the honest empty slots can finally hold the approved values, and the placement and quest waves can publish content whose numbers exist. Without this change the two dependent hunt changes would have to invent values or publish unnumbered content, both of which the design forbids.

## What Changes

- Populate `world/lore/monster_species.py::_VARIANT_DECLARATIONS` with the user-approved literal profile and the user-approved guild danger grade for each of the twelve first-batch variants, exactly as approved:

  | variant key | species | hp | mp | sp | atk_phys | agility | defense | magic_power | danger_grade |
  |---|---|---|---|---|---|---|---|---|---|
  | grain_pecker | sway_whistle_sparrow | 55 | 0 | 0 | 4 | 7 | 3 | 0 | F |
  | flock_leader | sway_whistle_sparrow | 80 | 0 | 0 | 6 | 8 | 4 | 0 | E |
  | shore_walker | tide_lamp_crab | 70 | 0 | 0 | 5 | 4 | 8 | 0 | F |
  | reef_warden | tide_lamp_crab | 110 | 0 | 0 | 7 | 3 | 8 | 0 | E |
  | burrow_maker | ridge_burrow_hare | 60 | 0 | 0 | 4 | 8 | 3 | 0 | F |
  | nest_guard | ridge_burrow_hare | 95 | 0 | 0 | 6 | 5 | 7 | 0 | E |
  | cliff_stepper | rock_echo_goat | 240 | 0 | 0 | 14 | 17 | 13 | 0 | D |
  | pass_warden | rock_echo_goat | 330 | 0 | 0 | 17 | 13 | 18 | 0 | C |
  | wood_stalker | fog_mane_lynx | 220 | 0 | 0 | 16 | 18 | 12 | 0 | D |
  | trail_hunter | fog_mane_lynx | 280 | 0 | 0 | 18 | 19 | 14 | 0 | C |
  | bank_lurker | tide_devouring_crocodile | 340 | 0 | 0 | 18 | 12 | 17 | 0 | D |
  | bay_warden | tide_devouring_crocodile | 400 | 0 | 0 | 20 | 12 | 20 | 0 | C |

  The approved design rules behind them (recorded as the accepted rationale in `design.md` with its calibration evidence) are: every value stays inside its variant's declared tier band; the ordinary variant takes the lower end of the tier's `guild_rank_range` and the stronger variant the upper end (low F/E, mid D/C); low HP sits at the bottom of the band because a creation-budget character's per-hit damage against defense 3–8 is small; mid values are calibrated so a creation-budget character can only chip them (defense 12–20 against such a character's attack), which is what "a party of ordinary adventurers" means; `mp`/`sp`/`magic_power` stay 0 because monster magic is documented nowhere and every tier's magic band is deliberately `(0, 0)`, while the six special abilities have no executable mechanics, so a resource pool would have no consumer.
- Add the missing invariant to registry construction: a shipped variant's `combat_profile` SHALL lie inside its declared tier band (HP inside the tier's HP band, `atk_phys`/`agility`/`defense` inside the tier's physical band, `magic_power` inside the tier's magic band) and its `danger_grade` SHALL lie inside its tier's `guild_rank_range`. Today nothing ties a rating to the tier it claims; this change is what makes the approved ratings durable against later edits.
- Amend `docs/superpowers/specs/2026-10-05-monster-data-model-design.md` §8 so the granted prerequisite (一) is recorded with the approved numbers, without rewriting any approved boundary: the existing appended-section idiom is used (a new subsection after the current "提案交付" section), never an in-place rewrite of §1–§7. `docs/lore/bestiary.md` gets the same treatment for its own usage-boundary note, which currently states that numbered commissions are unpublished and that the numeric and grade slots stay explicitly empty.
- Update the contracts that pin the current "no numbers" state: `world/lore/tests/test_monster_species_content.py`'s balance-slot class is replaced by the approved-literal pin (the module keeps its registered data-contract role), `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json` get the matching reason string, and a behavior test exercises the new band invariant with injected invented bands.
- No production caller changes. `world/rules/traits.py::initial_trait_config_for_variant` already branches on the profile, so every newly constructed individual — wilderness ambient, site, and acceptance provisioned — picks the approved values up and records `NUMERIC_SOURCE_APPROVED_PROFILE`; this change pins that with a test rather than editing the callers.

## Capabilities

### New Capabilities

- None. (The balance slots and their validation already exist as `monster-species-registry` requirements; this change populates them and adds one invariant.)

### Modified Capabilities

- `monster-species-registry`: the balance-gated-slot requirement changes from "shipped records carry `None`" to "shipped records carry the user-approved literals, and only an explicit user approval may populate a slot", and a new requirement makes tier-band and guild-rank-range membership a construction-time invariant.

## Impact

- Code: `world/lore/monster_species.py` (twelve literal profiles and grades; band-membership validation with an injectable tier face), `world/lore/tests/` (the registered balance-slot content contract updated, one new behavior test module for the invariant).
- Data contracts: `tools/test_data_freeze.json` + `tools/test_data_lint_seed.json` (the frozen reason string for the lore content contract carries its new role; both ledgers change together because `seed-mismatch` pins the frozen fields).
- Docs: `docs/superpowers/specs/2026-10-05-monster-data-model-design.md` §8 and `docs/lore/bestiary.md`'s appended delivery note, both as appended amendments. No player-visible surface, no command, no rendering: `docs/game/commands.md` and `docs/game/command-reference.md` and `tests/test_command_docs.py` are untouched, and `.github/evennia-shards.json` needs no entry (package label `world.lore` already owns the modules).
- Behaviour: the interim numeric source stops being used for the twelve shipped variants. Already-persisted individuals keep their stored traits and are never rescaled (the design's own rule); no migration, no database rewrite. Placed and provisioned individuals created after this change carry the approved numbers.
- Downstream: `monster-regional-species-hunts` and `monster-site-clear-out-hunts` publish the approved hunts; they depend on this change and are serialized after it.
