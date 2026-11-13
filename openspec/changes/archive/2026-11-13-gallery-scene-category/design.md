# Design: the scene gallery category

## Context

- `validate_gallery_subject_key` (Python) and `gallerySubject` (JS) admit only
  `portrait:character` and `portrait:monster`.
- `_card_artwork(subject, card, generation, terminal)` and `_alpha_terminal`
  build card descriptors with the person/monster alpha silhouette terminal;
  `_validate_card_artwork(row, selected)` checks them.
- `lore_codex._build_art` already describes a scene through
  `describe_scene(SceneTarget(identity=f"codex:{category}:{key}",
  trusted_identity=False, archetype=..., room_art_key=None,
  room_binding_invalid=False))`; `presenter._scene_bundled_resource` and the
  bundled-scene terminal (`descriptors.TERMINAL_SCENE_IMAGE`) exist.
- `_mutate` raises "no typed producer resolves this gallery kind" for scenes.
- `SCENE_ARCHETYPE_REGISTRY[key].display_name_zh` / `.scene_sentence`.

## Goals / Non-Goals

**Goals:** listing, artwork, description, validators, action resolution.

**Non-Goals:** landscape tiles and page (`gallery-landscape-page`); room
official images and the dream throne (never listed: they are not archetype
subjects).

## Decisions

1. Source: `_scene_groups(actor)` → one group `("scene", None, None, None,
   refs)` with `GallerySubjectRef(scene_subject_for(k), None,
   registry[k].display_name_zh[:64], False)` for `k in
   entered_archetypes(gallery_owner(actor))`; no group at all when nothing is
   entered, so the wall shows its empty state. Every category is enabled:
   `DISABLED_REASONS` becomes empty rather than deleted, because the selection
   store's refusal of a disabled category and the stored-view fallback from a
   disabled category stay specified (`webclient-gallery-management-actions`,
   `webclient-gallery-panel`); keep the `enabled`/`reason` fields.
2. Tile artwork for scene subjects: `validate_artwork(describe_scene(SceneTarget(
   identity=f"gallery:scene:{key}", trusted_identity=False, archetype=key,
   room_art_key=None, room_binding_invalid=False)))`.
3. Card rows for scene subjects: `_card_artwork(..., terminal=scene_terminal)`
   where `scene_terminal` is the archetype's bundled-scene terminal built the
   way `describe_scene` builds it (extract a presenter helper
   `scene_bundled_terminal(archetype)` in `world/art/presenter.py`).
   `_validate_card_artwork` and its JS mirror accept, for a scene subject,
   a `TERMINAL_SCENE_IMAGE` terminal naming the archetype's own bundled image
   (`scene.terminal:<key>`, bundled origin, terminal rank) or no terminal when
   the bundled snapshot does not admit that image (a logged startup fault
   that must not make the panel unavailable), and keep requiring the alpha
   terminal for portrait kinds. A scene original carries its decoded size and
   no face rectangle or stage. The card's terminal is deliberately the
   archetype's own image, not `describe_scene`'s declared terminal key.
   Chips follow the declared capabilities: the face chip appears exactly when
   the kind declares face rectangles, so a scene card's chips are
   `["目前預設"]`; scene rows are labelled 背景 / 背景（生成中）.
4. `description = SCENE_ARCHETYPE_REGISTRY[key].scene_sentence[:512]` when the
   selected subject is a scene, else `None`.
5. Validators: Python admits `ArtSubjectKind.SCENE`; JS regex becomes
   `/^(portrait:(character|monster)|scene):(.+)$/u` with directory `scene`
   for the scene kind; gallery URL checks use that directory. Add parity cases.
6. Actions: in `_mutate` and `_mutate_official`, `elif parsed.kind is
   ArtSubjectKind.SCENE: subject, entity = scene_subject_for(parsed.key), None`.
   A scene holds no official entry and no personal official preference, so
   `_mutate_official` refuses a scene subject with `official_unsupported`
   before any write.

## Risks / Trade-offs

- [A scene descriptor per tile is a heavier read than a portrait] → bounded by
  the archetype registry; no timing assertion.
