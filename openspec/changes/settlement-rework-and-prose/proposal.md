# Proposal

## Why

The generator from `settlement-graph-generator` refuses to touch an existing settlement document. That refusal blocks two jobs:

- **Rework of `capital_altoria`.** Its coordinates and roads are development data. The rework must keep every node that something joins on:
  - 23 interior doorways (`exterior.node`), which carry the places and service hosts in `world/lore/settlements/places*.py`;
  - the district landmark `central_plaza`;
  - the city gate `south_gate`;
  - the two wilderness gates.
- **Real names and descriptions.** Generated nodes get only role labels and empty descriptions. The zh-TW prose pass needs a machine-readable brief to work from, and a safe way to apply its output.

## What Changes

- Add `generate LOCATION_ID --replace --bind FILE` to `tools/settlement_synthesis`. It generates a fresh plan and then applies explicit bindings of existing node ids to plan slots.
  - Bindings: `"<existing_id>": "<slot_id>"`, or `"<existing_id>": "nearest:<slot_id>"`, which takes the closest free approach or filler slot.
  - Protected nodes: the nodes named by an interior doorway, a district landmark, an external incoming reference or the city gate, plus the anchor. If the reference index is missing, every existing node is protected.
  - Refusals: a missing binding for a protected node, an unknown or duplicate binding, or an anchor bound to a non-anchor slot. A refused run writes nothing.
  - A bound node keeps its id, `key`, `desc`, `typeclass` and `scene_archetype`, and takes its new position, roads and directions from the plan.
  - Unbound, unreferenced existing nodes are dropped and reported.
  - `options`, `exit_prototype` and `city_gate` are carried over.
  - The output must pass the terrain-fit lint, and the write is atomic.
- Add `brief MAP_ID`, a read-only JSON prose brief. It lists every node's id, key, role, bearing and distance from the anchor and whether its `desc` is empty. It also gives the settlement summary: display name, kind, nation, population, morphology, water and uphill bearings and neighbour display names.
- Add `prose MAP_ID FILE`. It applies `{"<node_id>": {"key": "...", "desc": "..."}}` and changes only those fields. Unknown ids and empty strings are rejected atomically. It writes through the codec.
- Add a prose standard for agent writers in `docs/development/settlement-synthesis.md` § Prose pass: zh-TW, JRPG sword-and-magic setting, in-world only, consistent with the settlement archetype.
- Update the skill docs: rework recipe, brief, prose and a "never edit generated YAML by hand for prose" note.

## Capabilities

### New Capabilities

- `settlement-map-rework`: reference-preserving replacement with explicit and nearest bindings, plus the read-only brief and the key/desc-only prose application.

### Modified Capabilities

None.

## Impact

- Edited: `tools/settlement_synthesis/generate.py`, `workspace.py` and `__main__.py`.
- New: `tools/settlement_synthesis/rework.py`, `tools/settlement_synthesis/prose.py` and `tests/test_settlement_map_rework.py`. The tests are synthetic, and the new test is registered in `.github/top-level-shards.json`.
- Docs: `docs/development/settlement-synthesis.md` and `.agents/skills/map-data-authoring/references/settlements.md`.
- No map data is changed by this change. `capital_altoria` is reworked in `altoria-capital-river-rework`.
- Human-reviewed, not tested: prose tone, wording and fidelity to the lore. The checklist is in `docs/development/settlement-synthesis.md` § Human review.

## Batch:

- depends-on: settlement-graph-generator
- conflicts: the same tool, documentation and shard files as `settlement-graph-generator`. They stay serial through the dependency.
