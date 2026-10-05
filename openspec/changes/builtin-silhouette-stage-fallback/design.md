## Context

See proposal.md for motivation. The selection rule (`fallback_key_for`), the six committed images, the `/art/defaults/` route, and the per-key rectangle map already exist and are contract-locked (`art-gallery-fallback`). The stage placeholder today is an inline stretched SVG in `ReferenceArtwork.vue` (`.reference-artwork__silhouette`), with pending shimmer gated on reduced motion. The source design is §9. This change is independent of the official artwork mount.

## Goals / Non-Goals

**Goals:**
- Truthful state + dignified figure: silhouette is presentation data for a still-absent portrait.
- One selection rule in Python; the browser renders whatever identity the server resolved.

**Non-Goals:**
- No new or converted image files; no `/art/defaults/` route change; no selection-rule change (bands, hash, declarations stay); no change to compact/cover placeholders; no official artwork dependency.

## Decisions

- **CSS `mask-image` with `mask-mode: alpha` semantics against the existing `/art/defaults/<key>.<ext>` URL**, filled with the current dark fill color, instead of server-side silhouette pre-rendering or a canvas pipeline: the committed images already carry contract-tested alpha (transparent backdrop, opaque figure), the browser keeps one resource, and no second derivative file set is created. Alternatives rejected: pre-generated SVG paths from the bitmaps (duplicate assets to maintain), and canvas masking (unnecessary JS in the render path).
- **Payload: carry `fallback` key + identity as distinct fields beside the true status**, rather than flipping the existing fallback branch to a fake `missing` payload: the current payload shape (URL present, status passthrough) is already close; only the `done`-labeling in the fallback branch changes, keeping the wire change minimal and the design's "never return DONE" rule testable in one place.
- **Stage-only upgrade**: gallery rail, cover-mode avatars, and roster thumbnails keep their existing treatments (design §9: compact views may retain text/glyph placeholders), bounding the blast radius to `ReferenceArtwork.vue` stage mode.
- **Floor alignment via the existing stage box** (center-bottom anchor) with `mask-position: bottom center` + `mask-size: contain`, reusing the contain/bottom convention real images already use so silhouettes and real art share one geometry.
- **Payload shape (reconciled with the delta specs):** the decorative `fallback` field is the ONLY place a resolved silhouette appears — the payload's own `url`, `face_rect`, `stage`, `subject_key`, and `origin` are never filled from it (`art-gallery-fallback`: "only a real payload image carries a media URL of its own"; `webclient-art-panel`: the field "SHALL NOT populate the entry's real media URL, subject key, face rectangle, stage, or origin"). A silhouette-only resolution therefore stays the truthful placeholder row the chain would otherwise return, with `origin: silhouette`; D2's "the current payload shape (URL present, status passthrough) is already close" is realized as "the URL present becomes the decorative field's URL, and the status passthrough becomes total (never `done`)".
- **One event per presented silhouette:** the terminal seam keeps its single resolution and gains a keyword-only `report` flag (default `True`). The presenter reports exactly when the resolved silhouette IS the presented figure (the terminal rung) and stays silent when it only decorates a resolved real image, so the `gallery_fallback_used` scenario ("the chain reaches the seam for a subject with no card and no `done` classic asset → one event is logged") keeps its meaning and a busy stage adds no log noise.
- **The former inline SVG is retained only where no fallback identity is carried** (today's roster portraits, a scene-kind actor) — the `webclient-contextual-hud` clause "when no fallback media identity is carried ... the existing grounded standing-silhouette treatment SHALL apply unchanged". Wherever an identity is carried the alpha mask replaces it, and a failed bundled mask keeps the actor name and the truthful label with no figure standing in.
- **The bundled-mask failure signal:** a CSS `mask-image` resource reports nothing to the DOM, so the mask's own URL also rides one non-painted probe image; its `error` removes the figure (name + label remain) and the fill paints only after that probe loads, so a missing resource can never leave a solid fill rectangle.
- **Roster deferral:** the roster portrait serialiser keeps its exact field set here; the roster wire gains the portrait origin discriminator in `official-art-resolution-contracts`, which this change's decorative `fallback` field already anticipates.

## Risks / Trade-offs

- [Browser mask support edge cases] → masked images are baseline-supported in the project's supported browser set; the bundled-resource-failure path (name + text placeholder, usable surface) is spec'd as the universal fallback.
- [`DONE` removal from the fallback payload touches consumers that branch on status] → the change updates all in-repo consumers atomically; wire validators pin the shape; the load-failure path is spec'd to reuse the carried silhouette without new requests.
- [Elder band ships one shared image, so elder male/female look alike] → accepted by the design's explicit table (one shared elder image in the current set); the mask simply renders what is committed.

## Migration Plan

None needed: files, route, and stored data are untouched; deploy = new payload field + component change shipped together (server and client ship together per existing contract).

## Open Questions

None.
