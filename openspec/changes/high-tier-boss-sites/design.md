# Design

## Context

See proposal.md (Why). Facts after the predecessors:

- `MonsterSite(key, kind, region_key, coordinates, composition_key, activity_key, capacity, one_shot, recover_after_ticks=None, individual_label_zh=None)`; a label requires a `(1, 1)` composition; `activity_key=None` lets the composition binding govern.
- `reservoir_warden` (utility, never AI-flees; legal innate flee stays available) and `warm_den_boar` (legacy `pack_hunter`, flees at its inclusive HP threshold) are constructible.
- `world/maps/tests/test_content_expansion_sites.py` exists with the shipped-registry wilderness fixture and `TransferStationEncounterTests`.
- `world/maps/tests/test_monster_journeys.py::MappedFleeIntegrationTests.test_a_two_enemy_rounds_flee_departs_and_reengages_the_same_identity` is the reference for driving a real mapped flee, journey and re-engagement.
- Planning probe (map-core over `content/maps`):

| Item | Region | Cell or rectangle | Check |
| --- | --- | --- | --- |
| crocodile site | `southeast_coast` | `(2076, 381)` | land, passable; nearest location/harbor `imperial_southeast_main_port` at distance 140; 11 inland water cells within radius 5 |
| crocodile territory | `southeast_coast` | `(2066, 2086, 371, 391)` | 420/441 land, 21 water |
| crocodile bay (defended) | `southeast_coast` | `(2071, 2081, 376, 386)` | 110/121 land, 11 water |
| boar site | `western_hills_valleys` | `(710, 530)` | land, passable; nearest location `town_olive_ferry` at distance 263 |
| boar territory | `western_hills_valleys` | `(700, 719, 520, 539)` | 400/400 land |
| boar den (defended) | `western_hills_valleys` | `(705, 714, 525, 534)` | 100/100 land |

Planning inputs only; the declarations become the single authority. Neither rectangle overlaps an existing or `weak-species-habitats` area.

## Goals / Non-Goals

**Goals:** two one-shot territorial boss sites with labelled bosses and real-consumer evidence.

**Non-Goals:** changing `tide_mouth_boss_site`; boss commissions or rewards; any mechanism, AI or balance edit.

## Decisions

### D1. Areas and activities

- `ActivityArea("reservoir_backwater_grounds", "southeast_coast", ((2066, 2086, 371, 391),))`, `ActivityArea("reservoir_backwater_bay", "southeast_coast", ((2071, 2081, 376, 386),))`, `ActivityArea("ember_bristle_grounds", "western_hills_valleys", ((700, 719, 520, 539),))`, `ActivityArea("ember_bristle_den", "western_hills_valleys", ((705, 714, 525, 534),))`.
- `MonsterActivity("reservoir_crocodile_territory_activity", "solitary_roaming", "reservoir_backwater_grounds", 60, AggressionCondition("defended_area", "reservoir_backwater_bay"))`; `MonsterActivity("ember_bristle_territory_activity", "solitary_roaming", "ember_bristle_grounds", 60, AggressionCondition("defended_area", "ember_bristle_den"))`.

### D2. Compositions and sites

- `EncounterComposition("reservoir_crocodile_boss", "reservoir_crocodile_territory_activity", (CompositionMember("reservoir_warden", 1, 1),))`; `EncounterComposition("ember_bristle_boss", "ember_bristle_territory_activity", (CompositionMember("warm_den_boar", 1, 1),))` in the manual-site block.
- `MonsterSite("reservoir_crocodile_boss_site", "boss_site", "southeast_coast", (2076, 381), "reservoir_crocodile_boss", None, 1, True, individual_label_zh="閉灣者")`; `MonsterSite("ember_bristle_boss_site", "boss_site", "western_hills_valleys", (710, 530), "ember_bristle_boss", None, 1, True, individual_label_zh="赤背")`, appended after the transfer-station site with English comments (remote placement, one-shot, label is display only).

### D3. Smoke extension

Add class `HighTierBossSiteTests` to `world/maps/tests/test_content_expansion_sites.py` (same fixture; site keys read as module constants), observations naming their defects:
- Each site populates exactly one individual whose `key` equals the site's declared label, whose species/variant keys are its composition row and whose single group binds the territorial activity (detects label/identity confusion).
- Croc: defeating the boss through an ordinary session clears the site; after a committed reload, a later site settlement, `site_living_members` read, map/population view read and a clear-out acceptance attempt, the site stays cleared and nothing is created (detects one-shot restoration).
- Boar: drive the boar to its legacy flee threshold in a real session (reference pattern `MappedFleeIntegrationTests`), observe a legal departure and journey, confirm the site is not cleared, the same persistent id remains owned by the site and its HP/MP/SP equal their values at departure after a committed reload, and that a new engagement with that id starts with those values (detects replacement or exit-time reset).
Freeze reason and shard ownership are unchanged (same module).

### D4. Review documentation

Extend "Content expansion sites" in `docs/development/regional-monster-population.md` with both bosses: remoteness rationale (tidal backwater beside inland water; dry remote woodland with charcoal-site context), territory/defended choice, the crocodile's utility no-AI-flee trade-off, labels as display facts, and smoke results. No coordinate repetition.

## Risks / Trade-offs

- [The crocodile never chooses flee] → recorded; the boar exercises the living-escape path, and party-side retreat stays available against both under `paid-party-retreat`.
- [Water cells inside the croc territory] → region-intersection activity uses the shared legal-cell predicate, so water cells are never journey targets.

## Verification

Focused labels: `world.maps.tests.test_content_expansion_sites.HighTierBossSiteTests`, `world.maps.tests.test_content_expansion_sites.TransferStationEncounterTests`, `world.lore.tests.test_monster_placement`, `world.lore.tests.test_monster_activity`, `world.maps.tests.test_population_geometry`, `world.maps.tests.test_monster_sites`. Then `uv run --locked python -m tools.map_reference_context --check`, `openspec validate high-tier-boss-sites --strict`, `uv run --locked python -m tools.contract_gate`.
