# Proposal: gallery mutations re-derive subject admission

## Batch:

Gallery window programme, stage 1 (design D6 "Authority").

- depends-on: gallery-v4-cutover
- conflict: `web/webclient/actions/gallery_actions.py` (`_mutate`,
  `_mutate_official`, adapter signatures); `gallery-people-category` and
  `gallery-scene-category` later only extend the category sources this reads.

## Why

Today a gallery mutation accepts any subject key the resolver can resolve, so
a client can edit the gallery of any named character in the world. The design
requires every mutating action to re-derive, before writing, that its subject
is admitted for the actor: a member of any enabled category. Being absent from
the currently listed category is not a rejection; being in no category is.

## What Changes

- The ten mutating gallery adapters (`gallery.generate`,
  `gallery.default.set`, `gallery.card.delete`, `gallery.face_rect.update`,
  `gallery.stage.update`, `gallery.binding.save`, `gallery.official.select`,
  `gallery.official.clear_selection`, `gallery.official.geometry.set`,
  `gallery.official.geometry.clear`) check
  `gallery_categories.is_subject_admitted(actor, subject_key)` after payload
  admission and subject parsing and before any card read or write; a refusal
  returns `subject_not_admitted` with the standard three-panel refresh.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-gallery-management-actions`: mutations require an admitted
  subject.

## Impact

- Code: `web/webclient/actions/gallery_actions.py`.
- Tests: the gallery action test module; the companion/age tests keep passing
  because party companions are admitted.
- Estimate: 4 hours (signature threading and check 1 h, tests for every
  adapter family 2.5 h, gates 0.5 h).
