# Proposal

## Why

`landmark-rite-content-model` gives the rite document a model and a loader but ships no document. Rites cannot be performed, listed or presented until authored content exists and the running server holds it. This change ships the first half of the document and adopts it at startup. It is additive: nothing a player sees changes, because no rule or surface reads the snapshot yet.

## What Changes

- New shipped document `world/lore/rites/content/landmark_rites.yaml` with five of the ten ritual archetypes of the design's §6.3 (`spring`, `statue`, `megalith`, `tower`, `tree`), two options per archetype, one `self` scene per option, `watch: null` on every option, and an assignment of every shipped district to one of those five. Districts whose landmark belongs to a family not yet authored take a provisional archetype until `landmark-rite-content-completion`.
- A startup step loads the document against the published district world, installs the snapshot and refuses to start on an invalid document.
- A human-reviewed authoring review, `docs/lore/landmark-rites-review.md`, records the check of every scene against the adult-content and authoring rules of the design's §11. That review is human judgement; no test asserts tone, wording or the narrative beats.
- One data-contract test proves the shipped document validates against the shipped district document.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `landmark-rite-content`: the shipped document is adopted at startup.

## Impact

- New: `world/lore/rites/content/landmark_rites.yaml`, `docs/lore/landmark-rites-review.md`, `world/lore/tests/test_rite_content_document.py`.
- Edits: `world/lore/rites/__init__.py` (`load_published`), `server/conf/at_server_startstop.py` (one startup step and `STARTUP_STEP_ORDER`), `server/conf/tests/test_startup_observability.py`, `world/lore/tests/test_rite_content.py`, `.github/evennia-shards.json`, `tools/test_data_freeze.json`.
- The other five archetypes (`landmark-rite-content-completion`), the watch perspectives, a third option and art are separate changes.

## Batch:

- depends-on: landmark-rite-content-model
- conflicts: `landmark-rite-content-completion`, `landmark-rite-watch-perspectives` and `landmark-rite-third-option` edit the same YAML document and review document; they run after this change and serially. `landmark-rite-art` edits `world/lore/rites/__init__.py`.
- parallel with: `landmark-rite-settlement`.
