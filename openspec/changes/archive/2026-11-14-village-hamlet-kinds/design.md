# Design

## Context

The location kind is a closed vocabulary declared twice and required to agree: `LOCATION_KINDS` in `packages/map-core/elosern_map_core/schema.py` and `AnchorKind` in `world/lore/anchors.py`. `world/lore/tests/test_anchors.py` compares the two sets and composes one synthetic location of each kind. The spec already says that shipped content need not use every kind.

Other places branch on the kind:

| Place | Current rule | Effect of a new public kind |
| --- | --- | --- |
| `web/webclient/presentation/world_map_geometry.py` `_place_geometry` | hidden for `elven_village` and `dungeon`, `capital` for a capital, else `settlement` | Already `settlement`. No code change. |
| `world/rules/sight.py` `SUPPORTED_SETTLEMENT_KINDS` | `("capital", "city", "town", "port")`; the rulebook must hold exactly these silhouette rows | Must list the new kinds, and the rulebook needs two rows. |
| `world/rules/sight.py` and `world/rules/wilderness_disclosure.py` `HIDDEN_ANCHOR_KINDS` | `elven_village`, `dungeon` | Unchanged: the new kinds are public. |
| `world/maps/population_geometry.py` `INHABITED_SETTLEMENT_KINDS` | capital, city, town, port, elven village | Must list the new kinds. |
| `tools/settlement_synthesis/budget.py` `NATIONAL_KINDS` | capital, city, town, port | Unchanged here. `single-cell-size-budget` owns it. |
| `content/maps/road_network.yaml` `node_kinds` | capital, city, port, town | Unchanged. `road-spur-stage` owns road behaviour. |

## Goals / Non-Goals

**Goals:**

- A location of kind `village` or `hamlet` loads, composes, draws as a public settlement and excludes monster births around it.

**Non-Goals:**

- No location of either kind is authored.
- No size budget, settlement generator, road or spacing behaviour.
- No new nation, archetype enum or per-nation kind. The nation selects the archetype in prose and in later tools.
- No change to `SettlementArchetype` in `world/lore/settlements/settlements.py`.

## Decisions

### D1. The two kinds are appended, not inserted

`LOCATION_KINDS` becomes:

```python
LOCATION_KINDS = ("capital", "city", "town", "port", "elven_village", "dungeon", "village", "hamlet")
```

`AnchorKind` gains two members after `DUNGEON`:

```python
    VILLAGE = "village"
    HAMLET = "hamlet"
```

Appending keeps every existing index. `tests/test_road_network_generation.py` takes `LOCATION_KINDS[1]` and `LOCATION_KINDS[4]` as a node kind and a non-node kind, and `tests/test_road_network_format.py` takes `sorted(LOCATION_KINDS)[:2]`; both keep their current values.

Alternative considered: inserting the kinds after `port` for reading order. Rejected, because it silently changes the kind those two test modules exercise.

### D2. Inhabited categories

`INHABITED_SETTLEMENT_KINDS` in `world/maps/population_geometry.py` gains `AnchorKind.VILLAGE` and `AnchorKind.HAMLET`. The module docstring's list "(capital, city, town, port, or elven village)" gains "village, hamlet". Nothing else in the module changes: a location with no settlement document already measures from its published cell, and `MINIMUM_SETTLEMENT_BUFFER` already applies.

### D3. Sight: two supported kinds and two silhouette rows

`SUPPORTED_SETTLEMENT_KINDS` in `world/rules/sight.py` becomes `("capital", "city", "town", "port", "village", "hamlet")`.

`world/rules/rulebook/sight.yaml` gains these rows under `settlement_silhouettes`, after `port`:

```yaml
  village:
    day: 幾十戶屋頂聚成一簇，炊煙從中升起
    night: 聚在一處的幾點窗火
  hamlet:
    day: 田野間幾戶人家低矮的屋影
    night: 孤零零的一兩點燈火
```

The sentences name no church and no totem, because humans and beastfolk share both kinds. They are authored prose: a person reviews them against `docs/lore/settlement-locations.md` 〈人類聚落的層級差異〉, and no test pins the wording. The existing rule that a rulebook missing a supported kind is rejected already covers the mechanism.

### D4. Editor dropdown

`LOCATION_KINDS` in `tools/map-editor/frontend/src/components/ContinentInspector.vue` gains two rows after `port`:

```js
  { value: "village", label: "village · 村莊" },
  { value: "hamlet", label: "hamlet · 小村莊" },
```

### D5. Population is a sample

The design says the settlement populations are never reconciled against the 30 million world total, and asks that any test assuming a reconciliation be corrected. The existing tests reconcile only the three nations against the continent, the three capitals against their share and the three elven villages against the elven total (`world/lore/tests/test_nations.py`). None sums cities, towns and ports. No test changes for this reason.

The comment above the national rows of `ANCHOR_LORE` in `world/lore/anchors.py` says "the rural majority lives in unnamed villages". Replace that sentence with: "Settlement populations are a representative sample and are never reconciled against the national or continental totals."

### D6. Tests

| Test | File | Establishes |
| --- | --- | --- |
| A synthetic `VILLAGE` and a synthetic `HAMLET` anchor with no wilderness entry each exclude their own cell and its 8 neighbours, and a `DUNGEON` at the same distance excludes nothing | `world/maps/tests/test_population_geometry.py`, beside the existing `AnchorKind.ELVEN_VILLAGE` case | regional-ecology scenario "Village and hamlet categories" |
| `settlement_kinds` in `test_national_settlements_carry_nation_and_population` gains `AnchorKind.VILLAGE` and `AnchorKind.HAMLET` | `world/lore/tests/test_anchors.py` | lore-registries scenario "National settlement lore joins" |
| `expected` in `test_anchor_classification_keeps_villages_and_dungeons_visit_only` gains `AnchorKind.VILLAGE: ("settlement", False)` and `AnchorKind.HAMLET: ("settlement", False)` | `web/webclient/presentation/tests/test_world_map.py` | existing webclient-world-map requirement; the test asserts its table covers every `AnchorKind` |

`world/lore/tests/test_anchors.py::test_anchor_kinds_match_the_schema_location_kinds` and the synthetic sight policy in `world/rules/tests/test_sight.py` iterate the two vocabularies and need no edit.

The two MODIFIED requirements keep their identifiers, so the existing `covers_requirement` annotations stay valid. Add the same existing annotation, `regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings`, to the new population test only if `uv run --locked python -m tools.spec_traceability list` prints exactly that identifier.

### D7. Documentation

- `.agents/skills/map-data-authoring/references/locations-and-districts.md`, section "Location kinds": add `village` and `hamlet` to the closed list and to the table ("a national settlement of 300 to 2,000 people" and "a national settlement of 50 to 300 people"), state the prefixes `village_` and `hamlet_`, state that the elven villages use `elven_village_`, and add `world/maps/population_geometry.py` → `INHABITED_SETTLEMENT_KINDS` and `world/rules/sight.py` → `SUPPORTED_SETTLEMENT_KINDS` with its rulebook rows to the list of places a kind change must touch. Remove the sentence that `test_anchors.py` expects every kind to be used by a shipped location; the test does not.
- `.agents/skills/map-data-authoring/SKILL.md` line 309 and `docs/development/map-authoring-documents.md` line 83: add the two kinds to the listed values.
- `docs/development/regional-monster-population.md` line 143: add the two kinds to the inhabited list.

## Risks / Trade-offs

- [A consumer branches on the kind in a place not listed above] → The search `grep -rnE "AnchorKind\.|LOCATION_KINDS|HIDDEN_ANCHOR_KINDS|SUPPORTED_SETTLEMENT_KINDS|NATIONAL_KINDS" --include='*.py' --include='*.vue' world web tools packages typeclasses commands server` was run for this design; the table in Context lists every production hit that decides behaviour by kind.
- [About 300 public markers will later appear on the world map] → Out of scope here; the trial change records it for human review.
