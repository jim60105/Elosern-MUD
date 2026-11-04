# Design

## Context

See proposal.md (Why). After `activity-group-formation`, `world/lore/monster_activity.py::movement_units(row_counts, row_bindings, *, activities=None)` forms groups from a per-row binding tuple, and the writers currently pass `(placement.activity_key,) * len(rows)` (zones) and `(site.activity_key,) * len(rows)` (sites). Current declarations in `world/lore/monster_placement.py`:

```python
class MonsterSite:  # frozen, slots
    key: str
    kind: str
    region_key: str = field(metadata=ref("wilderness_regions", inverse="monster_sites"))
    coordinates: tuple[int, int]
    composition_key: str = field(metadata=ref("encounter_compositions", inverse="monster_sites"))
    activity_key: str = field(metadata=ref("monster_activities", inverse="monster_sites"))
    capacity: int
    one_shot: bool
    recover_after_ticks: int | None = None

class CompositionMember:  # frozen, slots
    variant_key: str = field(metadata=ref("monster_variants", inverse="composition_members"))
    minimum: int
    maximum: int
```

`world/lore/registry_refs.ref(registry, *, inverse, nullable=False)` supports nullable single references. `construct_species_individual(species_key, variant_key, *, key=None, position="floor")` already accepts a display `key`.

## Goals / Non-Goals

**Goals:** per-row bindings with site-override precedence; a designated single-individual label.

**Non-Goals:** authoring any shipped composition, site, label or activity (owned by `abandoned-transfer-station-encounter` and `high-tier-boss-sites`); changing quest materialization, GM placement, recovery timing or one-shot semantics; any nickname tradition or naming generator.

## Decisions

### D1. Schema

```python
class CompositionMember:
    variant_key: str = field(metadata=ref("monster_variants", inverse="composition_members"))
    minimum: int
    maximum: int
    activity_key: str | None = field(
        default=None,
        metadata=ref("monster_activities", inverse="composition_member_bindings", nullable=True),
    )

class MonsterSite:
    ...  # key, kind, region_key, coordinates, composition_key unchanged
    activity_key: str | None = field(
        metadata=ref("monster_activities", inverse="monster_sites", nullable=True)
    )  # still positional; None means "no site override"
    capacity: int
    one_shot: bool
    recover_after_ticks: int | None = None
    individual_label_zh: str | None = None
```

Shipped site declarations keep passing their stationary override positionally and need no edit.

### D2. Resolver

Add to `world/lore/monster_placement.py` and its exports:

```python
def composition_row_bindings(
    composition: EncounterComposition,
    *,
    site: MonsterSite | None = None,
) -> tuple[str, ...]:
    """One effective activity key per composition member row, in member order."""
```

Rule: if `site is not None and site.activity_key is not None`, every row resolves `site.activity_key`; else each row resolves `member.activity_key` when not `None`, else `composition.activity_key`.

### D3. Validation

In `validate_ecology_registries` / `_check_composition` and `validate_monster_placement_registry`: a non-`None` `member.activity_key` must be a nonempty string present in the activity registry (`MonsterPlacementRegistryError` naming composition, row index and key). `_check_site_activity` accepts `None`; a non-`None` value must resolve. `individual_label_zh`: `None`, or a nonempty `str`; when present, `composition_bounds(composition) == (1, 1)` is required, else raise naming the site. The site-kind vocabulary, capacity, lifecycle and habitat checks are unchanged.

### D4. Writers and forecast

- `commit_population_wave`: `row_bindings = composition_row_bindings(ENCOUNTER_COMPOSITION_REGISTRY[placement.composition_key])`, passed to `movement_units`. `PopulationPlacement.activity_key` stays the composition binding for plan comparison.
- `monster_sites._populate`: `row_bindings = composition_row_bindings(composition, site=site)`; call `construct_species_individual(species_key, variant_key, key=site.individual_label_zh)` (passing `None` keeps the variant display name).
- `population_forecast.py`: `ProjectedSite.activity_key` and `_SiteState.activity_key` become `str | None`; every projection that calls `movement_units` uses `composition_row_bindings` with the same composition and site; any `activity_decision_interval(...)` call uses each unit's `activity_key`, never the site field.
- Recovered members of a labelled recoverable site receive the same label; they remain new persistent identities.

### D5. Documentation

Extend the "Activity Group Formation" section of `docs/development/monster-field-behaviour.md` with the precedence rule, the label constraint and the evidence map.

## Risks / Trade-offs

- [A reused zone composition placed by a site silently ignoring its row bindings] → precedence is explicit and documented: a site override governs the whole site; authors who need row bindings at a site omit the override.
- [Labels leaking into identity] → the label is only the object key; tests compare species/variant/site/group ownership with an unlabelled site.

## Verification

Focused command policy as in `activity-group-formation`: `/tmp/mud-field-tests.env` with `MUD_TEST_SETTINGS=1`; `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <label>` one class at a time; pure lore tests may use `uv run --locked python -m unittest`. Canonical IDs from `uv run --locked python -m tools.spec_traceability list --repo-root <merged tree>`. Handoff: `uv run --locked python -m tools.map_reference_context --check`, `uv run --locked python -m tools.observability_lint check`, `openspec validate site-member-activity-bindings --strict`, `uv run --locked python -m tools.contract_gate`. Synthetic catalogs only.
