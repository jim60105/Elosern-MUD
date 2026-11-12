# Design: gallery mutations re-derive subject admission

## Context

`web/webclient/actions/gallery_actions.py`: the six card adapters call
`_mutate(action_id, payload)` and the four official adapters call
`_mutate_official(action_id, payload)`; neither receives `actor`. Both parse
the subject, resolve it, then branch per action. `gallery_categories`
(`gallery-category-sources`) exposes `is_subject_admitted(actor, subject_key)`
which raises `GalleryCategoryError` when the owner cannot be resolved.

## Goals / Non-Goals

**Goals:** one admission check on every mutating path.

**Non-Goals:** selection actions (already validated against the listed
category); changing service-level preconditions.

## Decisions

- Change signatures to `_mutate(actor, action_id, payload)` and
  `_mutate_official(actor, action_id, payload)`; each adapter passes `actor`.
- Insert, right after `validate_gallery_subject_key(...)` succeeds and before
  the kind-specific resolution:

  ```python
  try:
      admitted = is_subject_admitted(actor, payload["subject_key"])
  except GalleryCategoryError:
      admitted = False
  if not admitted:
      log_warn("gallery_action", context=context)
      return _rejected("subject_not_admitted")
  ```
- Add `subject_not_admitted` → `這個對象不在你的圖庫中。` to the code/message
  table used by `_rejected`.
- Order relative to existing refusals: malformed payload (dispatcher) →
  subject grammar → admission → `binding_unsupported` → `official_read_only`
  → card lookup. A direct official identity for a non-admitted subject
  therefore reads `subject_not_admitted`.

## Risks / Trade-offs

- [Admission recomputes categories per mutation] → bounded sources, one call.
- [Existing tests that mutate a non-party NPC's gallery] → they must create
  the subject as a party companion or account character; this is the intended
  behaviour change.
