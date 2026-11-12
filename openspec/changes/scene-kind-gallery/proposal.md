# Proposal: the scene kind becomes gallery-bearing

## Batch:

Gallery window programme, stage 3 ("The scene kind becomes gallery-bearing" of
Specification 3 in `docs/superpowers/specs/2026-11-12-gallery-window-design.md`).

- depends-on: gallery-kind-card-capabilities
- conflict: `world/art/gallery_kinds.py` (scene record values),
  `world/art/presenter.py` (scene chain), `world/art/queue.py`/`gallery.py`
  guard messages; `scene-asset-migration` and `scene-classic-fallback-removal` edit
  `world/art/service.py` and the scene chain afterwards.

## Why

Generated scene images are classic asset records with no gallery: only staff
can regenerate them and the gallery window cannot show them. The design makes
the scene kind gallery-bearing with the monster kind's one-card shape and no
geometry, and makes the background chain's generated step read the scene
gallery's default card.

## What Changes

- Scene capability record: gallery, directory `scene`, one card, deletion
  allowed, no bindings, age precondition, field selection, free text, face
  rectangle or stage.
- The scene chain's generated position reads the archetype's scene gallery
  default card first, then (until `scene-asset-migration`) its classic `done`
  record; the chain order is unchanged. Generation state and retention read
  the gallery facts first.
- `@art requeue scene:<archetype>` and `@art retry` follow the new
  declaration automatically (`commands/art.py` already routes by
  `has_gallery`).
- Producers are unchanged here (room entry and startup still write classic
  records; `scene-asset-migration` switches them), so every intermediate
  state keeps showing a generated background.
- `art-staff-commands` stops claiming that no player-triggered generation
  surface exists.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-gallery-kind-capabilities`: scene declaration; the gallery-less
  scenario uses a synthetic kind.
- `art-gallery-model`: `scene` kind directory.
- `art-gallery-generation`: scene requests go through the seam.
- `art-staff-commands`: scene requeue is a gallery request; player
  generation only through gallery actions.
- `scene-artwork-presentation`: generated position source.

## Impact

- Code: `world/art/gallery_kinds.py`, `world/art/presenter.py`
  (`describe_scene`, `_scene_generated_resource`,
  `_scene_retained_output_identity`), message strings in `world/art/gallery.py`
  and `world/art/queue.py` that say "scene subjects have no gallery".
- Tests: kind contract tests, presenter scene tests, staff command tests,
  `web/webclient/presentation/tests/test_art_panel.py` scene cases.
- Estimate: 7 hours (declaration and guards 0.5 h, scene chain gallery-first
  with generation facts and retention 2.5 h, tests 3 h, spec and gates 1 h).
