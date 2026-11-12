# Design: register the gallery category selection action

## Context

`_gallery_subject_select_adapter` in `web/webclient/actions/gallery_actions.py`
wraps `select_gallery_subject(session, actor, key)`, sets
`affected_panels = AFFECTED_GALLERY_PANELS` and logs `gallery_action` (info on
success, warn otherwise). Payload validators use `_payload(payload, keys)`.
`gallery-v4-presenter` provides `select_gallery_category(session, actor,
category)` returning a result dict with `unknown_category` on refusal.

## Goals / Non-Goals

**Goals:** one registered adapter mirroring the subject-select adapter.

**Non-Goals:** switching `gallery.subject.select` to the v4 store (cutover);
client dispatch (window).

## Decisions

- `validate_gallery_category_select_payload(payload)`: an exact key set of
  `{"category"}` checked directly (the shared `_payload` helper always
  validates `subject_key`, which this payload does not carry), then the value
  must be one of `CATEGORY_KEYS` (`"mine"`, `"party"`, `"people"`,
  `"monster"`, `"scene"`) else `GalleryActionError`, the `ValueError` every
  gallery validator raises (→ `malformed_payload`).
- `_gallery_category_select_adapter(actor, payload, session=None)`: same shape
  as `_gallery_subject_select_adapter`. `_context` today reads
  `payload["subject_key"]`; give this adapter its own context dict
  `{"category": payload["category"], "action_id": "gallery.category.select"}`.
- Register beside `gallery.subject.select` in `registry.py`.
- The command-echo catalog pins every registered action: the id joins the
  silent presentation controls in `command_echo.js`, both lists of
  `command_echo_coverage_manifest.json`, and the Node and Vitest coverage
  tables, beside `gallery.subject.select`. It has no typed-command equivalent.

## Risks / Trade-offs

- [The action is registered before the panel reads its store] → harmless; it
  publishes the same three panels as subject selection and writes only
  presentation state.
