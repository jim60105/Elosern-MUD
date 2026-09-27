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
// - the portrait anchors `actor-left` (the player's stage actor) and
//   `actor-right` (the dialogue host's stage actor while the mode is
//   dialogue), standing on the bottom band's top edge;
// - the `choices` anchor (webclient-dialogue-choices-overlay D6): the
//   dialogue choice list, centred over the stage between the portraits and
//   above the expanded command-line row, rendered only in dialogue mode;
// - the bottom band `.stage-band`: one fixed-height (`--band-h`) container
//   split into the message region `band-message` (left 2/3) and the command
//   region `band-command` (right 1/3). No frame, mode, or content resizes it;
//   creation hides the message region and dialogue collapses the command
//   region, so the other one spans the band;
// - the `command-line` row, docked on the message region's top edge and
//   collapsed by default (`data-expanded="false"` -> `display:none`,
//   webclient-collapsible-command-line design D1/D4).
// Mode gating is CSS-only on the `data-elosern-mode` attribute (the single
// source for the committed mode), using `display:none` so hidden surfaces
// leave the accessibility tree and the tab order (REDESIGN.md §0.1:
// 不顯示的絕對隱藏，不是灰掉).
//
// Layers: backdrop 0, vignette 1, combat veil 2, portrait anchors 2 (after
// the veil in DOM order, so the player stays bright in combat), the combat
// flash 3, the place card, the island anchors, and the choices anchor 4,
// band 5, command line 6.
//
// Mode transitions (webclient-mode-transitions, AVG stage design §9.3): the
// stage root carries `data-mode-change`, the last LIVE mode change
// (`exploration-dialogue`, `combat-exploration`, ...), computed from the raw
// committed mode by composables/use-mode-change.js. Every mode transition
// is CSS keyed on it, so mounting and a reconnect — which never set it —
// render each mode's final state at once:
// - dialogue collapses the command region by a slide over the message
//   region, which widens in the commit's frame (the grid never animates:
//   the window would re-page every frame). The region is inert from the
//   commit and `visibility: hidden` once its slide ends (design D1);
// - entering combat plays the white flash once, fades the veil in, and
//   flips the command region's content to the combat root; leaving combat
//   fades the veil out and flips the content back (design D2).
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
  // Whether the collapsible command-line row is expanded (design D1):
  // rendered as `data-expanded` on `[data-anchor="command-line"]`.
  commandLineExpanded: { type: Boolean, default: false },
  // The last live mode change (webclient-mode-transitions D2), or null when
  // none happened since the last mount or reconnect.
  modeChange: { type: String, default: null },
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
    :data-mode-change="modeChange"
  >
    <div class="stage-vignette" data-testid="stage-vignette"></div>
    <!-- Decorative: always rendered, faded by opacity (design D2). -->
    <div
      class="stage-combat-veil"
      data-testid="stage-combat-veil"
      :data-mode="mode"
      aria-hidden="true"
    ></div>
    <slot name="backdrop" />
    <!-- The portrait anchors come after the combat veil (same z-index), so
         the standing portraits paint above it (design D1/D4). -->
    <div
      class="stage-anchor stage-actor-anchor"
      data-anchor="actor-left"
      data-testid="anchor-actor-left"
    >
      <slot name="actor-left" />
    </div>
    <div
      class="stage-anchor stage-actor-anchor"
      data-anchor="actor-right"
      data-testid="anchor-actor-right"
    >
      <slot name="actor-right" />
    </div>
    <!-- The combat entry flash (design D2): decorative, above the backdrop
         and the portraits, under every island and the band. -->
    <div class="stage-flash" data-testid="stage-flash" aria-hidden="true"></div>
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
    <div
      class="stage-anchor"
      data-anchor="choices"
      data-testid="anchor-choices"
    >
      <slot name="choices" />
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
        :inert="mode === 'dialogue' || null"
      >
        <slot name="band-command" />
      </div>
    </div>
    <div
      class="stage-anchor"
      data-anchor="command-line"
      data-testid="anchor-command-line"
      :data-expanded="commandLineExpanded ? 'true' : 'false'"
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

/* The combat veil (H2 supplies the low-HP and combat state; H1 ships the
   hooks — design D7). Always rendered and faded by its own opacity
   (webclient-mode-transitions D2); the gradient and its pulse live on a
   `::before` layer, so the pulse's opacity keyframes and the fade's opacity
   transition never fight over one property. The pulse runs only in combat. */
.elosern-stage .stage-combat-veil {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  opacity: 0;
}
.elosern-stage .stage-combat-veil::before {
  content: "";
  position: absolute;
  inset: 0;
  background: var(--stage-combat-veil);
}
.elosern-stage[data-elosern-mode="combat"] .stage-combat-veil {
  opacity: 1;
}
.elosern-stage[data-elosern-mode="combat"] .stage-combat-veil::before {
  animation: elosern-combat-pulse var(--motion-pulse) ease-in-out infinite;
}

/* The combat flash (webclient-mode-transitions D2): a warm white light that
   floods the stage once on entering combat — a hard attack and a longer
   release — brightest at the centre of the scene and falling off towards
   the edges, so it reads as an impact rather than a blank frame. Its peak is
   `--motion-flash-peak` (0 at `reduced`: a white flash is a photosensitivity
   trigger) and it lasts `--motion-flash` (0 at `reduced` and `off`). */
.elosern-stage .stage-flash {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  opacity: 0;
  background: radial-gradient(120% 100% at 50% 44%, #fffdf8 0%, #fff4e2 46%, #f4dcc0 100%);
}
.elosern-stage[data-mode-change$="-combat"] .stage-flash {
  animation: elosern-stage-flash var(--motion-flash) linear 1;
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
/* The insets (webclient-dialogue-stage-actors): 6% of the stage width,
   grown where the island column on that side would cover the figure's face
   (`--actor-left-inset` / `--actor-right-inset` in tokens.css; exactly 6% at
   1920x1080). */
.elosern-stage [data-anchor="actor-left"] { left: var(--actor-left-inset); }
.elosern-stage [data-anchor="actor-right"] { right: var(--actor-right-inset); }

/* choices (webclient-dialogue-choices-overlay D6): the dialogue choice
   list, horizontally centred on the stage at `min(560px, 40%)` wide and
   vertically centred in the span between the top band's inset and the
   expanded command-line row (`--stage-content-bottom`), so the list clears
   the place card, the islands, the band, and the borrowed command line at
   every supported viewport. The anchor itself is pointer-transparent; the
   list inside it takes pointer events and scrolls when it is taller than
   the span. No transform, so the text never lands on half pixels. */
.elosern-stage [data-anchor="choices"] {
  top: calc(var(--header-h) + var(--stage-inset-y));
  bottom: calc(var(--stage-content-bottom) + var(--stage-inset-y));
  left: calc(50% - min(280px, 20%));
  width: min(560px, 40%);
  z-index: 4;
  display: flex;
  flex-direction: column;
  justify-content: center;
  pointer-events: none;
}
.elosern-stage:not([data-elosern-mode="dialogue"]) [data-anchor="choices"] {
  display: none;
}

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
.elosern-stage [data-anchor="command-line"][data-expanded="false"] {
  display: none;
}

/* Mode-gated visibility (design D2/D7): CSS-only on data-elosern-mode,
   display:none so hidden surfaces leave the a11y tree and tab order. The
   matrix: the place card, the message region, both island anchors (`vitals`
   and `map`, with every island in them), and the command line are hidden in
   creation, where the command region spans the whole band; the command
   region is hidden in dialogue, where the message region spans the whole
   band; the minimap is hidden in combat; the objective line shows only in
   exploration; the scene backdrop stays visible in every mode. */
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
/* Dialogue (webclient-dialogue-stage-actors design D4): the message region
   spans the whole band at the same fixed height, from the commit's frame.
   The command region collapses by a slide instead of `display:none`
   (webclient-mode-transitions D1): it leaves the grid for an absolute layer
   over the band's right third, inert from the commit (HudFrame binds
   `inert`), slides out to the right and fades over the widened message
   region, then turns `visibility: hidden` — which also keeps the still-
   mounted `#action-dock` out of the accessibility tree. The stage root's
   own `overflow: hidden` clips the slide at the stage edge. */
.elosern-stage[data-elosern-mode="dialogue"] .stage-band {
  grid-template-columns: minmax(0, 1fr);
}
.elosern-stage[data-elosern-mode="dialogue"] [data-anchor="band-command"] {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 33.3333%;
  transform: translateX(calc(100% * var(--motion-travel)));
  opacity: 0;
  visibility: hidden;
}
.elosern-stage[data-elosern-mode="combat"] .local-map {
  display: none !important;
}
/* The objective line (webclient-avg-stage-hud-anchors design D2) is an
   exploration-only surface; it carries no tab stop, so no focus rescue. */
.elosern-stage:not([data-elosern-mode="exploration"]) [data-anchor="map"] .obj {
  display: none;
}

/* Live mode transitions (webclient-mode-transitions D1/D2). Declared only
   under `[data-mode-change]`, which a mount or a reconnect never sets, so
   those render every final state at once.

   The command region: leaving, it accelerates away over the panel duration
   while it thins early, so it never sits opaque over the widened window;
   returning, it re-enters the grid at the offset it holds and decelerates
   home. Leaving, `visibility` transitions over the slide's duration, which
   (being discrete) keeps the region visible until the slide ends; the return
   does not transition it, so the region is visible — and the dock focusable —
   in the commit's own frame. */
.elosern-stage[data-mode-change] [data-anchor="band-command"] {
  transition:
    transform var(--motion-panel) var(--ease-enter),
    opacity calc(var(--motion-panel) * 0.8) var(--ease-standard);
}
.elosern-stage[data-mode-change][data-elosern-mode="dialogue"] [data-anchor="band-command"] {
  transition:
    transform var(--motion-panel) var(--ease-exit),
    opacity calc(var(--motion-panel) * 0.6) var(--ease-standard),
    visibility var(--motion-panel) linear;
}
/* The veil breathes in and out behind the portraits. */
.elosern-stage[data-mode-change] .stage-combat-veil {
  transition: opacity var(--motion-actor) var(--ease-standard);
}
/* The command region's content turns over to the committed menu: the combat
   root swings in from one side on entering combat and the exploration
   overview from the other on leaving it. The dock switched its content at
   the commit and keeps focus throughout; the flip only reveals it. */
.elosern-stage[data-mode-change$="-combat"] [data-anchor="band-command"] > * {
  animation: elosern-panel-flip-in var(--motion-panel) var(--ease-enter) 1;
}
.elosern-stage[data-mode-change="combat-exploration"] [data-anchor="band-command"] > * {
  animation: elosern-panel-flip-out var(--motion-panel) var(--ease-enter) 1;
}

/* The open-surface registry (design D9): when a drawer or overlay is open
   the stage is visually recessed; the mark clears only when nothing is
   open. The transition is token-gated, so the motion level's `reduced` and
   `off` blocks resolve it to 0ms while the recessed state still applies. */
.elosern-stage[data-menu-open="true"] .stage-anchor:not(.stage-band > .stage-anchor),
.elosern-stage[data-menu-open="true"] .stage-band {
  filter: var(--menu-open-filter);
  transition: filter var(--motion-base) var(--ease-standard);
}
</style>
