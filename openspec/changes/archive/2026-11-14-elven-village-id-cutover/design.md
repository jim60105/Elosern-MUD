# Design

## Context

Location IDs are stable identities. The approved design makes one exception: the three elven villages move from `village_` to `elven_village_`. The old IDs appear in 43 tracked text files outside `openspec/`. One of the three villages, Ciaran, has a settlement map, 10 interiors and service hosts. The other two exist only as locations and lore rows.

The settlement map ID is the file stem and also the XYZ map key, so renaming the file changes every grid node ID of that map.

## Goals / Non-Goals

**Goals:**

- No current code, content, test or current documentation names an old ID.
- The world loads, and every generated artifact is fresh.

**Non-Goals:**

- No alias, redirect, compatibility decoder or database migration.
- No rename of ecology zone keys, activity ground keys or composition keys that start with `village_<name>_hinterland`.
- No rename of the test module `world/maps/tests/test_village_ciaran.py`, the spec capability `village-ciaran-map`, or interior IDs such as `ciaran_shelter`.
- No edit to historical records: `docs/superpowers/specs/**`, `docs/design/world-map/prototype-data.js`, `openspec/changes/archive/**`.
- No edit to `web/webclient-app/stories/fixtures/local_map.js`. It is a Storybook display fixture, not a reference to shipped data.
- No edit to `tests/test_map_settlement_contract.py`. Its two matches name the retired Python module `world/maps/village_ciaran.py`, not the location.

## Decisions

### D1. One regular expression performs the whole substitution

The substitution is:

```text
s/(?<!elven_)(?<!test_)village_(fionnen|ciaran|eolas)(?!_hinterland)/elven_village_$1/g
```

- `(?<!elven_)` makes a second run a no-op.
- `(?<!test_)` keeps the test module name `test_village_ciaran` in the shard manifests, the lint ledgers and the documentation.
- `(?!_hinterland)` keeps the ecology keys of D2.

It is applied with `perl -pi -e` to exactly these 36 files. The settlement file is moved first, so the list names it by its new path.

```text
.agents/skills/map-data-authoring/references/interiors.md
.agents/skills/map-data-authoring/references/locations-and-districts.md
.agents/skills/map-data-authoring/references/settlements.md
content/maps/interiors/ciaran_elenis_home.yaml
content/maps/interiors/ciaran_gwenaera_home.yaml
content/maps/interiors/ciaran_hailiel_home.yaml
content/maps/interiors/ciaran_lareneth_home.yaml
content/maps/interiors/ciaran_nireth_home.yaml
content/maps/interiors/ciaran_shelter.yaml
content/maps/interiors/ciaran_silverfeather.yaml
content/maps/interiors/ciaran_teliel_home.yaml
content/maps/interiors/ciaran_valwyn_home.yaml
content/maps/interiors/ciaran_vethiel_home.yaml
content/maps/locations.yaml
content/maps/settlements/elven_village_ciaran.yaml
docs/development/evennia-testing-guide.md
docs/lore/ciaran-commons-dialogue-review.md
docs/lore/ciaran-crafts-dialogue-review.md
web/tests/browser/test_browser_scene_transitions.py
world/lore/anchors.py
world/lore/races.py
world/lore/settlements/places_ciaran.py
world/lore/settlements/places.py
world/lore/settlements/settlements.py
world/lore/tests/test_settlements.py
world/lore/tests/test_wilderness_entry.py
world/maps/tests/_bootstrap_fixtures.py
world/maps/tests/test_bootstrap_sync.py
world/maps/tests/test_bootstrap/test_bootstrap_grid.py
world/maps/tests/test_bootstrap/test_bootstrap_selection.py
world/maps/tests/test_city_movement_cost.py
world/maps/tests/test_settlement_reload.py
world/maps/tests/test_settlement_sources.py
world/maps/tests/test_village_ciaran.py
world/quests/tests/test_definitions.py
world/rules/rulebook/commerce/scales.yaml
```

`content/map-reference-context.json` also names an old ID. It is regenerated (D3) and never edited.

Alternative considered: hand edits per file. Rejected, because 16 of the references sit in one test module and a missed one fails only at run time.

### D2. Ecology keys are not location references

`world/lore/monster_placement.py` and `world/lore/monster_activity.py` hold keys such as `village_eolas_hinterland` and `village_ciaran_hinterland_grounds`. They identify ecology zones, compositions and activity grounds. No code derives a location from them, and the `village_` prefix rule of the tiers design applies to location IDs only. They stay.

### D3. Regeneration order

`content/maps/locations.yaml` and one settlement document change, so three artifacts are stale. Regenerate in the order of `docs/development/road-network.md`:

1. `uv run --locked python -m tools.map_district_partition`
2. `uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_elevation.py --check` (the continent did not change, so this only confirms freshness)
3. `uv run --locked python -m tools.road_network`
4. `uv run --locked python -m tools.map_reference_context`

The elven villages are not road nodes, so the regenerated road artifact differs from the committed one only in `source_signature`.

### D4. The lore note becomes a fact

In `docs/lore/settlement-locations.md`, section 〈原型與地圖層級的對應〉, the second bullet under 「三點補充」 starts with 〔提案〕 and says the IDs will change. Replace that bullet with this text:

```text
- 〔已實作〕精靈村落的地點 ID 使用 `elven_village_` 前綴；`village_` 前綴歸人類村莊與獸王國部族村寨使用。地點 ID 原則上永不更名，精靈村落由 `village_` 改為 `elven_village_` 是經過核可的特例。
```

This wording is human-reviewed against `docs/lore/settlement-locations.md`. No test reads it.

## Risks / Trade-offs

- [A reference built from parts, such as an f-string joining `village_` and a name, escapes the expression] → Task 2.1's grep finds literal leftovers, and the focused tests of group 3 load every renamed map, interior and host.
- [The browser module reads grid node IDs from the built bundle] → Task 3.3 rebuilds the bundle before the run.
- [An existing development database no longer matches] → Documented in the proposal; reset per `docs/development/database-reset.md`.
