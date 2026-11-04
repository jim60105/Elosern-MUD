# Proposal

## Why

The content-expansion design (`docs/superpowers/specs/2026-11-03-monster-content-expansion-design.md` §4.1, §7.1) requires one birth occurrence of one to three 泥膜史萊姆 in which every individual moves as its own unit. Today a zone wave creates exactly one movement group for the whole sampled composition, and publication rejects a `solitary_roaming` binding whose composition can place more than one individual, so that content cannot be authored. Manual sites, on the other hand, always create one group per individual even when their binding is `cohesive_group`, and the read-only forecast projects a recovered site as one group, so the two writers and the forecast already disagree about how a policy forms groups.

## What Changes

- **BREAKING** Group formation follows the activity policy of each individual's binding: individuals sharing one `cohesive_group` binding form one group; every `solitary_roaming` or `stationary` individual forms its own one-member group. Zone waves, manual-site population and the read-only population forecast all use one shared pure helper.
- **BREAKING** Remove the publication rule that a `solitary_roaming` binding must total exactly one individual, together with `validate_activity_binding` and its call sites. A solitary binding of a multi-member composition becomes legal and disperses at construction.
- Add an explicit-placement group registration beside `register_explicit_individual`, so a site can register a cohesive multi-member group atomically; quest, GM and exam callers keep the single-individual entry point.
- Shipped declarations are unchanged: every shipped solitary composition already totals one, the shipped mixed zone compositions are cohesive, and every shipped site binds a stationary override, so their observable group shapes stay identical.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monster-field-activity`: replace the solitary-total publication scenario and add the policy-driven group-formation requirement for zone births, manual sites and the forecast.

## Impact

Code: `world/lore/monster_activity.py` (new `MovementUnit`/`movement_units`, removal of `validate_activity_binding`), `world/lore/monster_placement.py` (binding checks keep reference resolution only), `world/maps/regional_population.py` (`commit_population_wave` per-unit groups, new `register_explicit_group`), `world/maps/monster_sites.py` (`_populate` per-unit registration), `world/maps/population_forecast.py` (zone and site projection per unit). Tests: `world/lore/tests/test_monster_activity.py`, `world/lore/tests/test_monster_placement.py`, `world/maps/tests/test_regional_population.py`, `world/maps/tests/test_monster_sites.py`, `world/rules/tests/test_field_contact_boundaries.py`. Documentation: `docs/development/monster-field-behaviour.md`. Regenerated artifact: `content/map-reference-context.json`.

No content, species, skill, AI or combat change. Human review: the developer section added to `docs/development/monster-field-behaviour.md` records the reasoning for the formation rule; tests establish only the mechanism. Pre-release: no save migration or compatibility reader; an existing development save may be reset.

## Batch:

depends-on: none (landed prerequisites: regional-population-owner, manual-monster-compositions, monster-activity-authoring, mapped-monster-escape, global-monster-activity, interruptible-field-contact — all archived)

Batch 1, parallel with `owned-kit-decision-coverage` and `affirmative-monster-prose-guidelines` (disjoint files).

Code conflicts:
- `site-member-activity-bindings` edits the same helper, `monster_placement.py`, `monster_sites.py`, `regional_population.py` and `population_forecast.py`; it lands after this change.
- `weak-species-habitats`, `abandoned-transfer-station-encounter` and `high-tier-boss-sites` append declarations to `world/lore/monster_activity.py` and `world/lore/monster_placement.py`; they land later.
- `content/map-reference-context.json` is a generated file whose source manifest hashes every `world/lore` and `world/rules` module; any parallel change touching those trees conflicts mechanically on it. Resolve by rerunning `uv run --locked python -m tools.map_reference_context` after rebase, never by hand-merging.
