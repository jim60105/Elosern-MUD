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

## Risks / Trade-offs

- [Browser mask support edge cases] → masked images are baseline-supported in the project's supported browser set; the bundled-resource-failure path (name + text placeholder, usable surface) is spec'd as the universal fallback.
- [`DONE` removal from the fallback payload touches consumers that branch on status] → the change updates all in-repo consumers atomically; wire validators pin the shape; the load-failure path is spec'd to reuse the carried silhouette without new requests.
- [Elder band ships one shared image, so elder male/female look alike] → accepted by the design's explicit table (one shared elder image in the current set); the mask simply renders what is committed.

## Migration Plan

None needed: files, route, and stored data are untouched; deploy = new payload field + component change shipped together (server and client ship together per existing contract).

## Open Questions

None.
