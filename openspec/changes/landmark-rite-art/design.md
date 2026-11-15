# Design

## Context

Design document: `docs/superpowers/specs/2026-11-14-landmark-rites-design.md` §5 (asset key), decision 13, §12.1 (`art`). Existing code, read on 2026-11-14:

- `world/lore/scene_archetypes.py`: `SceneArchetype(key, display_name_zh, scene_sentence)`, the tuple `_SCENE_ARCHETYPES` and the frozen `SCENE_ARCHETYPE_REGISTRY`.
- `world/art/scene_definitions.py`: `SceneArtDefinition(key, terminal_key)`, the tuple `_SCENE_ART_DEFINITIONS` (lore order plus `dream_throne`), `TERMINAL_SCENE_KEYS = ("city_street", "forest_path")`, `BUNDLED_SCENE_MAX_FILE_BYTES = 524_288`, and the contract `scene_art_collection_problems()` which requires, for every declaration, a bundled `web/static/art/scenes/<key>.webp` that decodes and is exactly 16:9.
- The existing packs: `web/static/art/scenes/<key>.webp` with `<key>.provenance.json` (see `shrine_interior.provenance.json` for the exact sections `schema_version`, `key`, `label_zh`, `scene_sentence_zh`, `asset`, `file`, `source`, `license`, `production`, `processing`, `visual_review`), produced with sd-webui txt2img through `world.art.sd_worker.SDWebUIClient.generate`, the prompt templates `art.scene_prompt` / `art.negative_prompt` of `prompts/art.yaml`, and local WebP encoding through `world.art.formats.encode`. Pack data-contract tests: `world/art/tests/test_bundled_sacred_art.py` (the model for a new pack test) and `world/art/tests/test_bundled_scenes.py` (pins the collection to eleven keys in several assertions).
- `world.art.subjects.scene_subject_for(archetype)`; `world.art.presenter.describe_scene(target)` with `world.rules.art_view.SceneTarget(identity, trusted_identity, archetype, room_art_key, room_binding_invalid)`; `web.webclient.presentation.artwork.validate_artwork`.
- `world/rules/travel_events.py` `_scene_artwork(location)` is the precedent for producing a descriptor and degrading to `None` with a warning.
- `world.lore.rites.load_published` (`landmark-rite-content`), `world.lore.rites.shape.art_subject_key`, `web/webclient/presentation/rite.py` `rite_presenter` (`art` is `None`).
- `tools/map_reference_context.py` writes the registry keys into `content/map-reference-context.json`.

## Goals / Non-Goals

**Goals**

- Ten registered rite scene subjects with real bundled illustrations, resolved through the one existing scene chain.

**Non-Goals**

- No new art subject kind, resolution chain, media route or client artwork component.
- No change to the rite surfaces: they already render a descriptor or quiet ink.
- No exclusion of rite archetypes from quests, rooms or the map editor: `world/ai/scenario_director/validators.py`, `world/quests/` and `world/lore/registry_index.py` read the same registry, so a generated quest may name a `rite_*` scene. That is accepted.
- No test of what an image depicts. Visual acceptance is the human review recorded in each provenance record's `visual_review`.
- No placeholder, reused or copied image. If the image generation service is unavailable, stop and report; do not commit substitute files.

## Decisions

### D1. Archetypes and declarations

Append to `_SCENE_ARCHETYPES`, in this order, ten `SceneArchetype` entries with keys `rite_spring`, `rite_statue`, `rite_megalith`, `rite_tower`, `rite_tree`, `rite_grave`, `rite_mine`, `rite_gate`, `rite_cliff`, `rite_plaza`. Each `display_name_zh` is a short place name for the family (for example 泉之石龕 for `rite_spring`) and each `scene_sentence` is one Traditional Chinese sentence describing the empty place in the register of the design's §6.3 table: the landmark object, the light and the mood, with no person, no guardian figure and no sexual content.

Append to `_SCENE_ART_DEFINITIONS`, before the `DREAM_SCENE_KEY` entry so the lore order is kept: `SceneArtDefinition("rite_<archetype>", "forest_path")` for nine archetypes and `SceneArtDefinition("rite_plaza", "city_street")`.

### D2. Illustrations

For each key, generate one landscape with the existing production method named in Context, encode it as WebP, and commit `web/static/art/scenes/rite_<archetype>.webp` (exactly 16:9, at most 524288 bytes; the existing packs use 1536x864) with `rite_<archetype>.provenance.json` in the exact shape of `shrine_interior.provenance.json`. Composition rules, as for every stage backdrop: the landmark object in the upper two thirds, an unobstructed open foreground for the stage figures, no person or creature, no interface, watermark or readable lettering. The ten images must be visibly different places. Fill `visual_review` after inspecting each image at native scale and under the desktop cover crop.

### D3. Adoption check (`world/lore/rites/__init__.py`)

In `load_published`, after `load_rites` and before `install`: for every archetype key, `art_subject_key(key)` must be in `SCENE_ARCHETYPE_REGISTRY` (imported inside the function); otherwise raise `RiteContentError` with one `RiteDiagnostic(field_path=f"archetypes.{key}", code="art_subject_unregistered", message=...)` per missing key. Nothing is installed. `parse_rites_document` and `load_rites` stay pure and unchanged.

### D4. Panel artwork (`web/webclient/presentation/rite.py`)

```python
def _rite_artwork(archetype_key: str) -> dict | None: ...
```

Build `SceneTarget(identity=f"rite:{archetype_key}", trusted_identity=False, archetype=art_subject_key(archetype_key), room_art_key=None, room_binding_invalid=False)`, call `describe_scene(target)`, pass the result through `validate_artwork`, and return it. Any exception: `log_warn("landmark_rite_artwork_failed", exc=error, context={"archetype": archetype_key})` and return `None`. `rite_presenter` sets `art = _rite_artwork(site.archetype.key)`.

### D5. Reference context

Regenerate `content/map-reference-context.json` with the command documented at the top of `tools/map_reference_context.py` and commit the result.

### D6. Tests

- `world/art/tests/test_bundled_rite_art.py`: a pack data-contract test modelled on `test_bundled_sacred_art.py` with the ten owned keys: each file decodes under the admission limits, is 16:9 and within the byte bound, the ten are distinct by content hash, and each provenance record's checksum, size and dimensions match the file. Register it in `.github/evennia-shards.json` beside `world.art.tests.test_bundled_sacred_art` and in the `tools/test_data_freeze.json` ledger, seeded through `tools/test_data_lint_seed.json`. It also cross-checks each sidecar's `label_zh` and `scene_sentence_zh` against the archetype's registry entry: the panel presents that entry beside that illustration, so a later lore refinement re-records the sidecar (which states what was generated) rather than editing it.
- `world/art/tests/test_bundled_scenes.py`: this existing data-contract test pins the collection size; change its expected count from eleven to twenty-one wherever it asserts it and update its prose.
- `world/lore/tests/test_rite_content.py`: `load_published` with a synthetic document whose archetype has no registered art subject raises with `art_subject_unregistered` and installs nothing; with `SCENE_ARCHETYPE_REGISTRY` patched to contain the synthetic `rite_<key>` it installs.
- `web/webclient/presentation/tests/test_rite_panel.py`: with `describe_scene` patched to return a valid synthetic descriptor the panel's `art` equals it and the panel validates; with it patched to raise, `art` is `None`, the panel is still available and one warning is logged. The existing fixture's synthetic archetype needs no registered subject for these tests because `describe_scene` is patched.
- `world/lore/tests/test_registry_index_contract.py` and `world/maps/tests/test_static_map_references.py` read the scene archetype registry; run both and update any enumeration of archetype keys they hold.
- `world/art/tests/test_official_catalog.py` and `world/art/tests/test_gallery_fallback.py` pin the same committed collection from the startup-catalog and tracked-image sides: the former's bundled-snapshot counts and the latter's closed tracked-image allowlist both gain the ten rite paths.
- The new `中央廣場` display name enters the test-data gate's shipped-token universe and collides with three synthetic fixtures that used the phrase: `commands/tests/test_localized/test_xyz_grid_and_help.py` and `web/webclient-app/tests/world/island_labels.test.js` take a synthetic label, and `world/quests/tests/test_room_observation.py` derives its anchor room from the placement row's entrance cell instead of naming the shipped place key.
- Existing: `world.lore.tests.test_rite_content_document` must still pass (the shipped document's ten archetypes now all have registered subjects), as must `world.lore.tests.test_scene_archetypes` and `world.art.tests.test_scene_resolution`.

## Risks / Trade-offs

- This deviates from the design's "generated lazily, may be absent" wording because the scene-art contract forbids a registered archetype without a bundled image. The player-visible result is better: the art is present offline from the first arrival.
- Ten images add about one to five megabytes to the repository.
- Startup now also registers ten scene gallery subjects through the existing startup sync; that path is already bounded per subject.
