# Map Editor Monster Spawn Layer Design

## Goal

Show on the map editor's continent view where monsters are born and which
monsters each place can produce. The layer is read-only: spawn data stays
authored in `world/lore/monster_placement.py` and is edited through git.

Two lookups must work:

- From a place: select a zone or site and read what it spawns.
- From a monster: search a species or variant name and jump to every place
  that can spawn it.

## Scope

In scope:

- Ecology zones (`EcologyZone`): the rectangles that own automatic births.
- Manual sites (`MonsterSite`): camps, nests, boss sites, strays and encounters.

Out of scope:

- Activity areas (`ActivityArea`) and roaming bounds.
- Live population, living counts or any database read.
- Editing spawn data in the editor.
- Per-cell eligibility in the editor.

Authored rectangles are drawn as they are. At the time of writing, every zone's
eligible birth cells equal its full rectangle (400 of 400 for each of the nine
zones, measured with `eligible_birth_cells` on the published world), so the
rectangle is the real range. A later terrain edit does not redraw it; the game's
publication validation (`validate_ecology_geometry`) remains the authority on
legality.

## Data flow

The editor may not import the game, so the data crosses the boundary through the
existing exported artifact.

1. `tools/map_reference_context.py` reads the placement, species and region
   registries and adds a `monster_spawns` section to
   `content/map-reference-context.json`.
2. `elosern_map_core.reference_context` gains the field on
   `ReferenceContextDocument`, encodes it deterministically and decodes it
   strictly. `SCHEMA_VERSION` becomes 2. There is no compatibility path for
   version 1 documents.
3. `elosern_map_editor.snapshot` publishes the decoded section in the workspace
   payload as `monster_spawns`, beside the existing `external_context_status`.
4. The frontend builds drawables, catalog entries and inspector rows from that
   payload. It applies no game rule.

This reuses the artifact's file following, freshness check, CI `--check` step
and regeneration command. The existing discovery rule `world/lore/**/*.py`
already covers the placement and species sources, so the section adds no new
source rule.

### Exported shape

Rows are sorted by key. Names are resolved at export time, so the editor never
needs a species registry. Only fields the layer, search or inspector use are
exported.

```json
{
  "monster_spawns": {
    "zones": [
      {
        "key": "example_habitat",
        "region_key": "example_region",
        "region_name_zh": "範例地形區",
        "rectangles": [[100, 119, 200, 219]],
        "lower_density": 1,
        "upper_density": 3,
        "cell_capacity": 3,
        "wave_budget": 3,
        "recovery_delay": 3600,
        "replenishment_interval": 600,
        "pool": [
          {
            "composition_key": "example_group",
            "weight": 1,
            "members": [
              {
                "variant_key": "example_variant",
                "variant_name_zh": "範例變種",
                "species_key": "example_species",
                "species_name_zh": "範例物種",
                "minimum": 1,
                "maximum": 2
              }
            ]
          }
        ]
      }
    ],
    "sites": [
      {
        "key": "example_site",
        "kind": "camp",
        "region_key": "example_region",
        "region_name_zh": "範例地形區",
        "coordinates": [100, 200],
        "capacity": 2,
        "one_shot": false,
        "recover_after_ticks": 86400,
        "individual_name_zh": null,
        "composition_key": "example_group",
        "members": []
      }
    ]
  }
}
```

Decoding refuses unknown keys, rectangles that are not four integers with
`min <= max`, nonpositive weights, member ranges with `minimum > maximum`, and a
site kind outside the closed vocabulary. A refused section fails the whole
document through the existing `ReferenceContextError` path. The site `members`
array uses the same member row as a zone pool.

## Map presentation

`CONTINENT_LAYERS` gains one layer, key `monsters`, label
`怪物生成（匯出・唯讀）`, hidden by default. Choosing a search result reveals it
through the existing `navigate({ layer })` path. The layer exists only on the
continent domain.

- A zone draws one translucent polygon per rectangle. Coordinates are inclusive
  cells, so a rectangle spans `x_min..x_max + 1` and `y_min..y_max + 1` in cell
  units, converted with `cellMetres(world)`.
- Each zone also draws one fixed-screen-size mark at the centre of its first
  rectangle, so it stays findable at full-continent zoom. Zones may hold several
  rectangles; the polygons and the mark share one ref.
- A site draws one fixed-screen-size mark at its cell centre. The glyph differs
  per site kind.
- No permanent text labels are drawn. A label appears in the hover title and in
  lists.

Zones have no display name, so labels are composed from their spawns:

- Zone: `生態區：<species names>`, deduplicated in first-seen pool order.
- Site: `<site kind word>：<individual name or species names>`.

## Selection and search

Two new reference forms identify the objects:

- `monster_zone:<key>`
- `monster_site:<key>`

Both are selectable and appear in the object catalog on the `monsters` layer.
Neither is draggable, and neither has a delete or edit command. The kind has no
delete command, so the delete explanation reports `unavailable` through the
existing rule. No service route accepts these references, because the document
commands only resolve authored map objects.

The catalog entry gains an optional `searchTerms` array holding species and
variant names and keys. `rank()` in `lib/search.js` includes those terms when
present. A species search therefore returns every zone and site that can spawn
it, each as its own result.

## Inspector

A read-only `MonsterSpawnInspector` component shows the selected object:

- Header: label, key in monospace, region name, source file
  `world/lore/monster_placement.py`.
- Zone: density range per 100 cells, cell capacity, wave budget, recovery delay,
  replenishment interval, and one row per pool composition with its chance
  (`weight / total weight`, display-only) and its member rows.
- Site: kind, coordinates, capacity, one-shot or recovery time, individual name,
  and its member rows.

Each member row shows the species name, variant name and count range. Times are
game seconds and render in a readable unit.

## Freshness and failure handling

The section follows the artifact's status.

| Artifact status | Layer behaviour |
|---|---|
| current | Draws normally. |
| stale | Draws the exported data. The inspector shows a stale notice with the regeneration command `uv run --locked python -m tools.map_reference_context`. |
| missing or undecodable | The layer is empty, and the navigation row states why. Other editing is unaffected. |

Stale data is drawn because it is still useful for reading, and the notice states
that it may be behind the source.

## Testing

Specs and tests define logic only and use synthetic data, never real monster
content.

- Exporter: identical inputs yield byte-identical output; rows sort by key;
  composed names come from the registries; the committed artifact passes
  `--check`.
- `elosern_map_core`: encode/decode round trip, and each refusal listed under
  Exported shape.
- Service: the payload carries the decoded section, and an empty section when the
  artifact is unavailable.
- Frontend (`pnpm --dir tools/map-editor/frontend test`): scene geometry including
  inclusive rectangle edges and multi-rectangle zones, hidden-by-default layer,
  label composition, catalog entries, species search, chance calculation, stale
  and unavailable states, and that these references have no drag or delete path.
- Manual check in the browser at 1451x790 and 2560x1440, with text at 16px or
  larger, using the existing ink and gold theme.

## Documentation

- `docs/development/map-editor.md`: describe the layer and its read-only status.
- `docs/development/adding-monsters.md`: note that regenerating the reference
  context also refreshes the map editor's spawn layer.
