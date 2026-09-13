# Design: webclient-gallery-actions

## D1 — Adapters are thin, backend is the only authority

Every gallery rule lives behind
`world/art/service.py::request_gallery_image` and the `world/art/gallery.py`
single-writer boundary (kind capability gates, typed errors, monster one-card
cap with replace semantics, tolerant reads, the no-create snapshot reader) —
plus the in-place card writers and public subject-key resolver now shipped by
the dependency change `gallery-card-update-api`. Each persistent-mutation adapter
therefore: re-resolves `subject_key` — character kind through
`resolve_gallery_subject_by_key` (yielding subject AND live entity; the age
precondition and `snapshot_for` need the entity), registry kinds through the
typed producer, never trusting the caller's key alone — re-resolves `image_id`
against `cards_for`, calls exactly one public API, and maps typed errors
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

## D7 — Wire validation and domain refusal are separate layers

Exact payload validation is kind-neutral. Unknown/duplicate catalog ids,
prompts over 512 code points, non-printable text, malformed UUIDs, invalid
rectangles, and unknown/duplicate/empty slot selections return the dispatcher's
`malformed_payload` before any adapter or `gallery_action` event runs.
Valid catalog fields on a monster reach the service and return
`field_selection_unsupported`; nonempty printable free text returns
`free_text_unsupported`. The defensive service-error mapping retains
`unknown_field`, `prompt_too_long`, and `invalid_prompt` (including duplicate
field errors) for direct adapter calls or future service-side refusals.
Python's shared prompt validator rejects all Unicode C and Z categories except
ASCII space; the JS mirror follows that actual contract. The original accepted
payload is preserved; only the service normalizes fields and prompt text.

Binding refusal precedes card lookup for a kind without bindings, matching the
public writer. Otherwise each card is looked up through `cards_for`. Binding
mask order is the backend's declared `SLOT_ORDER`, not client list order.
Every completed result targets only `gallery`, including domain rejections.
Selection is the explicit exception to D1's mutation resolver: the rail store
validates current membership and owns the session-only write.

The JS export `validateGalleryActionPayload` is the exact six-action mirror
for the subsequent gallery UI; this change does not add a transport or Vue
component. All six actions are explicitly silent in the command-echo catalog
because D14 adds no text commands.
