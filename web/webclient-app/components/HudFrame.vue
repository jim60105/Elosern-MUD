<script setup>
// HudFrame (H1, webclient-hud-01-shell-and-scene; AVG stage shell,
// webclient-avg-stage-shell design D1/D3/D4/D7): the full-bleed cinematic
// stage. A `position:relative; overflow:hidden` root with named anchors:
// - the `place` anchor (webclient-avg-place-card-top-bar design D4): the
//   place card at the stage box's top-left, at the fixed `--place-h`;
// - the island anchors named by their content
//   (webclient-avg-stage-hud-anchors design D1): `vitals` below the place
//   card (the vitals, conditions, and compact party islands) and `map` at
//   the top-right (the minimap, the one-line objective, the combat
//   participant frame, and the title ballot);
// - the portrait anchors `actor-left` (the player's standing portrait) and
//   `actor-right` (reserved), standing on the bottom band's top edge;
// - the bottom band `.stage-band`: one fixed-height (`--band-h`) container
//   split into the message region `band-message` (left 2/3) and the command
//   region `band-command` (right 1/3). No frame, mode, or content resizes it;
// - the `command-line` row, docked on the message region's top edge.
// Mode gating is CSS-only on the `data-elosern-mode` attribute (the single
// source for the committed mode), using `display:none` so hidden surfaces
// leave the accessibility tree and the tab order (REDESIGN.md §0.1:
// 不顯示的絕對隱藏，不是灰掉).
//
// Layers: backdrop 0, vignette 1, combat veil 2, portrait anchors 2 (after
// the veil in DOM order, so the player stays bright in combat), the place
// card and the island anchors 4, band 5, command line 6.
//
// The open-surface registry (design D9): a drawer or full-screen overlay
// marks the stage `menu-open` so the surfaces behind it are visually
// recessed; the mark clears only when no open surface remains.
import { computed } from "vue";

const props = defineProps({
  // The committed mode value rendered on the shell root. The store's reducer
  // modes are "exploration", "combat", and "creation".
  mode: { type: String, default: "exploration" },
  // The open-surface registry for the stage recession (design D9). The set
  // of currently open surface names (e.g. "drawer", "full-log", "creation").
  openSurfaces: { type: Array, default: () => [] },
  // The low-HP flag (design D7): H2 supplies the state from the status
  // payload; H1 ships the CSS hook, defaulting off.
  lowhp: { type: Boolean, default: false },
});

// The open-surface registry drives the `menu-open` mark (design D9): the
// mark clears only when no surface remains open.
const menuOpen = computed(() => props.openSurfaces.length > 0);

defineExpose({ menuOpen });
</script>

<template>
  <div
    class="elosern-stage"
    data-testid="elosern-stage"
    :data-elosern-mode="mode"
    :data-menu-open="menuOpen"
    :data-lowhp="lowhp ? 'true' : 'false'"
  >
    <div class="stage-vignette" data-testid="stage-vignette"></div>
    <div
      class="stage-combat-veil"
      data-testid="stage-combat-veil"
      :data-mode="mode"
    ></div>
    <slot name="backdrop" />
    <!-- The portrait anchors come after the combat veil (same z-index), so
         the standing portraits paint above it (design D1/D4). -->
    <div
      class="stage-anchor stage-actor"
      data-anchor="actor-left"
      data-testid="anchor-actor-left"
    >
      <slot name="actor-left" />
    </div>
    <div
      class="stage-anchor stage-actor"
      data-anchor="actor-right"
      data-testid="anchor-actor-right"
    >
      <slot name="actor-right" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="place"
      data-testid="anchor-place"
    >
      <slot name="place" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="vitals"
      data-testid="anchor-vitals"
    >
      <slot name="vitals" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="map"
      data-testid="anchor-map"
    >
      <slot name="map" />
    </div>
    <div class="stage-band" data-testid="stage-band">
      <div
        class="stage-anchor"
        data-anchor="band-message"
        data-testid="anchor-band-message"
      >
        <slot name="band-message" />
      </div>
      <div
        class="stage-anchor"
        data-anchor="band-command"
        data-testid="anchor-band-command"
      >
        <slot name="band-command" />
      </div>
    </div>
    <div
      class="stage-anchor"
      data-anchor="command-line"
      data-testid="anchor-command-line"
    >
      <slot name="command-line" />
    </div>
  </div>
</template>

<style>
.elosern-stage {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

/* The scene backdrop (the `backdrop` slot content) is the lowest stage
   layer (z-index 0). The vignette and the combat veil sit just above it. */
.elosern-stage .stage-vignette {
  position: absolute;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  border-radius: 2px;
  box-shadow: var(--vignette);
  transition: box-shadow var(--motion-base) var(--ease-standard);
}
.elosern-stage[data-lowhp="true"] .stage-vignette {
  box-shadow: var(--vignette-lowhp);
}

/* The combat pulse (H2 supplies the low-HP and combat state; H1 ships the
   hooks — design D7). */
.elosern-stage[data-elosern-mode="combat"] .stage-combat-veil {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background: var(--stage-combat-veil);
  animation: elosern-combat-pulse var(--motion-pulse) ease-in-out infinite;
}
.elosern-stage:not([data-elosern-mode="combat"]) .stage-combat-veil {
  display: none;
}

/* Named anchors (design D1/D10): absolutely positioned, bounded. */
.elosern-stage .stage-anchor {
  position: absolute;
  box-sizing: border-box;
}

/* place: the place card's anchor at the stage box's top-left corner, one
   fixed height whatever the labels (webclient-avg-place-card-top-bar design
   D4), aligned to the brand column above it. */
.elosern-stage [data-anchor="place"] {
  top: calc(var(--header-h) + var(--stage-inset-y));
  left: 16px;
  width: calc(var(--left-column) - 32px);
  height: var(--place-h);
  z-index: 4;
}

/* vitals / map: the island stacks. Bounded above the bottom band (never the
   band's content) and scrolling internally. vitals begins below the place
   card; map clears only the top bar. The
   `.elosern-root` override in app-shell.css repeats these offsets (it sets
   the column widths); keep the two in step. */
.elosern-stage [data-anchor="vitals"] {
  top: calc(var(--header-h) + var(--stage-inset-y) + var(--place-h) + 12px);
  left: 16px;
  width: 262px;
  z-index: 4;
  display: flex;
  flex-direction: column;
  gap: 9px;
  max-height: calc(100% - var(--header-h) - var(--band-h) - var(--place-h) - 12px - 2 * var(--stage-inset-y));
  overflow-y: auto;
  overflow-x: hidden;
}
.elosern-stage [data-anchor="map"] {
  top: calc(var(--header-h) + var(--stage-inset-y));
  right: 16px;
  width: 230px;
  z-index: 4;
  display: flex;
  flex-direction: column;
  gap: 9px;
  align-items: flex-end;
  max-height: calc(100% - var(--header-h) - var(--band-h) - 2 * var(--stage-inset-y));
  overflow-y: auto;
  overflow-x: hidden;
}

/* The portrait anchors (design D4): standing on the band's top edge,
   `min(62vh, 680px)` tall but never taller than the stage box, inset 6%
   from their own side. Non-interactive art: no pointer events. */
.elosern-stage [data-anchor="actor-left"],
.elosern-stage [data-anchor="actor-right"] {
  bottom: var(--band-h);
  height: min(62vh, 680px, calc(100% - var(--header-h) - var(--band-h)));
  aspect-ratio: 2 / 3;
  z-index: 2;
  pointer-events: none;
}
.elosern-stage [data-anchor="actor-left"] { left: 6%; }
.elosern-stage [data-anchor="actor-right"] { right: 6%; }
.elosern-stage .stage-actor > .reference-artwork { height: 100%; }

/* The bottom band (design D1): one fixed-height container spanning the
   stage bottom. It carries the reference draft's band chrome (the upward
   gradient, the `--line` hairline top border, the upward shadow —
   `docs/design/elosern-redesign/index.html`'s `.dockwrap`) once across both
   regions, so no seam and no stage background ever shows inside it. Its
   height is the `--band-h` token alone. */
.elosern-stage .stage-band {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: var(--band-h);
  z-index: 5;
  box-sizing: border-box;
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  background: linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel));
  border-top: var(--line);
  box-shadow: 0 -14px 34px -24px #000;
}
/* The two band regions are in-flow grid cells (overriding the anchors'
   absolute default): they share the band's top edge and height by
   construction. */
.elosern-stage .stage-band > .stage-anchor {
  position: relative;
  min-width: 0;
  min-height: 0;
  height: 100%;
}
.elosern-stage [data-anchor="band-message"] {
  padding: 10px 12px 12px 18px;
}
.elosern-stage [data-anchor="band-command"] {
  padding: 10px 18px 12px 6px;
}

/* command-line: one row docked on the message region's top edge (design
   D3), from the left island column's edge to the message region's right
   edge. It overlays the lowest strip of the stage box, never the band. */
.elosern-stage [data-anchor="command-line"] {
  left: var(--left-column);
  right: 33.3333%;
  bottom: var(--band-h);
  height: var(--command-line-h);
  z-index: 6;
}

/* Mode-gated visibility (design D2/D7): CSS-only on data-elosern-mode,
   display:none so hidden surfaces leave the a11y tree and tab order. The
   matrix: the place card, the message region, both island anchors (`vitals`
   and `map`, with every island in them), and the command line are hidden in
   creation, where the command region spans the whole band; the minimap is
   hidden in combat; the objective line shows only in exploration; the
   command region and the scene backdrop stay visible in every mode. */
.elosern-stage[data-elosern-mode="creation"] [data-anchor="place"],
.elosern-stage[data-elosern-mode="creation"] [data-anchor="band-message"],
.elosern-stage[data-elosern-mode="creation"] [data-anchor="vitals"],
.elosern-stage[data-elosern-mode="creation"] [data-anchor="map"],
.elosern-stage[data-elosern-mode="creation"] [data-anchor="command-line"] {
  display: none;
}
.elosern-stage[data-elosern-mode="creation"] .stage-band {
  grid-template-columns: minmax(0, 1fr);
}
.elosern-stage[data-elosern-mode="combat"] .local-map {
  display: none !important;
}
/* The objective line (webclient-avg-stage-hud-anchors design D2) is an
   exploration-only surface; it carries no tab stop, so no focus rescue. */
.elosern-stage:not([data-elosern-mode="exploration"]) [data-anchor="map"] .obj {
  display: none;
}

/* The open-surface registry (design D9): when a drawer or overlay is open
   the stage is visually recessed; the mark clears only when nothing is
   open. The transition is token-gated, so prefers-reduced-motion disables
   it at the token level while the recessed state still applies. */
.elosern-stage[data-menu-open="true"] .stage-anchor:not(.stage-band > .stage-anchor),
.elosern-stage[data-menu-open="true"] .stage-band {
  filter: var(--menu-open-filter);
  transition: filter var(--motion-base) var(--ease-standard);
}
</style>
