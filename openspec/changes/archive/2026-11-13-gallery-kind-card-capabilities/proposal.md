# Proposal: declare per-kind card operations (face rectangle, stage, deletion)

## Batch:

Gallery window programme, stage 1 (pulled forward from "Specification 3" of
`docs/superpowers/specs/2026-11-12-gallery-window-design.md`, see design D1).

- depends-on: none (may land in parallel with `remove-baseline-visual-species`)
- conflict: `world/art/gallery_kinds.py` is edited again by `scene-kind-gallery`
  (scene record values only); `web/webclient/actions/gallery_actions.py` is
  edited again by `gallery-v4-cutover` and `gallery-mutation-admission`
  (different functions). Land this first.

## Why

The gallery window's footer (design D5) must be capability-driven, never a
kind comparison in the client. Its buttons differ by kind in three ways the
current declaration cannot express: whether a card may carry a face rectangle,
whether it may carry a stage transform (scenes: neither), and whether a card
may be deleted by the player (monsters: no; characters and scenes: yes). The
design names the first two as new declared facts; the third is needed to
reconcile D5's monster row (no 刪除) with Specification 3's scene footer (刪除
and 重新生成) without comparing kinds.

## What Changes

- `world/art/gallery_kinds.py` declares three new booleans per kind:
  `supports_face_rect`, `supports_stage`, `supports_card_delete`. Character:
  all true. Monster: face rect and stage true, delete false. Scene (still
  gallery-less here): all false.
- The sole writer refuses, with a typed error, a face-rectangle update, a
  stage update, an official geometry component and a generation face rect for
  a kind that does not declare the matching fact; `gallery.card.delete`
  refuses a kind that does not declare deletion.
- The management adapters map these refusals to stable codes
  `face_rect_unsupported`, `stage_unsupported`, `delete_unsupported`.
- **BREAKING (pre-release)**: `gallery.card.delete` on a monster card is now
  refused. Monster cards are replaced by regeneration, as D5 shows.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `art-gallery-kind-capabilities`: three new declared facts and their
  enforcement.
- `webclient-gallery-management-actions`: stable refusal codes for the three
  undeclared operations.

## Impact

- Code: `world/art/gallery_kinds.py`, `world/art/gallery.py`
  (`update_card_face_rect`, `set_stage`, `set_official_geometry`,
  `remove_card`), `world/art/service.py` (`request_gallery_image` face rect),
  `web/webclient/actions/gallery_actions.py` (`_error_code`).
- The v3 panel wire is unchanged; the v4 panel (`gallery-v4-validators`)
  carries the facts in `capabilities`.
- The current `GalleryDetailRail.vue` still shows 刪除 for a monster card;
  the press is refused with the new code until the window replaces the rail.
- Estimate: 5 hours (declaration and contract 1 h, four writer guards 1.5 h,
  adapter codes 0.5 h, tests 1.5 h, spec and gates 0.5 h).
