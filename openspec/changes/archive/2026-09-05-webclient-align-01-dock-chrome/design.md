# Design: webclient-align-01-dock-chrome

## Context

The stage's dock anchor is full-width; inside it `ActionDock.vue` carries both the visual
band (gradient `linear-gradient(0deg,#0c0a0e,#141019 70%,var(--panel))`, `border-top`,
upward shadow) and the max-width 1180 centered content column. Verified in the live
container at 1600×900: the painted band spans only x∈[210,1390]; the anchor's outer gutters
are transparent over the black stage. The draft owns these chrome properties on
`.dockwrap{left:0;right:0}` and centers `.dock{max-width:1180px;margin:0 auto}`.

The legend currently renders `方向鍵選擇・Enter 確認・Esc 返回・/ 聚焦指令列` as plain text
with a visually-hidden duplicate for the test hook. The draft renders
`數字鍵 1–4 · <kbd>Enter</kbd> 執行 · <kbd>Esc</kbd> 返回` with styled `<kbd>` elements.
All three named affordances are implemented (1–4 pick dock/suggestion cards, Enter activates
the focused row, Esc pops one frame). `/` focuses the command line but the draft's legend
does not advertise it.

## Goals / Non-Goals

**Goals:**
- Band chrome paints full-width; gutters can never go black at any viewport width.
- Legend matches the draft's text and `<kbd>` structure, one visible instance, truthful.
- Utility buttons visually match draft `.hist button`.

**Non-Goals:**
- No change to the router, focus model, `--dock-h` sizing, row-region scrolling, breadcrumb,
  or the `/` binding itself.
- No change to chip content (owned by change 02) and no narrative-feed work (change 03).

## Decisions

- **Where the band lives:** add the band classes to the existing full-width stage anchor
  wrapper element (or a dedicated `.dock-band` wrapper inside it) and strip gradient,
  border, shadow, and horizontal padding from the centered container, which keeps only
  `max-width:1180px;margin:0 auto` and vertical layout. Alternative considered: a fixed
  viewport-width pseudo-element on the dock — rejected, it decouples the band from the
  anchor's `--dock-h` and complicates the recessed/dimming marks.
- **Legend content per mode:** keep the single legend slot; render the draft's exact
  explore/combat string now. The dialogue variant (`數字鍵 1–4 選 · <kbd>→</kbd> 指令列自由對話`)
  arrives with the dialogue mode (change 08) — this change ships only modes that exist.
- **kbd styling:** copy the draft rule verbatim onto `kbd` inside the legend class.
- **Test hook:** the `data-testid` shortcut-legend hook stays on the visible element; the
  visually-hidden duplicate is deleted, simplifying the one-instance contract to
  "exactly one element".

## Risks / Trade-offs

- Geometry tests measure the painted band → any test asserting the gradient on the inner
  container must move to the band wrapper; enumerated in tasks.
- The legend rewrite drops `/ 聚焦指令列`; a discoverability concern only — the key works,
  and the command-reference docs already list it.
