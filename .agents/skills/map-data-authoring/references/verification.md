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

# 3. Regenerate the wilderness elevation tiles with the editor environment (no game needed; a few seconds)
uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_elevation.py
uv run --locked --project tools/map-editor python .agents/skills/map-data-authoring/scripts/regenerate_elevation.py --check

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

## Wilderness elevation tiles (`content/maps/wilderness_elevation.json`)

This is the deterministic physical relief and prominence tile bundle for the wilderness frame.
It is generated, committed and read-only. The game and `check_map_sources.py` refuse to adopt
a world whose elevation signature does not match the current sources.

- **Inputs.** `continent.yaml` (coast, ridge, waterways, regions, `elevation_shapes`),
  the default generator configuration, and the algorithm version. Whole-document
  fingerprinting of `continent.yaml` is conservative: editing prose or scene archetypes
  in `continent.yaml` invalidates the signature and requires running `regenerate_elevation.py`.
- **Regenerate it after** the edit loads and the other checks are clean.
  `regenerate_elevation.py` checks static sources, re-reads them before publishing,
  and replaces the artifact atomically.
- **Budget.** The serialized UTF-8 JSON text must remain within 4 MiB (`MAX_ELEVATION_BYTES`).
  If the budget is exceeded, generation fails and leaves prior output intact.
- Never hand-edit the JSON.

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

## Capturing an image of a map

`capture_map.py` produces one image of one authored view — continent,
settlement or interior — without starting the editor, the game or a browser
session of your own. It reads the current disk sources once, draws them with
the editor's own map surface in a disposable headless browser, and publishes
the image atomically. The YAML stays the source of truth; the image is a
derived artefact you read, never a file you commit.

### Setup (once per checkout)

The capture runtime is an optional developer group of the independent editor
project, so it never becomes a game dependency. Prepare it explicitly; the
command itself installs nothing.

```console
uv sync --locked --project tools/map-editor --group capture
uv run --locked --project tools/map-editor --group capture playwright install chromium
pnpm --dir tools/map-editor/frontend install --frozen-lockfile
pnpm --dir tools/map-editor/frontend run build:capture
```

The last command writes `tools/map-editor/frontend/capture-dist/`, the
file-based map-only page the capture opens; it is untracked build output. A
missing environment, browser build or page is reported with the command that
fixes it, never installed on your behalf.

### Usage

Run from the repository root (the working directory supplies the sources and
resolves a relative `--output`):

```console
uv run --locked --no-sync --project tools/map-editor --group capture python \
    .agents/skills/map-data-authoring/scripts/capture_map.py \
    --view continent --output /tmp/continent.webp
```

| Argument | Accepted values | Default |
| --- | --- | --- |
| `--view` | `continent`, `settlement`, `interior` | required |
| `--map` | the document ID of a settlement or interior | required for those views, forbidden for `continent` |
| `--bounds MIN_X MIN_Y MAX_X MAX_Y` | four finite numbers, `MIN_X < MAX_X` and `MIN_Y < MAX_Y` | absent: fit the whole map |
| `--width` / `--height` | positive integer pixels | `1280` / `960` |
| `--hide LAYER [LAYER ...]` | repeatable; applicable layer names of the selected view | none: every layer visible |
| `--format` | `webp` (lossless), `png` (lossless) | `webp` |
| `--output` | image path; extension must match `--format`, parent directory must exist | required |

There is no `--show`, no quality slider and no service URL. Unknown flags,
abbreviations, unknown or cross-view layers, fractional or nonpositive
dimensions, non-finite or degenerate bounds, an unsupported format, a
mismatched suffix and a missing parent are all refused before anything is
rendered. Repeated `--hide` names are de-duplicated and reported sorted.
Hiding every layer is allowed and yields the plain background at the same
camera.

### Finding an ID

`--map` takes the document ID, which is the file stem:

- settlements: `content/maps/settlements/<map_id>.yaml`, for example
  `capital_altoria`;
- interiors: `content/maps/interiors/<interior_id>.yaml`.

The continent is a single document and takes no ID. If a document is not on
disk it does not exist; there is no map-list API to add.

### Coordinate frames

`--bounds` and the reported `bounds` use the view's own frame, never a mixed
one:

| `view` | Input and result frame | `units` | `axes` |
| --- | --- | --- | --- |
| `continent` | continental kilometres (`east_km` grows east, `north_km` north) | `km` | `{x: east, y: north}` |
| `settlement` | authored local metres (`x_m`, `y_m`) | `m` | `{x: east, y: north}` |
| `interior` | editor layout units (`x` right, `y` down) | `layout` | `{x: right, y: down}` |

An explicit rectangle keeps its centre and is grown on its narrower axis to
the output aspect ratio, with one uniform scale; the result is never clipped,
stretched or recentred, and may reach beyond the map or contain no objects.
The reported `bounds` is the expanded rectangle actually drawn, so it can be
wider than what you asked for. Content outside a tightly requested region is
clipped at the image edge — ask for a larger region instead of a bigger
padding. A full-map fit grows the extent until the map's own cards and labels
fit; an output size too small for them is refused with an explicit error
rather than a silently cropped image.

### Layers

Every layer is visible by default, independently of the editor's own
preferences. `--hide` removes a layer for this one image only.

| `view` | Layer | Content hidden |
| --- | --- | --- |
| `continent` | `terrain` | mainland, terrain/passability raster, forest edge |
| `continent` | `water` | waterways |
| `continent` | `ridge` | ridge walls, passes, fords |
| `continent` | `locations` | locations and reserved harbour sites |
| `continent` | `footprint` | settlement wilderness footprints |
| `continent` | `partition` | derived national boundaries and district outlines |
| `settlement` | `nodes` | street nodes, including gate glyphs |
| `settlement` | `roads` | authored directed roads and their bends |
| `interior` | `rooms` | room cards |
| `interior` | `connections` | within-interior connections and their direction indicators |
| `interior` | `exterior` | the exterior doorway card and its link |
| all | `labels` | object names, IDs and connection text |

Hiding a geometry layer removes that layer's drawables and its own labels.
`labels` removes text only: cards, glyphs and direction indicators stay.
`nodes`/`roads` and `rooms`/`connections` are independent in both directions.
Hiding a layer never moves the camera; the reported `bounds` is identical.

### Examples

```console
# Default continent overview: 1280x960 lossless WebP, every layer on.
uv run --locked --no-sync --project tools/map-editor --group capture python \
    .agents/skills/map-data-authoring/scripts/capture_map.py \
    --view continent --output /tmp/continent.webp

# One settlement, without its labels, as PNG.
uv run --locked --no-sync --project tools/map-editor --group capture python \
    .agents/skills/map-data-authoring/scripts/capture_map.py \
    --view settlement --map capital_altoria --hide labels \
    --format png --output /tmp/altoria.png

# One interior against its layout frame, several layers hidden.
uv run --locked --no-sync --project tools/map-editor --group capture python \
    .agents/skills/map-data-authoring/scripts/capture_map.py \
    --view interior --map altoria_tavern --hide labels exterior \
    --output /tmp/tavern.webp

# A regional continent crop in kilometres, at a portrait aspect ratio.
uv run --locked --no-sync --project tools/map-editor --group capture python \
    .agents/skills/map-data-authoring/scripts/capture_map.py \
    --view continent --bounds 100 200 180 260 \
    --width 960 --height 1280 --output /tmp/region.webp
```

### The success object and exit status

On success the command prints exactly one JSON object on stdout:

```json
{"image_path": "/abs/path/continent.webp", "view": "continent", "map_id": null,
 "format": "webp", "width": 1280, "height": 960,
 "bounds": [-3.5, 0, 43.5, 40], "units": "km",
 "axes": {"x": "east", "y": "north"}, "hidden_layers": [],
 "diagnostics": []}
```

`image_path` is absolute; `map_id` is `null` only for the continent;
`hidden_layers` is sorted and de-duplicated; `diagnostics` is the structured
source result of the snapshot that was drawn. Exit status `0` means one image
was produced. It does **not** mean the map is game-ready, and it is not an
inspection of the image. Run `check_map_sources.py` for readiness.

Every refusal exits nonzero with a short message on stderr and publishes no
partial image. An existing file at `--output` is replaced only after the
complete image has been encoded; a failure before that replacement leaves the
previous file byte-identical and removes temporary files.

Replacement is the last filesystem step. If the image has already replaced the
destination and writing the success object to stdout then fails (for example a
closed pipe), the command exits nonzero with a `report_failed` message naming
the published image: it does not delete or hide an image it already produced,
and it never claims an image it did not write.

### Read the image after capturing

A successful command is not a look at the map. After capturing, read
`image_path` with your image-reading tool and describe what is actually
visible: composition, readable Traditional Chinese labels, geometry.

- If your tool cannot decode WebP, rerun the same request with `--format png`
  and a `.png` path. The command never changes format on your behalf.
- For small labels, capture an overview first, then a targeted regional
  capture. Do not generate extra images speculatively.
- Compressed file size and model token use are different measurements. Do not
  claim token savings from WebP, do not assume WebP is always smaller, and do
  not lower quality for such claims: both formats are lossless.

### Partition refusal on a continent capture

The `partition` layer draws a generated artefact,
`world/maps/data/district_partition.json`. A continent capture with that layer
visible requires a current, decodable artefact. If it is missing, malformed or
stale, the capture is refused with the reason and two ways forward:

1. regenerate it — `regenerate_partition.py` above, or the editor's 分區
   chip — and capture again;
2. hide it for this image with `--hide partition`.

Never regenerate the artefact only to make a capture succeed when the work is
not ready to be game-ready, and never hand-edit it. Settlement and interior
captures, and a continent capture with `partition` hidden, never read the
artefact.

### Sources that do not load

A structural source or layout error refuses the capture and reports the
diagnostics: the editor would freeze on the same files. Loadable semantic work
in progress still captures, with its diagnostics in the result, because seeing
the map is useful before it is finished. A missing or stale reference index is
an advisory warning and does not block a capture.
