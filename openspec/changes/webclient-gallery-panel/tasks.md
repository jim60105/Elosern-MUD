# Tasks: webclient-gallery-panel

## 1. Read-model and presenter

- [ ] 1.1 New `web/webclient/presentation/gallery.py` with `GALLERY_SCHEMA_VERSION = 1`
  and `gallery_presenter(context)`: resolve the session's selected subject
  (default the puppet; unknown selection → puppet), build the bounded subject
  rail (puppet first; live gallery-bearing characters with active-party
  companions first from the party surface; every `MONSTER_TIER_REGISTRY`
  subject via `monster_subject_for`), cap at 24 rows by precedence group.
- [ ] 1.2 Card rows from `world/art/gallery.py::cards_for(selected_subject)`:
  newest-first by `created_at` (append order tiebreak), exact key set
  `image_id, status, label, url, face_rect, is_default, chips,
  requested_fields, binding_present, created_at` (label server-derived from the
  row timestamp; pending label suffixed 「生成中」); URL built only from the validated stored
  identity (subject gallery prefix, closed extensions, store-root confinement)
  exactly as the `art-gallery-resolution` presenter discipline; `null` url only
  for synthetic rows.
- [ ] 1.3 Server-authored chips: mask labels 主手/副手/防具/飾品 in declared slot
  order; 「自訂臉框」 vs 「預設臉框」 against `DEFAULT_FACE_RECT`; 「目前預設」 iff
  `default_image_id` matches. Labels are presenter constants; no client
  composition.
- [ ] 1.4 Pending rows: add one read-only accessor (bounded, ≤8 entries) to the
  art queue surface returning a subject's in-flight gallery job
  `{image_id, enqueued_at}`; render each as one `status: "pending"` row merged
  into card order by timestamp.
- [ ] 1.5 Failed row: when the record carries `last_error_code`, exactly one
  `status: "failed"` row (bounded message 「暫時無法生成，稍後再試」, stable code,
  `last_error_at` timestamp, null url/face_rect, no reused image_id).
- [ ] 1.5b `binding_warnings`: current snapshot once; non-default bound cards
  whose masked slots all evaluate equal to it, newest-first ≤5, each
  `{image_id, label, conditions}` with per-slot zh-TW condition lines
  (accessories 「任一」); empty list for kinds without binding support.
- [ ] 1.6 `filters` counts `{all, defaults, bound, pending, failed}` computed
  over the listed rows; `equipment_summary` (character kind: four slots with
  normalized values + registry display names + accessories sorted and n/5
  count, via the no-create stored-state reader discipline; null for kinds
  without binding support); `capabilities` from
  `gallery_kinds.capabilities_for`; `error_state` from the record.
- [ ] 1.7 Read-only proof: rendering twice mutates no record, card, job, or
  file; never imports `world.art.connectivity`; degrades SD-offline to rows,
  not unavailability.

## 2. Exact validator

- [ ] 2.1 `validate_gallery(payload)` in the same module: exact top-level key
  set (incl. `binding_warnings`), rail row key set and ≤24 rows, card row exact key set, `status`
  vocabulary, chip/label code-point bounds, face-rect re-use of the shared
  face-rect validation, URL re-use of the ≤129-char gallery-URL bound, unique
  `image_id` values, non-negative filter counts, envelope `MAX_CANONICAL_JSON_BYTES`
  guard, lone-surrogate rejection (party/objectives precedent).
- [ ] 2.2 Reject incoherent forms: failed/pending rows with a url, more than
  one failed row, `selected` naming no rail row, `equipment_summary` present
  for a kind declaring no binding support.

## 3. Session selection store

- [ ] 3.1 Per-presentation-sequence selection store in the presentation layer
  keyed by transport+puppet, retired at disconnect, unpuppet, and account
  character switch — wired beside the existing options-state retirement seams.
- [ ] 3.2 Expose the store's write API (validate subject-key grammar against the
  rail, `unknown_subject` reason data for the companion actions change's adapter
  to consume); this change ships no ui_action registration itself.

## 4. Registration and mirroring

- [ ] 4.1 Register `gallery` in `web/webclient/presentation/registry.py`
  (unavailable reason `("gallery_unavailable", "肖像圖庫目前無法顯示")`).
- [ ] 4.2 `web/static/webclient/js/elosern/protocol.js`: `PANEL_ALLOWLIST.gallery
  = 1`, full mirrored validator with identical bounds, dispatcher branch,
  exported constants; the Vue protocol mirror table updated in the same change.

## 5. Observability and traceability

- [ ] 5.1 Facade events: `gallery_panel_selected` info on a selection change
  (context `subject`, `kind`); no Evennia logger imports.
- [ ] 5.2 New test module (`web/webclient/presentation/tests/test_gallery_panel.py`,
  selection-store lifecycle covered here) registered in
  `.github/evennia-shards.json` in this change; new main-spec requirements
  tagged `@covers_requirement`.
- [ ] 5.3 Dual-direction Python/JavaScript parity tests cover the new panel
  (accept/accept, reject/reject on every bound); the schema-version parity
  contract includes `gallery`.
