# Gallery stage transform (per-card scale and offset) — design

Date: 2026-10-03
Status: approved by the user section by section
Change home: OpenSpec proposal to be authored from this document.

## 1. Problem

Stable Diffusion is instructed to fill the whole canvas with the subject, so
a generated child stands as tall on the stage as a generated adult: the
canvas-filling proportion is correct per image, wrong between images. Players
need a manual, per-portrait correction of how one card's figure is presented
on the cinematic stage — for example a child card scaled to 0.6 — plus a way
to slide the figure when the character is not centered in the source image.

## 2. Decision summary

| # | Decision |
|---|---|
| D1 | One persisted presentation triple per gallery card: `stage = {scale, x, y}`. Card-level (like `face_rect`), not subject-level, no override layering. |
| D2 | It is pure presentation. It never enters combat, resolution, appraisal, or any rules path. Server-side it is stored, validated, and delivered; only the browser interprets it. |
| D3 | It affects full-figure renderings only: the cinematic stage (`StageActor`/`ReferenceArtwork` stage mode) and the drawer art slot (which moves onto the stage render path). Every `object-fit: cover` avatar crop driven by `faceObjectPosition` — gallery cards, roster, party strip — is untouched. |
| D4 | One atomic action `gallery.stage.update` submits all three values; the editor is a dedicated modal mirroring the face-rect modal's interaction contract. Live preview is local-only; no per-tick server traffic. |
| D5 | The preview shows the current card transformed live against a static adult reference: `web/static/art/defaults/man.webp` rendered as a flat-color silhouette via CSS mask, anchored at scale 1.0 and offset left by half its own displayed width. |
| D6 | Bounds: `scale ∈ [0.2, 2.0]`; `x, y ∈ [-0.5, 0.5]` as fractions of the displayed frame's width/height. Slider + number box per value; dragging the figure in the preview edits x/y directly. |
| D7 | No migration and no compatibility layer: pre-existing stored cards simply lack the `stage` key and the tolerant read supplies the identity default `{scale: 1.0, x: 0.0, y: 0.0}` (the repository has no released users). |

## 3. Data contract (`world/art/gallery.py`)

The stored card contract grows from eleven keys to twelve:

```python
"stage": {"scale": 1.0, "x": 0.0, "y": 0.0}
```

- `validate_stage(value)`, new, follows `validate_face_rect`'s style: exact
  three-key mapping; every value a real finite number (bool rejected);
  `0.2 <= scale <= 2.0`, `-0.5 <= x <= 0.5`, `-0.5 <= y <= 0.5`; anything
  else raises `GalleryRecordError`. Returns a freshly built plain dict.
- `validate_card`: `api_defaults=True` (the write boundary) may omit `stage`
  and fills the identity default; `api_defaults=False` (reads) requires the
  complete twelve-key contract. The triple is stored atomically — consumers
  never patch one coordinate in isolation.
- Tolerant read (`_consolidate` path): a stored card without `stage` yields
  the identity default; a malformed stored `stage` is treated like a missing
  one. No data migration.
- New write seam `set_stage(subject, image_id, stage) -> dict`: validates
  through `validate_stage`, runs under `gallery_lock`, routes through the
  existing `_update_card_field`, and emits
  `log_info("gallery_stage_set", context={"subject": ..., "image_id": ..., "scale": ..., "x": ..., "y": ...})`
  per the observability catalog. All validation precedes persistence.

### Action seam (`web/webclient/actions/gallery_actions.py`)

- `validate_gallery_stage_update_payload(payload)`: exact keys
  `{subject_key, image_id, stage}`; subject-key and UUID grammar through the
  shared `_payload`; bounds owned by the art API — the dispatcher runs
  `gallery_api.validate_stage` for early syntax-shaped rejection exactly as
  the face-rect validator does, and acceptance never rewrites values.
- `_mutate` gains the `gallery.stage.update` branch calling
  `gallery_api.set_stage(subject, image_id, payload["stage"])`; success code,
  localized message, `affected_panels = AFFECTED_GALLERY_PANELS`, and the
  `gallery_action` info/warn event all follow the existing branches. A new
  `REJECTION_MESSAGES` entry covers stage rejection.

## 4. Wire contracts

### Gallery panel (`web/webclient/presentation/gallery.py`)

- `CARD_FIELDS` gains `stage`.
- `validate_gallery`: a `status == "card"` row's `stage` is validated with
  `gallery_api.validate_stage`; synthetic rows (`pending`/`failed`) must
  carry `stage: null` — the same "synthetic rows fabricate nothing" rule
  `face_rect` already enforces. No new chips: the triple is not a
  player-filterable fact, so the exactly-one-face-chip invariant is
  unchanged and the panel `schema_version` does not change (additive
  exact-field set; both endpoints land in one deployable).

### Portrait payloads (`world/art/presenter.py`)

Every `resolve_subject` payload already carries `face_rect`; it gains
`stage` with the same degradation contract, so payload construction never
fails on a stored value:

- `_card_payload`: the card's validated `stage`; a stored value failing
  `validate_stage` degrades to the identity default with one bounded
  `log_warn("art_stage_invalid", context={"subject": ...})`.
- Classic done-record branch and fallback branch: identity default.
- Placeholder branches: `stage: None`.
- Scene payloads share the shape and carry the default; the scene renderer
  never reads it (mirror of `face_rect`).

### Stage/actor consumption

- The `art` panel portrait-catalog entries and the stage/dialogue actor
  portrait entries gain the `stage` field (they already thread `face_rect`
  to the browser).
- All three exact-field validators move in lockstep: Python
  `web/webclient/presentation/art.py`, the dependency-free Node validator
  `web/static/webclient/js/elosern/protocol/panels/art.js`
  (`requireExactFields`), and the dialogue/stage presenter that feeds
  `StageActor`. A missed validator is a hard snapshot-validation failure —
  this is a mandatory checklist item, not an option.

## 5. Frontend rendering (`ReferenceArtwork.vue`)

Only this component changes rendering, and the two modes stay separate.

### Stage mode (`object-fit: contain`, `object-position: center bottom`)

The `<img>` receives:

```css
transform: translate(calc(var(--stage-x) * 100%), calc(var(--stage-y) * 100%))
           scale(var(--stage-scale));
transform-origin: 50% 100%;
```

- The transform origin anchors the displayed image's bottom-center: contain
  plus bottom alignment puts the feet on the frame floor, so scaling keeps
  the figure standing on the same ground line at any scale.
- `--stage-x`/`--stage-y` are frame-width/frame-height fractions; they
  compose after `scale` in the transform list, so offsets mean the same
  thing regardless of scale. Positive y moves down, negative up; a figure
  cropped at the head is pushed up with negative y. Default `0`.
- The `__ground` ellipse stays put — it marks the anchor, not the figure.
  The drop-shadow rides the transform (it scales with the figure), which is
  the intended look.
- The stage wrapper already has `overflow: visible`; a scaled figure may
  lean outside its box and is not newly clipped.
- `null`/missing `stage` normalizes in-component to `{1.0, 0, 0}` as
  defense-in-depth even though the wire guarantees the shape.
- No animation: a scale change applies as a plain style update; `portraitKey`
  does not include `stage`, so adjusting it never retriggers the crossfade.

### Drawer art slot

The drawer's `ReferenceArtwork` usage switches to the stage branch (it is a
full-figure surface). The true framed-avatar semantics — the non-stage cover
branch driven by `faceObjectPosition` — is untouched everywhere (gallery
cards, roster, party strip).

### Placeholder

The stage placeholder's inline SVG human silhouette stays exactly as it is.
It is not the preview reference (see §6) and shares no code with it.

## 6. Preview modal (`GalleryStageTransformModal.vue`)

New component, structurally symmetric to `GalleryFaceRectModal.vue`: scrim,
`role="dialog"` `aria-modal`, focus trap with opener restore, Escape close,
`@submit` once on save, `@log` escape hatch, `disabled`/`rejected` props.

### Left: live preview stage

- One fixed 3:4 preview frame simulating the stage box, stage-dark
  background.
- Adult reference: a static element painted purely in CSS —
  `mask-image: url("/art/defaults/man.webp")` (plus `-webkit-` prefix),
  `mask-size: contain`, `mask-position: bottom center`,
  `mask-repeat: no-repeat`, `background: #17191f` (the existing placeholder
  fill) — contain keeps the silhouette's own 9:16 proportions inside the
  3:4 frame. `man.webp` carries a real alpha channel (verified: extrema
  0–255) and is one of the six committed fallback keys already served by
  the `/art/` route, so no new asset and no new route. The reference sits
  at scale 1.0, statically translated left by 50% of its own displayed
  width (about 37.5% of the frame width under contain) via its own
  element transform — independent of the card's editable triple — with no
  stroke, no ground ellipse, no chest text, `aria-hidden`. It never moves
  with the controls. Both layers share the contain-plus-bottom-anchor
  math, so the feet lines coincide and a canvas-filling adult and a
  canvas-filling child are directly comparable.
- Current card: the same `card.url`, rendered with §5's transform bound to
  a local `ref`. Every slider `input` / pointer `move` only mutates the
  ref — CSS-variable updates, zero network traffic.
- Drag-to-offset: `pointerdown` → `pointermove` on the preview frame maps
  pointer deltas to frame-fraction x/y, clamped to ±0.5, with
  `touch-action: none` and pointer capture. Pure helpers live in
  `stage-transform-edit.js` (same style/testability as
  `face-rect-edit.js`): `clampStage`, `moveStage`, `editStageField`.
- Image load failure degrades the preview to the silhouette plus an honest
  error line and disables save — the face modal's `loaded` contract.

### Right: numeric controls

- Three paired `range` + `number` controls: 比例 0.2–2.0 step 0.01,
  水平 −0.5–0.5 step 0.01, 垂直 −0.5–0.5 step 0.01, kept in two-way sync
  with clamping.
- 重設 button sets the local triple to the identity default; saving is
  still required.
- One explanatory line: affects stage and full-figure presentation only,
  never the avatar crop; only numbers are stored, no new image is produced.

### Save flow

- 儲存調整 → `emit("submit", { stage: {...} })` →
  `GalleryPanel.send('gallery.stage.update', $event)`; the existing
  pending/rejected/revision contract is reused unchanged (close only after
  the presentation revision arrives; rejection keeps the local values plus
  the log link).
- `GalleryDetailRail` gains a 比例調整 control emitting `stage`;
  `GalleryPanel` wires `@stage="openEditor('stage')"`. The existing
  `send` guard already refuses non-`card` rows.

## 7. Error handling

- Out-of-bounds or malformed payloads are rejected at every boundary
  (action validator, `validate_stage`, wire validator) before any write;
  stored-but-malformed values can never be produced because the triple is
  written atomically, and any that appear (hand-edited DB) degrade to the
  identity default at read/present time with one bounded log line — never
  a failed snapshot.
- The action follows the standard gallery rejection ladder: unknown card,
  unresolvable subject, and record errors map through `_error_code` to
  localized rejections; nothing partial is ever persisted.
- Offline/placeholder states are unaffected: `stage` rides only on asset
  payloads; placeholders carry `null` and render as today.

## 8. Testing

- Pure Python (`world/art/tests/test_gallery/`): `validate_stage` bounds and
  type hostility (bool, NaN, inf, extra/missing keys); `validate_card`
  twelve-key enforcement and `api_defaults` fill; `set_stage` success,
  unknown-card, and atomic replacement; tolerant-read default.
- Presenter: card stage passthrough, stored-malformed degradation with the
  log event, classic/fallback defaults, placeholder `None`.
- Wire: `test_gallery_panel` rows with `stage`, synthetic-row `null`,
  rejection of out-of-range values; art-panel and Node protocol validator
  updated in the same change (`node --test` file green).
- Vitest: `stage-transform-edit.js` pure math (clamp, drag mapping, field
  edit); modal component (slider↔number sync, drag→offset, submit payload,
  save-disabled before load); `ReferenceArtwork` stage-mode transform
  style including custom-property values and normalization of `null`.
- Traceability: a new main-spec requirement in the owning gallery
  capability (stage-transform contract) with `covers_requirement` anchors
  on the substantive tests; `tools.spec_traceability check` green; any new
  Python test module registered in `.github/evennia-shards.json` in the
  same change; `tools.contract_gate` before handoff.

## 9. Out of scope

- Automatic proportion inference (age/body-size detection) — manual only.
- Per-subject defaults or inheritance; per-card values stand alone.
- Any effect on avatar crops, `face_rect`, SD prompts, or stored images.
- New player commands (the surface stays the existing gallery panel), so
  `docs/game/commands.md` is untouched.
- Animating scale changes or ground-shadow adaptation.
