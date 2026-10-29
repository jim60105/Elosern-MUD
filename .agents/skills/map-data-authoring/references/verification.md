# Verification, generated artifacts and deletion safety

## The gates

Each diagnostic has a category, and the category decides what it blocks:

| Category | Examples | Effect |
| --- | --- | --- |
| `structure` | bad YAML or type, unknown field, id ≠ file stem, duplicate key, coordinate or road, unknown endpoint or reference, self-loop, duplicate outgoing direction, invalid mask or gate | **The world does not load.** The editor keeps a stale preview, refuses every write, and recovers by itself on the next loadable change. |
| `semantic` | `empty_graph`, `unreachable_landmark`, `blocked_approach`, `terrain_inconsistent`, `stale_partition` | Saveable work in progress. The editor keeps working, but the world is not game-ready. |
| `external` / `freshness` | an invalid or unknown scene or reference, a stale reference index or partition | Blocks game adoption only. |

On top of these, the game runs its own cross-file rules at startup (see
SKILL.md, "Cross-file invariants"). The editor does not run them.

## Commands (run from the repository root)

```console
# 1. Everything static, no Evennia needed (structure, semantic, game cross-file rules, freshness)
uv run --locked --project packages/map-core python .agents/skills/map-data-authoring/scripts/check_map_sources.py

# Core-only views
uv run --locked --project packages/map-core python -m elosern_map_core inspect .   # JSON diagnostics
uv run --locked --project packages/map-core python -m elosern_map_core schema      # authoritative field schema

# 2. Regenerate the district partition with the editor environment (no game needed; a few seconds to minutes)
uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py
uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_partition.py --check

# Game-side equivalents (need the game's Django/Evennia environment)
uv run --locked python -m tools.map_district_partition [--check]
uv run --locked python -m tools.map_reference_context [--check]

# Focused repository checks after a larger change
uv run --locked python -m unittest tests.test_map_authoring_contract
uv run --locked python -m tools.contract_gate
```

`check_map_sources.py` exits `0` when the static checks find nothing that
blocks game adoption. It exits `1` for loadable work in progress or a stale
artifact, and `2` when the sources do not load. It writes nothing.

The game's adoption test exercises a real reload of persistent rooms. It
needs the test database, so run it only when the user asks or the change
touches the runtime:

```console
uv run --locked --env-file=<file with MUD_TEST_SETTINGS=1> evennia test --settings test_settings.py --keepdb world.maps.tests.test_editor_final_yaml_adoption
```

## District partition (`world/maps/data/district_partition.json`)

This is the walking-distance ownership raster behind the world-map districts.
It is generated, committed and read-only. The game refuses to adopt a world
whose partition signature does not match the current sources.

- **Inputs.** `continent.yaml`, `locations.yaml`, `districts.yaml` and every
  `settlements/*.yaml`. Membership and content both count, so moving a single
  node also stales the artifact. Interiors and layouts are **not** inputs.
- **Regenerate it after** the edit loads and the other checks are clean.
  `regenerate_partition.py` refuses to run otherwise. It also rereads the
  sources before writing, and only replaces the file when nothing changed in
  between.
- **One generator at a time.** If the editor is open, either press its 分區
  chip (重新產生分區) or run the script, never both at once. The editor treats
  an external artifact write as a status change, not a source change.
- Never hand-edit the JSON or copy it from another branch. A partial diff of
  this file is always wrong.

## External reference context (`content/map-reference-context.json`)

This is an index the game exports and the editor reads. It contains:
- the external identifier sets: `scene_archetypes`, `nations`,
  `quest_definitions`, `service_hosts`, `shops` and more;
- `incoming_references`, keyed by qualified ID (for example
  `interior_room:altoria_tavern:altoria_tavern`), listing the static Python
  declarations that point at map objects;
- a SHA-256 manifest of the external Python sources it was built from.

It does **not** cover map geometry, so moving or editing map objects never
requires regenerating it. It goes stale only when external Python lore changes:
places, service hosts, quests, scene catalogues and the like. Regenerate it with
`uv run --locked python -m tools.map_reference_context` and commit it with the
lore change that caused it. CI checks it with `--check`.

Use it:
- to validate `scene_archetype` and nation values;
- before any deletion, to find external references to the object.

## Deletion safety

A deletion is safe only when all of these hold:

1. The reference index is **current**. `check_map_sources.py` prints
   `reference context: current`. If it is not, nothing can be proved absent,
   so do not delete.
2. `incoming_references` has no entry for the object's qualified ID.
3. No map document references it:
   - roads, gates and the city gate;
   - interior `exterior.node`/`exterior.room`;
   - `interior_links` in any interior;
   - district landmarks;
   - a settlement's `location_ref`.

   Search with `grep -rn "<id>" content/maps/`.

Remove the references first, as their own edits. The editor never cascades a
deletion, and neither should you. Static checks also cannot see live
save-game state (occupants, homes, persisted exits). The game's
synchronization refuses to prune a room that is still live, so a deletion the
user really wants may still need a game-side decision.

## Diagnosing a failure quickly

- A structure error carries `relative_path`, `line` and `field_path`. Fix
  exactly that spot. The usual causes are:
  - a stringified number;
  - a missing nullable key (`scene_archetype:`);
  - a duplicate key;
  - an ID that does not match the file stem;
  - a road to a misspelled node.
- `unreachable_landmark` / `blocked_approach`: a district landmark or gate
  approach lands on sea, ridge or river, or cannot reach the rest of the map.
  Move the landmark, or open a pass or ford.
- `footprint_location_offset` (`severity: warning`): the mask's bounding-box
  midpoint no longer equals the location cell. It is advisory — the world-map
  marker and the wilderness entrance are then in different places — and it
  never blocks saving, generation or adoption. Shift `wilderness_entry.offset`
  if you want them to coincide.
- `missing_anchor_room` / `multiple_anchor_rooms` / `anchor_location_mismatch`:
  the map needs exactly one `anchor_room` whose `anchor_key` is its
  `location_ref`. Nothing is promoted automatically; fix the node itself.
- `stale_partition`: expected after any partition-input edit. Regenerate it.
