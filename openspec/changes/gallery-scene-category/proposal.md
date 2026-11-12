# Proposal: the scene gallery category

## Batch:

Gallery window programme, stage 3 ("The category" of Specification 3 in
`docs/superpowers/specs/2026-11-12-gallery-window-design.md`).

- depends-on: scene-classic-fallback-removal
- depends-on: entered-archetype-record
- depends-on: gallery-people-category
- depends-on: gallery-landscape-page
- conflict: `web/webclient/presentation/gallery_categories.py`, `gallery.py`,
  `web/webclient/actions/gallery_actions.py`, both gallery validator mirrors.
  `gallery-people-category` last modified the category-order requirement.

## Why

Scene backgrounds can now be gallery cards, but the window still shows 背景
disabled. This change lists the archetypes the character has entered, gives
each tile the background in effect, carries the scene sentence for the page,
and lets the existing actions generate and delete scene cards.

## What Changes

- `gallery_categories.py`: `scene` source over
  `world.rules.scene_visits.entered_archetypes(owner)`; `scene` enabled (no
  disabled category remains).
- `gallery.py`: scene tile artwork via `describe_scene` with an untrusted
  gallery identity; scene card rows use the bundled-scene terminal;
  `description` = `SceneArchetype.scene_sentence` while a scene is selected;
  `validate_gallery_subject_key` admits the scene kind.
- JS mirror: `gallerySubject` admits `scene:<key>` with directory `scene`;
  the card-artwork rule accepts the scene terminal for scene subjects.
- `gallery_actions.py`: `_mutate`/`_mutate_official` resolve scene subjects
  with `scene_subject_for`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-categories`: scene enabled; scene source.
- `webclient-gallery-panel`: scene tile artwork, card terminal, description.
- `webclient-gallery-management-actions`: scene subjects resolve.

## Impact

- Estimate: 7.5 hours (source 1 h, scene artwork and description 1.5 h,
  validator mirrors and parity cases 2 h, adapter resolution 0.5 h, tests
  2 h, gates 0.5 h).
