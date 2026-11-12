# Design: declare per-kind card operations

## Context

`world/art/gallery_kinds.py` holds one `GalleryKindCapabilities` record per
kind value (`portrait:character`, `portrait:monster`, `scene`) with
`has_gallery`, `store_directory`, `max_cards`, `supports_bindings`,
`requires_age_precondition`, `supports_field_selection`, `supports_free_text`,
a frozen `__setattr__`-based record, `as_dict`/`__repr__`, and
`validate_declaration_contract(kind_values)`. Writers in `world/art/gallery.py`
already read `supports_bindings` and `max_cards` from it. The face rectangle
is today "shared gallery-card metadata, not a kind capability"
(`service.request_gallery_image` comment) and every kind accepts it.

## Goals / Non-Goals

**Goals:** three declared facts; writer refusal; adapter codes.

**Non-Goals:** no change to the card contract (every stored card still carries
`face_rect` and `stage`; an undeclared kind's cards simply keep the shared
default rect and identity stage); no v3 wire field; no change to the scene
kind's `has_gallery` (that is `scene-kind-gallery`).

## Decisions

### D1. Pull the two geometry facts forward into stage 1

The design places them in Specification 3, but D5 (stage 1) already requires
the footer to be "what the declared kind capabilities produce, not a kind
comparison in the client", and the design states the panel shape must not be
reshaped by later specifications. Declaring them now lets the v4 panel carry
them from its first version. Values for character and monster match D5 exactly
(臉框 and 舞台位置 shown for both).

### D2. A third fact for deletion (planner decision, flagged)

D5's table gives monster cards no 刪除 while Specification 3 gives scene
cards 刪除; both kinds cap cards at one. No existing fact separates them, so a
capability-driven footer needs `supports_card_delete`. Character true,
monster false, scene false now (true when `scene-kind-gallery` makes scenes
gallery-bearing). The backend enforces it so hiding is never the guarantee.

### D3. Field order and record changes

Append the three fields after `supports_free_text` in `__slots__`, the
constructor, `__setattr__`-freeze, `as_dict`, `__repr__`; extend
`validate_declaration_contract` with the bool check and "gallery-less kind
declares none of them".

### D4. Guards (exact sites)

- `gallery.update_card_face_rect`: before `record_for`, raise
  `GalleryRecordError(f"subject kind {kind!r} declares no face rectangle support")`
  when `not capabilities_for(subject.kind.value).supports_face_rect`.
- `gallery.set_stage`: same pattern, "declares no stage support".
- `gallery.set_official_geometry`: refuse a non-None `face_rect` / `stage`
  component with the same messages.
- `service.request_gallery_image`: refuse a non-None `face_rect` argument with
  the face-rectangle message before validating it.
- `gallery_actions._mutate`: for `gallery.card.delete`, refuse with
  `delete_unsupported` before the card lookup when
  `not capabilities_for(subject.kind.value).supports_card_delete`; the sole
  writer's `remove_card` stays unguarded because internal callers (browser
  support `_revoke_source`) remove cards for test staging.
- `gallery_actions._error_code`: map the two message fragments to
  `face_rect_unsupported`, `stage_unsupported`, checked
  before the existing `text.startswith("stage")` branch. Add zh-TW messages
  beside the existing code table (`此類圖片不能調整臉框。`,
  `此類圖片不能調整舞台位置。`, `此類圖片不能刪除，請改用重新生成。`).

## Risks / Trade-offs

- [The current panel offers 刪除 on monster cards until the window ships] →
  the press is refused with a truthful message; no data is lost.
- [`supports_card_delete` is not in the design's list of two facts] → flagged
  in the programme report for the user to confirm.
