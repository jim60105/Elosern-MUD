## D1 — Committed v1 facts only

The `gallery` panel is the sole live read model. Card labels, chips, filter
counts, equipment display names and warning conditions are rendered verbatim.
The client does not recompute rule matches, equipment identity, counts or
resolved portrait selection. Static headings, filter labels and the closed
field/slot vocabulary are presentation chrome. `created_at` formats as UTC.
Failed labels remain intact, including any code included by the server.

The v1 payload has no original pixel dimensions, full stored binding mask or
snapshot, or resolved-current-image flag. Omit dimensions. Display condition
lines only from an explicit matching `binding_warnings` record; otherwise mark
them unavailable. The default marker makes no claim about the currently
resolved image. Capability booleans independently gate binding, prompt fields
and free text; `max_cards === 1` supplies the replacement explanation.

## D2 — Bounded local view and intent state

`GalleryPanel` owns the local filter, grid/list toggle, highlighted image ID,
active editor, unsaved form drafts and correlation with its admitted request.
Rows retain their published order. Subjects are selected through
`gallery.subject.select`; the highlighted subject and rows change only on
publication. Filters use only published status/boolean fields, never binding
resolution logic.

Subject replacement, unavailable data and loss of an edited image discard
stale editors. A same-subject snapshot does not clear drafts. An initially
empty gallery receiving an unrelated pending row does not close generation.
Transport/epoch teardown unmounts the existing overlay through the store.

## D3 — Five components and existing host integration

- `GalleryPanel`: heading, subject rail, five filters, grid/list cards, local
  selection and action coordination. Cards use `faceObjectPosition` for the
  shared thumbnail anchoring convention; pending/failed rows have no image URL.
- `GalleryDetailRail`: selected portrait, default and binding facts, explicit
  conditions, generation/default/edit/face actions and inline delete confirmation.
- `GalleryGenerateDrawer`: right-side `HudDrawer`, optional reference portrait,
  five field choices, equipment summary, raw prompt and counter. The reference
  portrait is the selected gallery image, not a claim about current resolution.
- `GalleryBindingDrawer`: right-side `HudDrawer`, selected portrait, checkbox-only
  slot mask, current equipment facts and explicit warning rows with selection jumps.
- `GalleryFaceRectModal`: bounded two-column dialog using `createFocusTrap`,
  original image with drag/resize box, numeric controls, square preview and save.

Register `gallery` in the existing store overlay allowlist and mount the family
inside `OverlayHost`. An availability-gated button beside the existing portrait
opens it. The gallery-specific host layout leaves the status column and command
line visible. The integrated heading avoids duplicate host chrome.

## D4 — Exact actions and settlement

Every live action calls the existing `store.dispatchAction` entry through
`AppClient`; there is no alternate dispatcher or backend/protocol change:

- `gallery.subject.select`: `subject_key`.
- `gallery.generate`: `subject_key`, `fields`, raw `custom_prompt`.
- `gallery.default.set` and `gallery.card.delete`: `subject_key`, `image_id`.
- `gallery.binding.save`: `subject_key`, `image_id`, `slots`.
- `gallery.face_rect.update`: `subject_key`, `image_id`, `face_rect`.

The existing connection/mutation/in-flight gate controls all actions. Null
admission never arms a request. A submitted editor closes only after its own
successful result and declared presentation revision have committed; unrelated
results or pending rows do not settle it. Rejection preserves the draft.
The store appends the server message once; the editor adds only a generic
recovery hint and a control opening the existing full log above the editor.

## D5 — Generation and binding drafts

Generation exposes only supported controls. The optional text is never
truncated, trimmed, interpreted or assigned HTML `maxlength`; its counter counts
Unicode code points. The server validates the 512-code-point limit. A monster
with disabled field selection and free text submits `fields: []` and
`custom_prompt: ""`. Only the puppet gallery links to the puppet status drawer;
that link invokes the existing atomic overlay-to-drawer transition.

Binding starts unchecked because v1 does not expose the stored mask. At least
one slot must be selected. Saving captures current server equipment; the UI has
no item picker and computes no overlap/matching results. Empty current equipment
is a valid selected slot. The four catalog IDs are `weapon_main`, `weapon_off`,
`armor`, `accessories`. Warning conditions are rendered without reconstruction.

## D6 — Geometry and accessible interaction

The face rectangle remains normalized to the original image. Pointer movement
uses its actual displayed bounds, excluding any letterbox; move and bottom-right
resize clamp to the unit square with positive area. Pointer capture and
cancellation prevent dangling drags. Numeric controls provide keyboard access.
The editor saves coordinates only and never creates a derivative image.

The preview clips the exact selected region using CSS. The output frame is
square; a non-square selection is letterboxed to preserve the original aspect
ratio rather than stretched. Shared thumbnail anchoring remains separate from
this zoomed preview.

Editors teleport outside the outer host and have pointer-blocking scrims and
focus traps. Their keyboard events do not bubble into the host. The outer host
is not made inert because existing synchronous trap restoration precedes a
reactive inert-removal commit. Editor close restores the opener after rendering;
if it disappeared, focus falls back to a remaining gallery control. Escape or
cancel never dispatches. Deletion requires a separate confirmation. Visible
focus and textual status labels avoid color-only meaning; reduced motion stops
the pending spinner animation.

## D7 — Reference composition and storyboard

All four `docs/design/elosern-redesign2/角色肖像圖庫管理頁-*.webp` images were
viewed during design. The composition uses ink-black panels, gold borders and
headings, a central card grid and right detail rail, right-side generation and
binding drawers with portrait/controls columns, and a two-column face dialog.
Backend facts take precedence over illustrative reference copy.

Stories use the existing local fonts/artwork and deterministic synthetic data.
The frozen manifest adds exactly five titles: `Data/GalleryPanel`,
`Data/GalleryDetailRail`, `Overlays/GalleryGenerateDrawer`,
`Overlays/GalleryBindingDrawer`, `Overlays/GalleryFaceRectModal`. Stories and
manifest entries exist before application mounting.

`Data/GalleryPanel/Storyboard` mounts the real family with an explicit offline
publication driver, action inspector and success/rejection controls. It covers
browse, generation, pending/failure, bindings, crop, default and delete flows.
Its synthetic server publications exist only in the story; production code
never simulates them. The story media adapter uses local fallback images and
appropriate example face rectangles instead of nonexistent gallery assets.
`docs/design/elosern-redesign2/gallery-storyboard.md` records frame triggers,
visible facts, recovery paths, references and honest v1 differences.

## D8 — Verification

Focused Vitest component tests cover committed filtering, subject publication,
raw oversized Unicode text, capability gates, warning rendering, deletion,
request/revision correlation, empty-gallery publications, stale-context teardown,
focus restoration and non-square pointer geometry. Application integration uses
the real Pinia store, wire validator and fake transport to exercise availability,
confirmation, global locking, duplicate result/narrative handling and disconnect.

Build the Vite bundle and static Storybook, enforce showcase coverage, validate
the OpenSpec change, and exercise actual Chromium surfaces. Complete Python
coverage and managed browser evidence remain CI-owned. No player commands,
Python modules, persistent backend rules or main specifications change here.
