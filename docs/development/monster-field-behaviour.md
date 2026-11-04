# Monster Field Activity: Authoring Schema and Review

This document records the authored field-activity layer published by the
`monster-activity-authoring` change. It is the human review surface for the
authored bindings; tests establish state, identity, legality and timing rather
than shipped wording, coordinates or counts.

## Declaration schema

`world/lore/monster_activity.py` publishes three frozen slotted row types and
two immutable registries:

```python
ActivityArea(key, region_key, rectangles, home_radius)
AggressionCondition(kind, area_key, dayparts)
MonsterActivity(key, policy, area_key, decision_interval, aggression)
```

- Policies are closed: `stationary`, `solitary_roaming`, `cohesive_group`.
- Aggression kinds are closed: `passive`, `contact`, `defended_area`.
- `ActivityArea` authors exactly one geometry form:
  - region intersection: a known wilderness `region_key` plus non-empty
    inclusive `(x_min, x_max, y_min, y_max)` rectangles and no `home_radius`;
  - home distance: a nonnegative `home_radius` and no region or rectangles.
- `resolve_activity_area(area, *, home, candidate_world)` returns the
  deduplicated, canonically sorted legal-cell locators. The home/result
  locator is exactly `{"kind": "wilderness", "map": str, "x": int, "y": int}`
  or `{"kind": "room", "id": int}`. A room home is legal only at radius zero
  and contains that room alone. Home distance is inclusive Chebyshev distance.
- Empty `dayparts` means all times; every nonempty value must be a clock
  rulebook daypart. `defended_area` requires an `area_key`; other kinds forbid
  one.
- Decision intervals are positive integer game ticks, including for
  stationary bindings.

`world/lore/monster_placement.py` adds required `activity_key` to
`EncounterComposition` and to `MonsterSite`. The site override wins only for
that site's own movement declaration; there is no variant fallback and exactly
one complete binding. `solitary_roaming` requires every permitted composition
outcome to total one individual (`sum(member.maximum) == 1`), checked at
publication for the composition binding and again for a site override. A
sampled singleton never authorizes a wider possible outcome. A
`cohesive_group` declaration is legal only as a complete composition binding.

## Candidate publication

The lore import validates the shipped declarations before publishing the
read-only registries. `world.maps.geography.build_geography` (reached from the
candidate bundle in `world.maps.runtime.compose`) then validates the same
declarations against the candidate's own regions and frame, and every site
binding against its complete composition. Any defect rejects the whole
candidate and leaves the previously published snapshot untouched.

Activity geometry is independent of birth geometry. Settlement birth buffers
are never consulted as movement barriers, and no birth exclusion participates
in `resolve_activity_area`.

## Authored binding review

Each ecology zone has one region extent matching its authored birth rectangle.
The three manual sites keep a region extent for their complete composition and
a zero-radius home extent for their own stationary override.

| Kind | Authored choice |
| --- | --- |
| Single-variant ecology compositions | `solitary_roaming`, 60-tick decisions |
| Mixed ecology compositions | `cohesive_group`, 90-tick decisions |
| Manual sites | `stationary`, passive, 120-tick decisions |
| Predators and wardens | `contact` or `defended_area` |
| Non-aggressive foragers | `passive` |
| Highland trail hunter | `contact` at dawn and dusk only |

These are authored declarations, not policy inferred from a species name or
from ecology prose. Exam opponents and GM/quest construction gain their
explicit activity input at the consuming runtime changes' deterministic
placement boundaries; this slice validates published quest/site references and
does not add runtime writers.

## Evidence map

Canonical requirement ID (generated with
`uv run --locked python -m tools.spec_traceability list` against the synced
`openspec/specs/monster-field-activity/spec.md`):
`monster-field-activity::activity-declarations-publish-complete-validated-bindings`.
The listed tests carry that literal ID through `covers_requirement`.

| Scenario | Substantive test assertions |
| --- | --- |
| Complete forms | `world.lore.tests.test_monster_activity.GeometryResolutionTests` (region enumeration, home radius, canonical sort, room zero); `PublishedActivityRegistryTests.test_every_shipped_reference_resolves` |
| Atomic rejection | `DeclarationValidationTests` (bad forms, unknown refs/dayparts, bool/nonpositive timing, duplicate keys, no mutation on failure); `CandidateAreaValidationTests` (unknown region, outside frame, no legal cell); `world.maps.tests.test_geography_source.ActivityCandidatePublicationTests` (whole candidate rejects, prior snapshot retained) |
| Separate topology | `GeometryResolutionTests.test_settlement_buffers_never_participate_in_activity_geometry`; `PublishedActivityRegistryTests.test_the_module_offers_no_execution_callable` |
| Every solitary outcome is valid | `BindingValidationTests.test_solitary_binding_rejects_any_multi_individual_outcome`; `world.lore.tests.test_monster_placement` site-override tests |

## Focused verification run

```text
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_activity
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_placement
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_geography_source
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_sites
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_population_geometry
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population_recovery
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_sync world.lore.tests.test_registry_index_contract world.lore.tests.test_registry_refs
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.quests.tests.test_compile_registration world.quests.tests.test_definitions world.quests.tests.test_site_clear_out_acceptance
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.tests.test_synthetic_data
uv run --locked python -m tools.contract_gate
uv run --locked openspec validate monster-activity-authoring --strict
```
