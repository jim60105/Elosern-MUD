# Proposal

## Why

The rite arrival card and the rite stage are designed around one illustration per ritual archetype (design `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` decision 13 and §12). Until now the `rite` panel's `art` is always null and both surfaces show quiet ink. This change gives each of the ten archetypes a scene art subject and puts its artwork descriptor into the panel.

The design assumed a rite subject could exist with no image. The existing scene-art contract does not allow that: every registered scene archetype must ship a required bundled illustration and a declared terminal (`bundled-scene-art`). This change follows the existing contract: the ten subjects are registered together with ten bundled illustrations, as one more scene pack. The surfaces keep their quiet ink state for a descriptor that cannot be produced.

## What Changes

- Ten scene archetypes `rite_spring`, `rite_statue`, `rite_megalith`, `rite_tower`, `rite_tree`, `rite_grave`, `rite_mine`, `rite_gate`, `rite_cliff`, `rite_plaza` are registered, each with a scene-art declaration, a terminal, and a bundled 16:9 WebP with its provenance record.
- Adopting the rite document fails when an archetype's derived art subject is not a registered scene archetype.
- The `rite` panel's `art` carries the archetype's scene artwork descriptor from the existing scene resolution chain; a descriptor that cannot be produced is null.
- The ten illustrations are accepted by human visual review recorded in each provenance record; no test judges an image's content.

A registered rite archetype is an ordinary scene archetype: generated quests and authored rooms may use it as a backdrop. That is accepted; it is an illustration and a sentence, nothing else.

## Capabilities

### New Capabilities

- `bundled-rite-scene-art`: the ten rite scene illustrations and their provenance.

### Modified Capabilities

- `bundled-scene-art`: the completeness scenario no longer names a count of images.
- `landmark-rite-content`: adoption requires a registered art subject per archetype.
- `landmark-rite-panel`: the panel carries the archetype's artwork descriptor.

## Impact

- Edits: `world/lore/scene_archetypes.py`, `world/art/scene_definitions.py`, `world/lore/rites/__init__.py`, `web/webclient/presentation/rite.py`, `content/map-reference-context.json` (regenerated), `world/art/tests/test_bundled_scenes.py`, `world/lore/tests/test_rite_content.py`, `web/webclient/presentation/tests/test_rite_panel.py`, `tools/test_data_freeze.json`, `.github/evennia-shards.json`.
- New: `web/static/art/scenes/rite_<archetype>.webp` and `.provenance.json` (ten pairs), `world/art/tests/test_bundled_rite_art.py`.
- Needs the maintainer's image generation service to produce the ten illustrations.

## Batch:

- depends-on: landmark-rite-panel
- depends-on: landmark-rite-content-completion
- conflicts: `landmark-rite-lighting` also edits `web/webclient/presentation/rite.py`; run serially with it. No shared file with the browser changes.
