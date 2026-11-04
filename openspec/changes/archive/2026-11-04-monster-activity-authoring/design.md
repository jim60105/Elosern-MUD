# Design

## Context

`CompositionMember`, `EncounterComposition`, `EcologyZone` and `MonsterSite` are frozen lore rows. Candidate map publication validates ecology against candidate geography. Species/variant identity and the combat behavior profile already have their own contracts. Activity is separate from both birth exclusions and combat action policy.

## Goals / Non-Goals

This non-runtime slice adds exactly one schema/publication requirement. It delivers usable authoring validation, without state initialization or a scheduler. Human review of ecology bindings is recorded in `docs/development/monster-field-behaviour.md`; do not test a copied shipped policy table.

## Decisions

### Exact declarations

In new read-only `world/lore/monster_activity.py` publish frozen slotted `ActivityArea(key: str, region_key: str | None, rectangles: tuple[tuple[int,int,int,int],...], home_radius: int | None)`, `AggressionCondition(kind: str, area_key: str | None, dayparts: tuple[str,...])`, and `MonsterActivity(key: str, policy: str, area_key: str, decision_interval: int, aggression: AggressionCondition)`. Policies are `stationary`, `solitary_roaming`, `cohesive_group`. Aggression kinds are `passive`, `contact`, `defended_area`. Empty dayparts means all times; nonempty values resolve existing clock dayparts. Defended-area requires area_key; other aggression kinds forbid it. No numeric combat effects are declared here.

ActivityArea supports exactly one geometry form. Region-intersection form requires region_key and nonempty inclusive rectangles `(xmin,xmax,ymin,ymax)` and no home_radius. Home-distance form requires nonnegative integer home_radius and no region/rectangles. A stationary site may use radius zero. Decision intervals are positive integer ticks even for stationary bindings. Resolve a pure legal-cell predicate with `resolve_activity_area(area, *, home: Mapping[str,object], candidate_world: Any) -> tuple[Mapping[str,object],...]`; deduplicate and sort by canonical serialized locator because locator mappings are unhashable. Room-home radius zero contains that authored room only, nonzero room radius is invalid. The structural home/result locator is exactly `{kind:"wilderness",map:str,x:int,y:int}` or `{kind:"room",id:int}`; this pure candidate validator imports no rules runtime or new movement change. Candidate-world bounds and references are checked before publication. No birth buffer participates in activity geometry.

Add required `activity_key: str` to `EncounterComposition` and explicit required override `activity_key: str` to `MonsterSite`; the site override wins over composition only for its own movement declaration. Variant fallback is deliberately excluded, so there is exactly one complete composition/site binding and no precedence inference. GM and quest construction gain explicit `activity_key` input at their existing deterministic placement boundary in the consuming runtime change; registry validation here validates published quest/site references only. Every production composition gets an explicit bounded binding; current manual sites and designated exam opponents get explicit stationary/passive binding. Validate every permitted composition outcome at publication. With positive inclusive member counts, solitary_roaming requires sum(member.maximum) == 1. Validate a site's override against the same complete composition. Runtime sampling instantiates an already-valid policy and never filters, redraws or reinterprets an incompatible result. A cohesive declaration is legal only as a complete composition binding. Do not give prose or species names executable meaning.

Expose immutable `ACTIVITY_AREA_REGISTRY`, `MONSTER_ACTIVITY_REGISTRY` using existing ref/ref_many registry metadata. Extend `world/lore/{__init__,sync,registry_index}.py` and candidate `world/maps/runtime.py` validation with the existing candidate bundle, preserving the last published snapshot on any bad reference, impossible bounds, bool/nonpositive interval, incompatible policy or unknown daypart. Lore never reads the database and never constructs individuals.

## Risks / Trade-offs

Placement source signatures change atomically with their authoring/tests; no compatibility defaults or old constructor aliases. Existing development saves are untouched because this change publishes declarations only. Runtime consumers are added by mapped-monster-escape and global-monster-activity, which explicitly depend on this schema.

## Verification

Extend existing `world.lore.tests.test_monster_placement`, registry-reference tests and `world.maps.tests.test_geography_source`; add `world.lore.tests.test_monster_activity` and register it in evennia-shards. Synthetic valid forms and malformed candidates prove atomic publication, geometry derivation and policy/member compatibility. Generic production reference checks resolve every declaration without asserting names, coordinates, wording or counts.

## Implementation evidence contract

The canonical proposal ID for this requirement is `monster-field-activity::activity-declarations-publish-complete-validated-bindings`, generated with the traceability list tool against `/tmp/mud-field-proposed-specs`. Its complete-form, rejection and topology scenarios map to tasks1.1-2.1 in test_monster_activity, test_monster_placement and test_geography_source. This authoring-only slice adds exactly one mechanism requirement; ecology quality and shipped binding wording remain human-reviewed.

Create `/tmp/mud-field-tests.env` containing `MUD_TEST_SETTINGS=1` outside tracked source. Run one focused method/class at a time using the guarded command shown below; never concatenate the inventory or exceed 100 discovered tests. Register every new Python test module exactly once in `.github/evennia-shards.json`; new managed browser modules/methods belong exactly once in `.github/browser-shards.json`. Full managed-browser and complete traceability evidence remain CI-owned.

`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <named-label>`

Use canonical identifiers generated by `uv run --locked python -m tools.spec_traceability list`, never by concatenating names. For added/removed requirements, generate the equivalent merged specification tree outside Git and run the same tool with `--repo-root`; use its output before updating annotations. Preserve substantive assertion roles; delete retired claims without forwarding decorators, copy/data pin tests or waivers. Record requirement/scenario-to-test assertions and exercised evidence in `docs/development/monster-field-behaviour.md`. Human ecology/wording/visual judgment is reviewed there rather than asserted by shipped strings or counts.

At implementation handoff run focused tests, `uv run --locked python -m tools.observability_lint check` alongside changed-logging tests, the existing command-doc contract whenever command docs change, `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. These are future worker checks, not feature verification during proposal creation. Failure restores every owning durable/live surface and emits no committed success. No compatibility readers, migrations, hidden initialization of an existing save or reset-on-load.
