## Context

Part **B4** (showcase wave, Wave B serial chain; depends on B3). The world/services family spans the map,
the art panel, and the `services`-hosted menus. The dominant invariant is truthfulness (art placeholder;
no invented stock/quest/lore/bag).

## Goals / Non-Goals

**Goals** — `LocalMap`, `ArtPanel`, and the `services`-backed panels as documented, offline,
component-tested SFCs; manifest extended.
**Non-Goals** — no full inventory bag, no party/companion panel (both deferred, no backing read model),
no store/transport/mount.

## Decisions

- **D1 — Art degrades truthfully.** The `art` payload renders cover-style 16:9 with the portrait overlay
  when available and a truthful scene placeholder (never an invented image) when missing/pending/failed/
  invalid or the channel is unavailable; label/alt text stays outside the bitmap.
- **D2 — Services are hosts, not data sources.** Shop/quest/lore render only the `services` payload;
  inventory renders only equipped items.

## Risks / Trade-offs

- **Invented stock/quest/lore** → tests assert every entry comes from the mock `services` payload.
- **Art bitmap at 16:9** → cover crop + overlay; no layout overflow at the two supported viewports.

## Migration Plan

Offline/Storybook only; rollback = delete the family + manifest keys. B3 and all gates unaffected.

## Open Questions

- None.
