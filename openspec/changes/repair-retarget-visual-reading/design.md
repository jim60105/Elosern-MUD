## Context

See proposal.md for motivation. The fixed minimap is 240 CSS px at 1451x790. SVG user-unit labels were 16 while the minimap could shrink to 0.75 and the full map could shrink further. The map model already retains complete topology and the full-map controller already supports pan, zoom, focus reveal and recentre. No protocol changes are needed.

## Goals / Non-Goals

**Goals:** enforce the effective text floor, clear upper labels against lower markers, and preserve unchanged-layout message pages through log-held appends.

**Non-Goals:** change prose steps, redesign HUD anchors, add compatibility paths, or mutate gameplay/server state.

## Decisions

1. Keep the declared marker/label geometry and crop rather than shrinking text. The island uses a current-centered 240-unit window. Graph coordinates retain their radial center rather than reusing the lattice's zero-origin clamp. The full map opens at scale 1, centering the current node where it overflows and centering the drawing on smaller axes. Existing pan/zoom/reveal reaches the rest. Smaller labels or per-label counter-transforms were rejected because they violate the floor or invalidate collision geometry.
2. Derive vertical pitch whenever an upper labeled node has a lower marker, including suppressed lower wilderness labels. Reserve two widest marker half-extents, the baseline margin, a label type step and descent allowance, and a positive gap. Apply the maximum horizontal/vertical requirement to both island axes to preserve square bearings. Share the label-baseline constant with rendering.
3. Route initialization, default resize and default payload replacement through the same readable view operation. User-touched views keep their existing center-preservation and moved-current behavior.
4. Await the sliced Jim faces for the effective rendered response or separately published beat-and-tail glyph stream in both weights before synchronous page fitting. Mount-time font readiness alone does not request new CJK slices. A strengthened cold-font actual-game regression reproduced the reader changing from paragraphs 1–5 to 1–4 under an unchanged box. Stable final font metrics preserve the original offset-based reader semantics without freezing stale pages or special-casing the page index. Latest-request arbitration rejects superseded/unmounted preparations; pacing requires a committed response/binding so old pages cannot report a new combat beat or auto-advance during preparation. Regression coverage retains the pre-log baseline instead of resetting it after append. The literal historical 1-to-2 displacement remains distinct from the observed cold-font text displacement.

## Risks / Trade-offs

- A readable window cannot show an arbitrarily large drawing all at once → retain complete model topology, full text alternatives, remembered mirrors and full-map pan/zoom/focus reveal; prove reachability and the minimum effective size.
- Marker and label metrics differ → reserve the shared baseline, descent allowance and widest marker footprint; test upper-label/unlabeled-lower pairs and measure actual loaded-font browser boxes.
- A fit-state lifecycle can drift after resize → test current-centered default refits as well as touched-view retention.

## Migration Plan

Build the authored SPA, update existing consumer tests and current contracts through this delta, and deploy the source build normally. No database migration or stored preference change. Archived retarget artifacts remain unchanged.
