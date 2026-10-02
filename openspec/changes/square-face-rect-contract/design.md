# Design: square-face-rect-contract

## Context

The gallery design (2026-09-08, `docs/superpowers/specs/2026-09-08-character-gallery-art-design.md`,
§1/D9/§6/§3.1) states the *goal* is square avatar crops but never constrains the stored rectangle:
`face_rect` is any normalized rect in the unit square with positive `w`/`h`, and
`validate_face_rect` enforces exactly that. The Vue modal (`GalleryFaceRectModal.vue` +
`face-rect-edit.js`) resizes freely (`resizeFaceRect` moves `w` and `h` independently) and its
「方形裁切預覽（1:1）」 in fact preserves the raw rect's aspect. Nothing is square except the label.

### The geometry question (resolved here, evidence-backed)

Normalized `w`/`h` are fractions of image *width* and *height*, so the box is pixel-square only
when `w × imgW == h × imgH`. Can the server check that?

- **Gallery card images are NOT square.** Portraits render on the SD canvas
  `ART_SD_PORTRAIT_WIDTH/HEIGHT` = **768×1024 (3:4)** by default (`server/conf/settings.py`,
  `world/art/sd_worker.py::build_request`), both env-overridable; the cutout and
  `formats.encode` stages preserve the decoded size. The committed fallback images are
  **864×1536 (9:16)**. So normalized `w == h` is the *wrong* server rule: it would demand a
  3:4-shaped marked box on a 3:4 image, and it is inexpressible for the fallbacks at all.
- The card currently stores no image facts (D4: environment-driven generation parameters are not
  stored). A pixel-square check therefore needs a stored reference: option (b) below. Option (a)
  — "make images square by configuration" — is rejected: it fights the SDXL-friendly 3:4 canvas,
  would re-render every committed asset, and mis-crops the fallbacks.

## Goals / Non-Goals

**Goals:** the marked box is pixel-square end to end — modal drag/resize/numeric inputs, initial
fit, preview, stored value, server validation; one shared validator; **no automatic or explicit
write path admits a non-square rect**; no rect adjustment ever (reject, never fix).
**Non-Goals:** no cropping or second image; no face detection; no change to the 3:4 render canvas
or `ART_SD_*` settings; no migration of existing stored rects/cards (pre-release: they fail the
tolerant read or get overwritten on the next explicit save, per repo no-backcompat rule).

## Decisions

### D1 — `image_size` joins the card contract (11 keys), recorded from verified bytes

Each card gains `image_size: {"width": int > 0, "height": int > 0}` — a *fact of the stored
image*, distinct from the D4-prohibited *requested* dimension settings. Provenance rule:
**the dimensions actually decoded from the image bytes, never the request parameters.**
- `generated` settle: `GeneratedImage.width/height` are filled from `request["width"]/["height"]`
  (`sd_worker.py`) and are NOT guaranteed to equal the returned PNG's pixels — they are not
  trusted. `sd_worker._decode_image` already reads the IHDR `width, height` for the resource caps;
  return them, and the worker carries the decoded size through cutout/encode (both preserve
  dimensions) to `world/art/queue.py::settle_gallery_generated`, which passes it to
  `append_card`. (Worker→queue plumbing is part of this change; the settle signature gains the
  size.) A future request-vs-returned mismatch is caught by a decode-and-compare guard in
  `settle_gallery_generated` that refuses the append with the existing bounded failure path.
- `seed` append (`world/art/gallery_seed.py`): Pillow-decode the copied bytes (already a
  dependency via `formats.py`; startup path, capped sizes) and record the decoded size per file.
- Player traffic never carries it: exact-key payload validators reject extra keys.

`validate_card` requires the key on reads (11-key stored contract); appends fill it only from the
trusted value their caller supplies — an append with no trusted size raises the typed error and
persists nothing.

### D2 — `validate_face_rect(rect, image_size=None)` gains the square rule, with NO exemption

Signature: `validate_face_rect(rect, image_size: Mapping | None = None)`. With `image_size`
present, after the existing bounds checks, the rect must be pixel-square:
`abs(w × width − h × height) <= 1.0` (one pixel; float/JSON round-trip noise on a constructed
square is ~1e-13 px, a visible 1% slip is ~7 px). **There is no value-equality exemption for any
rect**, including one field-for-field equal to `DEFAULT_FACE_RECT`: a replayed legacy default on a
non-square card is a non-square marked box and is rejected like any other. Without `image_size`
(card-less presentation fills — classic assets, fallback-map gaps) the function keeps today's
bounds-only behavior, because there is no box *on an image* to square: those are composition
anchors, not marks.

Why 1 px and not exact fractions: the modal's exact square for `w=0.4` on 768×1024 is
`h=0.29999999…`; exact-fraction equality across JSON is float-hostile, and ≤1 px disagreement is
unobservable by construction.

### D3 — The card default rectangle becomes `default_face_rect(image_size)`, image-fitted

A card written without an explicit rect is filled — at append, once `image_size` is established —
with `default_face_rect(image_size)`: keep the pinned anchor's width fraction and upper-half
placement, derive the height fraction so the box is exactly square:
`{"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5 × width / height}` — on 768×1024 that is
`{x: 0.25, y: 0.06, w: 0.5, h: 0.375}` = **384×384 px**; on a square image it equals
`DEFAULT_FACE_RECT` exactly. Consequences, all in-delta:
- `DEFAULT_FACE_RECT` stays pinned byte-for-byte (`{"x":0.25,"y":0.06,"w":0.5,"h":0.5}`) and keeps
  its remaining roles: the card-less presentation anchor (classic assets, `validate_face_rect`
  with no size, fallback-map key gap) — never as a stored card rect on a non-square image.
- Automatic generation stops passing the constant explicitly: `service._gallery_autogen_request`
  sends `face_rect=None`, and the card takes the fitted default at append (the autogen spec's
  "shared default face rectangle" wording is amended to "the shared default rectangle fitted to
  the image").
- The 預設臉框/自訂臉框 chip can no longer be re-derived from the literal constant by anyone who
  lacks the card's size: the server computes it against `default_face_rect(card["image_size"])`;
  the presentation wire validator and the mirrored legacy validator in
  `web/static/webclient/js/elosern/protocol/panels/art.js` accept **either** face chip without
  re-deriving it from the rect (the rows keep their exact key sets — no `image_size` goes on the
  wire; the server stays the sole chip author). The legacy `validateGalleryFaceRect` helper keeps
  its bounds-only mirror (the read path never square-checks; squareness is a *write* contract).
- `update_card_face_rect(subject, image_id, DEFAULT_FACE_RECT)` on a non-square card now raises
  the typed square rejection — an existing test that submits the constant as an update value is
  re-aimed at a square rect.

### D4 — Update and request boundaries check against the right size

- `update_card_face_rect` validates `validate_face_rect(rect, card["image_size"])`; a malformed
  stored `image_size` fails the tolerant card read ⇒ the update raises the existing
  `remove_card`-miss typed error (never guess a size). The webclient action validator stays
  shape/bounds-only (the payload admits no size); the typed square rejection surfaces through
  `_mutate` as the bounded `gallery_rejected` presentation, card unchanged.
- `request_gallery_image(face_rect=...)`: before enqueue, validate with
  `validate_face_rect(face_rect, planned_image_size)` where `planned_image_size` is the subject
  kind's configured render size (portrait: `ART_SD_PORTRAIT_WIDTH/HEIGHT`), so a non-square
  request never writes a queue record (`art-gallery-generation` scenario). At settle, the
  authoritative check re-runs against the *decoded* size via `append_card`; if the SD server
  returned a different size than planned, the append rejects and the job settles failed with the
  bounded worker error — honest, and vanishingly rare (the caps in `_decode_image` bound drift).
- The presentation read path (`web/webclient/presentation/gallery.py`) validates outgoing rects
  bounds-only (it projects rows, which carry no size — see wire delta); a non-square stored rect
  can only exist from a pre-change DB and is skipped by the tolerant read (`image_size` missing ⇒
  card invalid ⇒ row omitted). The presenter validates a resolved card's rect against its
  `image_size` and degrades the malformed case to `default_face_rect(image_size)` (resolution
  delta). So "every rect that reaches a client is square on its image" holds by construction of
  the write contract, not by a read-side re-check.

### D5 — Seed manifests preflight the shared rect against the subject's actual images

The manifest `face_rect` is one shared rect applied to *all* of a subject's seed images, whose
sizes can differ. Before honoring either manifest field, `_parse_manifest` gains a preflight: it
receives the eligible files' decoded sizes (the sync already has the files open at the folder-fd
stage; Pillow-decode each eligible image — same startup path as D1) and requires the declared
rect to be pixel-square for **every** eligible image (missing/undecodable size ⇒ degrade). On any
violation: the existing `manifest_invalid_face_rect` diagnostic and whole-manifest degrade
(sorted-name default, per-card fitted defaults from each file's own decoded size). A manifest
rect may be legitimately `w ≠ h` (square on 768×1024 but not 864×1536) — mixed-size subject
folders therefore degrade, which is correct: no single shared rect is square on two different
aspects. In-repo test fixtures that currently carry valid sizes get square manifest rects or move
to the degrade path intentionally (task-listed audit).

### D6 — Frontend geometry: `face-rect-edit.js` becomes image-aware

Pure helpers take the natural size `{width, height}` (fallback `null` = unknown, see modal gating):
- `defaultFaceRect(dims)`: mirror of D3's `default_face_rect` — with unknown dims it returns the
  pinned anchor `{x:0.25,y:0.06,w:0.5,h:0.5}` (visibly square *on screen* only once the box is
  drawn over a square-ish placeholder; see gating on save);
- `squareFromWidth(rect, dims)` / used by: `resizeFaceRect(rect, dx, dy, dims)` — the ↘ handle
  drags the width axis; height is re-derived `h = w × width / height`; clamp the square inside the
  unit square via `w ≤ min(1 − x, (1 − y) × height / width)` and the `MIN_AREA_EDGE` floor;
- `editFaceRectField(rect, field, value, dims)`: numeric 寬度/高度 edits re-derive the partner
  field; x/y edits move only;
- `clampFaceRect(rect, dims)`: submit gate — with dims known, shrink the longer axis to square
  then bounds-clamp; **with dims unknown the modal does not submit at all (below), so this gate
  never invents a 1×1 aspect**;
- `moveFaceRect` unchanged; `faceCropStyle` unchanged.

Modal: the trusted geometry size is `naturalWidth/naturalHeight` once loaded, and **null before
load or after `@error`**. While null: the box renders the pinned anchor, numeric editing is
allowed (positions/sizes as fractions), but **儲存框選 is disabled** with a truthful zh-TW hint
(圖片尚未載入，無法儲存框選) — the client never dispatches geometry squared against a guessed
aspect. On load, the current box is re-derived: its center and height span are preserved, the
width is re-squared against the real aspect, clamped inside the image (a "never shrink the
player's edits" promise is dropped — reinterpretation onto a real aspect near an edge can require
a shrink; the clamp is the honest behavior). `previewStyle` becomes trivially square; the
「完整呈現框選範圍，保留原始比例。」 note is replaced with truthful square-crop guidance;
`rectStyle` unchanged.

### D7 — `FALLBACK_FACE_RECTS` re-authored to squares (computed, head-preserving)

Method: keep each key's head vertical span `h` (head-height framing is the authored intent),
square side = `round(h × 1536)` px, grow the width fraction symmetrically about the current
center (the images have transparent backgrounds, so widening crops no figure pixels — worst case
8 px of transparency on `man`). Final map (4-decimal, ≤0.05 px square error; the new contract
test decodes each committed `.webp` and asserts `|w·W − h·H| ≤ 1` per file):

```python
"man":          {"x": 0.3576, "y": 0.02, "w": 0.2847, "h": 0.16},
"woman":        {"x": 0.3576, "y": 0.03, "w": 0.2847, "h": 0.16},
"boy":          {"x": 0.3490, "y": 0.03, "w": 0.3021, "h": 0.17},
"girl":         {"x": 0.3576, "y": 0.02, "w": 0.2847, "h": 0.16},
"elder":        {"x": 0.3576, "y": 0.03, "w": 0.2847, "h": 0.16},
"monster_anon": {"x": 0.3403, "y": 0.02, "w": 0.3194, "h": 0.18},
```

### D8 — Design-doc amendment (this change edits the source of truth)

`docs/superpowers/specs/2026-09-08-character-gallery-art-design.md`:
- §3.1 card table: amend the `face_rect` row (pixel-square on the card's `image_size`), add the
  `image_size` row; the ten-key wording becomes eleven.
- §6 bullets: pixel-square rule, fitted-default fill rule, trusted-provenance recording rule.
- D9 line in §2: addendum marker.
- New `## 13. Addendum (2026-10-03): square face rectangles` in the §12 addendum style: D9's
  square-crop goal becomes a contract; why normalized `w == h` is wrong on the 3:4 canvas; the
  decoded-bytes provenance rule; the fitted default replaces the constant for cards; the constant
  survives as the card-less presentation anchor.

## Risks / Trade-offs

- **Stored 10-key cards / non-square stored rects.** Pre-release rule: cards without `image_size`
  fail the strict read and are skipped by the tolerant read (`gallery_card_invalid`, logged); the
  files are re-appendable via seed sync/generation; deleting affected gallery records is the
  documented pre-release remedy. Accepted per AGENTS.md (no compat readers).
- **Requested-vs-returned SD size drift**: `image_size` records the decoded truth, so the card is
  never a lie; the settle guard converts a drift that also breaks the queued rect into the
  existing bounded failed settle (no card), not a corrupt one.
- **Tolerance `≤ 1 px`**: generous for float/JSON, ~100× tighter than visible distortion, cannot
  smuggle a bounds violation.
- **Chip-relaxation window**: the legacy art.js mirror accepts either face chip, so it can no
  longer catch a server that mislabels the chip. The server has one chip author with a unit test;
  the mirror's exactness was never a security property. Accepted.
- **`DEFAULT_FACE_RECT` keeps a non-square life on card-less assets** (classic assets render at
  unknown size to the presenter): deliberate — it is an `object-position` anchor, not a marked
  box, and it is main-spec-pinned. Every *card* rect is square unconditionally.

## Migration Plan

Single cutover: validator + 11-key card contract + fitted default + chip coherence + UI ship
together; no flags, no compat readers, no data migration (tolerant skip per above). Rollback =
revert the commit (11-key cards then fail the tolerant read — same asymmetry as every prior
card-contract change).

## Open Questions

None blocking. Fallback y-anchors may get a ≤0.01 visual nudge during implementation without
touching the squareness math.
