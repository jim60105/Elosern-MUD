# Design: webclient-gallery-actions

## D1 — Adapters are thin, backend is the only authority

Every gallery rule already lives behind
`world/art/service.py::request_gallery_image` and the `world/art/gallery.py`
single-writer boundary (kind capability gates, typed errors, monster one-card
cap with replace semantics, tolerant reads, the no-create snapshot reader). Each
adapter therefore: re-resolves `subject_key` through the kind's typed producer
(never trusting the caller's key alone), re-resolves `image_id` against
`cards_for`, calls exactly one public API, and maps typed errors
(`ArtSubjectError`, `GalleryPromptError`, `GalleryRecordError`,
protocol-side `malformed_payload` for schema failures) to stable result codes
with zh-TW messages, following the `character_actions` exemplar. No adapter
assigns `.db` or gallery state directly.

## D2 — Binding save is a current-snapshot capture, not an item picker

Per the session decision (user decision #2): the binding snapshot the backend
stores is the CURRENT normalized equipment snapshot at save time. The mockup's
per-slot 指定裝備 dropdown is reconciled by constraining what the panel offers:
an enabled slot contributes its currently-equipped value, and the dropdown can
only show that current value or the empty-slot state. Hence the wire payload is
only `{subject_key, image_id, slots}` — item keys never cross the wire, so a
tampered payload cannot bind an image to equipment nobody wears. An empty
enabled slot binds `None`/`[]` (the all-empty binding stays legal).

## D3 — Overlap warnings are panel facts, never client rules

規則重疊提醒 data is computed by the shipped panel presenter (see
`webclient-gallery-panel`: bound cards whose masked slots all evaluate equal on
the current snapshot overlap) and travels in the committed payload. The binding
drawer renders those facts verbatim (other card's name + its condition rows +
查看 jump). The save adapter performs no warning logic; a client never
evaluates matching.

## D4 — Selection rides the panel's store

`gallery.subject.select` is registered here (this change owns the action
registry hunk) but writes the session store shipped by `webclient-gallery-panel`
— presentation state only, `affected_panels=("gallery",)`, stable
`unknown_subject` when the key names no rail entry.

## D5 — Errors are reported states

AI-offline is already §12.3.1: `gallery.generate` SUCCEEDS as an enqueue
(request never probes); the unreachable-server failure surfaces later on the
panel as the failed row. Adapter-level typed rejections (bad field id, oversized
prompt, monster binding attempt, unknown card) are `rejected` results with
stable codes (`unknown_field`, `prompt_too_long`, `binding_unsupported`,
`unknown_card`, …) and bounded zh-TW lines — the client shows the server line
verbatim (existing non-success-message requirement).

## D6 — Monster 替換 surfaces truthfully

For the monster kind, `gallery.generate` is legal (capability-gated: no fields,
no free text, no binding) and the backend's capped append REPLACES the single
card (`gallery_card_replaced`). The adapter reports success with the new
`image_id`; the panel then shows one card and no pending ghost after settle. The
binding/default affordances for monsters are absent because the panel's
capability flags say so, not because actions hide them.
