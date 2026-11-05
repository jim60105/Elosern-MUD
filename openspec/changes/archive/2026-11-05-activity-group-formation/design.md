# Design

## Context

See proposal.md (Why). Current code, read at `1b1be7b8`:

- `world/lore/monster_activity.py` publishes `MONSTER_ACTIVITY_POLICIES = ("stationary", "solitary_roaming", "cohesive_group")` and `validate_activity_binding(activity, largest_total, what)`, which raises when a `solitary_roaming` binding's composition can exceed one member. It is called from `_check_composition_activity` and `_check_site_activity` in `world/lore/monster_placement.py`.
- `world/maps/regional_population.py::commit_population_wave` constructs every sampled individual and calls `monster_activity.create_group(..., operation_id=f"wave:{zone.key}:{state.generation_sequence + 1}", ordinal=0, activity_key=placement.activity_key, member_ids=<all>)` once.
- `world/maps/monster_sites.py::_populate` constructs each individual and calls `register_explicit_individual(..., owner_kind="site", owner_key=site.key, activity_key=site.activity_key)` per individual; that function creates one one-member group with `operation_id=f"explicit:{x}:{y}:{pk}"`.
- `world/maps/population_forecast.py` projects a zone birth (`_settle_zone_recoveries` and the initial-wave path) and a matured site recovery (`_settle_sites`) each as one `_place(...)` group carrying the whole count.
- `world/maps/monster_activity.py::create_group(..., operation_id, ordinal, ...)` already derives `group_id_for(operation_id, ordinal) == f"{operation_id}#{ordinal}"` and refuses an existing id.
- Movement scheduling reads only `declaration.policy == "stationary"`; solitary and cohesive groups differ nowhere else at runtime.

## Goals / Non-Goals

**Goals:** one pure formation rule shared by both writers and the forecast; legal solitary multi-member compositions; atomic multi-group placement.

**Non-Goals:** per-row activity bindings, nullable site overrides or designated individual labels (owned by `site-member-activity-bindings`); any new species, composition, zone, site or activity declaration; any change to journeys, aggression, contact forecasting semantics, quest materialization or GM placement (they keep `register_explicit_individual` and its operation ids).

## Decisions

### D1. Shared pure formation helper in `world/lore/monster_activity.py`

Add verbatim:

```python
@dataclass(frozen=True, slots=True)
class MovementUnit:
    """One movement group a placement creates: its binding and member slots."""

    activity_key: str
    member_indices: tuple[int, ...]


def movement_units(
    row_counts: Sequence[tuple[str, int]],
    row_bindings: Sequence[str],
    *,
    activities: Mapping[str, MonsterActivity] | None = None,
) -> tuple[MovementUnit, ...]:
    ...
```

- `row_counts` is the sampled `(variant_key, count)` tuple in composition member order (exactly `PopulationPlacement.groups` or `site_occurrence_groups(...)`). `row_bindings` is the activity key each row resolves, parallel to `row_counts`.
- Member slots are the flattened construction order: row 0's individuals first, then row 1's, and so on; slot numbers start at 0. Writers must construct individuals in exactly this order.
- For every slot, read `activities[row_bindings[row]].policy` (default `MONSTER_ACTIVITY_REGISTRY`). `cohesive_group`: all slots whose binding is the same cohesive key join one unit. `solitary_roaming` and `stationary`: each slot is its own unit.
- Return units sorted by their smallest member slot. A row with count 0 contributes no slot. Raise `MonsterActivityRegistryError` when the two sequences differ in length, a count is negative or not an int (bools rejected), or a binding is unknown.
- Export `MovementUnit` and `movement_units` in `__all__`.

Alternative rejected: a new policy value such as `dispersed_solitary`. It would duplicate `solitary_roaming` movement semantics under a second name and leave the existing site/forecast disagreement unresolved.

### D2. Remove the solitary-total publication rule

Delete `validate_activity_binding` and its `__all__` entry. In `world/lore/monster_placement.py`, `_check_composition_activity` and `_check_site_activity` keep their key-presence and unknown-reference checks and stop computing `composition_bounds` for activity purposes. No other validation is weakened: unknown references, geometry, timing and aggression checks remain.

### D3. Zone waves

In `commit_population_wave`, keep construction order (rows in `placement.groups` order). After the construction loop compute `units = movement_units(placement.groups, (placement.activity_key,) * len(placement.groups))` and, for `ordinal, unit in enumerate(units)`, call `create_group` with the existing `operation_id=f"wave:{zone.key}:{state.generation_sequence + 1}"`, `ordinal=ordinal`, `activity_key=unit.activity_key`, `member_ids=tuple(created[i].pk for i in unit.member_indices)`, and the existing owner/home/position/seed/tick arguments. Everything stays inside the existing `transaction.atomic()` and `snapshot_population_surfaces`/`restore_population_surfaces` compensation. `PopulationPlacement` is unchanged.

### D4. Explicit group registration and site population

Add to `world/maps/regional_population.py` and `__all__`:

```python
def register_explicit_group(
    wilderness: Any,
    individuals: Sequence[Any],
    coordinates: tuple[int, int],
    *,
    tick: int,
    owner_kind: str,
    owner_key: str,
    activity_key: str,
    operation_id: str,
    ordinal: int = 0,
    transition_source_id: str | None = None,
) -> None:
```

It applies every per-individual check `register_explicit_individual` applies today (persisted `Monster`, valid coordinates), refuses an empty or duplicate individual list with `ExplicitPlacementRefused`, writes each coordinate and room attachment, calls `create_group` once with all member ids and the given `operation_id`/`ordinal`, then records one `PopulationTransition` per individual with `source_id = transition_source_id if transition_source_id is not None else f"{operation_id}#{ordinal}"` and emits the existing `monster_population_individual_registered` event per individual. `register_explicit_individual` becomes a thin delegate passing `[individual]`, `operation_id=f"explicit:{cell[0]}:{cell[1]}:{individual.pk}"`, `ordinal=0` and `transition_source_id=operation_id` (the legacy `explicit:x:y:pk` value without `#0`), so quest, GM and exam callers keep byte-identical group ids (`explicit:x:y:pk#0`, as today) and transition `source_id` values. `_populate` passes no `transition_source_id`, so its transitions read `site:<key>:<sequence>#<ordinal>`.

`monster_sites._populate(wilderness, site, *, seed, sequence, tick)` constructs every row in `site_occurrence_groups` order and stamps `db.site_key`, then computes `movement_units(rows, (site.activity_key,) * len(rows))` and calls `register_explicit_group(..., owner_kind="site", owner_key=site.key, activity_key=unit.activity_key, operation_id=f"site:{site.key}:{sequence}", ordinal=ordinal)` per unit. Shipped sites bind stationary overrides, so they keep one group per individual.

### D5. Forecast

In `population_forecast.py`, wherever a zone birth or a site occurrence is projected through `_place(...)`, compute the same `movement_units` from the same rows and binding and call `_place` once per unit with `group_id=f"{<existing base id>}#{ordinal}"`, `count=len(unit.member_indices)` and `activity_key=unit.activity_key`. The projection still creates no durable state and still contributes no idle decision for projected groups.

## Risks / Trade-offs

- [Existing development saves hold site groups keyed `explicit:x:y:pk`] → pre-release; newly created site groups use `site:<key>:<sequence>#<n>`. No reader depends on the old site prefix; do not add a compatibility reader.
- [A solitary multi-member birth places several groups in one cell] → cell capacity, density ceilings and wave budget already count individuals, not groups, so no ceiling changes.
- [Forecast drift] → the forecast calls the same helper with the same rows; D5's test compares projected and committed group shapes.

## Migration Plan

None. Pre-release; reset a development save if its old site group ids matter.

## Verification

Create `/tmp/mud-field-tests.env` containing `MUD_TEST_SETTINGS=1` outside tracked source. Run one focused method or class at a time with `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <label>`; never exceed 100 discovered tests per run. Pure lore tests may run with `uv run --locked python -m unittest <module>` when they need no database. Use canonical requirement IDs from `uv run --locked python -m tools.spec_traceability list`; for the added requirement, generate the merged tree outside Git and pass `--repo-root`. The modified requirement keeps its ID `monster-field-activity::activity-declarations-publish-complete-validated-bindings`. At handoff run `uv run --locked python -m tools.observability_lint check`, `uv run --locked python -m tools.map_reference_context --check` (after regenerating), `openspec validate activity-group-formation --strict` and `uv run --locked python -m tools.contract_gate`. All new tests use synthetic catalogs (`world.tests.synthetic_data`); no production key or count is asserted.
