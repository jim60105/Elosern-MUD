# Proposal

## Why

There are 59 national settlements without a local map: 2 capitals, 19 cities, 27 towns and 11 ports. Drawing them all by hand would take too long, and hand drawing tends to produce grid-like layouts that ignore rivers and coasts. `settlement-terrain-fit` gives us site context, a size budget and a fit lint. What is still missing is a generator that turns those into a street graph:

- the graph grows from the terrain;
- the footprint is the right size;
- gates face the neighbouring settlements;
- archetype roles are placed: quay on the water, temple and lord's seat on high ground, crafts downstream, market where the approach roads converge;
- the directed roads follow the editor's rules.

The generator only does the coarse fit. A person finishes bridge placement, district shape and appearance in the map editor.

## What Changes

- Add the `generate` command to `tools/settlement_synthesis`:
  - `generate LOCATION_ID [--gates s,e] [--plan-only]` generates one map;
  - `generate --missing --nation NATION [--plan-only]` generates a batch.
- Generation is deterministic and seeded by the location id. It runs in these steps:
  1. Choose a settlement class from nation and kind: human capital, human town, port, beast capital or beast town.
  2. Choose a morphology from the site: beast ring, harbour crescent, river crossing, waterside linear, hill terraces or crossroads. A port with no water within reach is refused.
  3. Grow a 4-connected, walkable footprint around the location cell, reaching toward the water first. It avoids other footprints, gate approaches, location cells, harbour sites and wilderness landmarks, and keeps its bounding-box midpoint on the location cell.
  4. Place the nodes: anchor `central_plaza` on the location cell; gates toward forced bearings, then the own capital, then neighbours, then fords; approach streets that converge on the plaza; catalogue roles placed by terrain; jittered filler inside a metre envelope sized from the built-up area.
  5. Connect the nodes along a Gabriel graph: a spanning tree, plus loops up to the tier target. Roads never cross water except through a `ford` or `bridge` node, and no node has more than 6 roads.
  6. Assign each road a direction in the 8-way compass, so that no node has two outgoing roads in the same direction.
- The output is written through the `elosern_map_core.codec` functions `document_from_data` and `serialize_document`, so it matches the editor's bytes. It must pass the terrain-fit lint before anything is written.
- Generated node `key`s are role labels in zh-TW, and `desc` is empty. A separable prose pass fills both (`settlement-rework-and-prose`).
- Safety:
  - an existing settlement file is never overwritten. Replacing a file under explicit ID bindings is part of `settlement-rework-and-prose`;
  - `--plan-only` writes nothing;
  - writes are atomic.
- The role catalogue (`tools/settlement_synthesis/roles.py`) comes from the place matrix in `docs/lore/settlement-locations.md`:
  - only a port gets a sea quay and a harbour office;
  - a beast settlement gets a tribal hall, an assembly ground, an ancestral altar and a prominent training ground, and has no academy, inn, bathhouse or exchange;
  - the academy and the palace appear only in a human capital.

## Capabilities

### New Capabilities

- `settlement-graph-generation`: deterministic settlement generation, morphology and dry-port refusal, footprint growth, structural guarantees, gate selection, catalogue-driven role placement and the never-overwrite and batch-order command contract.

### Modified Capabilities

None.

## Impact

- New files: `tools/settlement_synthesis/roles.py`, `tools/settlement_synthesis/generate.py` and `tests/test_settlement_graph_generation.py`. All tests are synthetic, and the new test is registered in `.github/top-level-shards.json`.
- Edited: `tools/settlement_synthesis/__main__.py` and `tools/settlement_synthesis/workspace.py`. The workspace gains a `blocked_cells` helper and an atomic writer.
- Docs: the generation section in `docs/development/settlement-synthesis.md`, plus the "Creating a new local map" recipe in `.agents/skills/map-data-authoring/references/settlements.md`.
- No map data is written by this change, and no runtime, schema or dependency changes are made.
- Qualities that are human-reviewed and not tested: how organic a layout looks, the naming feel of the role labels, and whether a morphology suits a given place. Design D9 lists the review checklist in `docs/development/settlement-synthesis.md` § Human review.

## Batch:

- depends-on: settlement-terrain-fit
- conflicts: `tools/settlement_synthesis/__main__.py`, `workspace.py`, `docs/development/settlement-synthesis.md`, `.github/top-level-shards.json` and the skill references are also edited by `settlement-terrain-fit` (before this change) and `settlement-rework-and-prose` (after it). The dependency chain keeps those edits serial.
