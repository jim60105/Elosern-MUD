<script setup>
// HudFrame (H1, webclient-hud-01-shell-and-scene; AVG stage shell,
// webclient-avg-stage-shell design D1/D3/D4/D7): the full-bleed cinematic
// stage. A `position:absolute; overflow:clip` root with named anchors:
// - the island anchors named by their content
//   (webclient-avg-stage-hud-anchors design D1): `vitals`, the lower-left
//   dock standing on the band's top edge (vitals-bar-redesign design D1:
//   the chromeless condition icons over the three compact bars;
//   it may cover the player portrait's lowest
//   strip, never its face) and
//   `map` at the top-right (the place card first — place-card-relocation
//   design D2 — then the minimap, the one-line objective, and the title
//   ballot). In combat the `map` anchor is not rendered: the combat
//   formation uses the stage's right column (webclient-combat-formation D2);
// - the portrait anchors `actor-left` (the controlled figure and companions) and
//   `actor-right` (the dialogue host's stage actor while the mode is
//   dialogue, the foe line-up while it is combat —
//   webclient-combat-foes-on-stage), standing on the bottom band's top edge.
//   While the combat formation stands (`formation`, webclient-combat-formation
//   D1) both anchors span the stage, so the line-ups' formation boxes are
//   stage coordinates;
// - the `plates` layer (webclient-combat-formation D4): a stage-sized,
//   pointer-transparent layer above the portrait anchors and below the
//   islands, holding only the combat figures' glance plates;
// - the `choices` anchor (webclient-dialogue-choices-overlay D6): the
//   centred card — the dialogue choice list, or in exploration the
//   person-focus verb card and the presence overflow card
//   (exploration-presence-rail) — between the portraits and above the
//   expanded command-line row, rendered only in dialogue mode, while an
//   exploration card is open (`cardOpen`), or in combat. In combat it holds
//   the combat command card (webclient-combat-command-card-centred D1/D3):
//   the band-command slot — the one `#action-dock` — is teleported, never
//   remounted, into a card host this component creates and appends into the
//   anchor; the anchor narrows to the formation's dead-centre gap
//   (264px·S, the formation engine's `CARD_WIDTH`) and the card stands at
//   its top, `min(400px·S, the anchor's span)` tall;
// - the `presence` anchor (exploration-presence-rail design D4): the
//   presence rail on the stage floor, right-aligned and inset left of the
//   right-hand island column, its baseline just above the band;
// - the bottom band `.stage-band`: one fixed-height (`--band-h`) container
//   split into the message region `band-message` (left 2/3) and the command
//   region `band-command` (right 1/3). No frame, mode, or content resizes it;
//   creation hides the message region, dialogue collapses the command
//   region, and combat sets it `display:none` (its content is the centred
//   card), so the other one spans the band;
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
// flash 3, the plates layer 3 (after the flash), the presence anchor, the
// island anchors, and the choices anchor
// 4 (the choices anchor last in DOM order, so a card paints over the rail),
// band 5, command line 6. Drawers and overlays live outside the stage, above
// all of it.
//
// Person focus (exploration-presence-rail design D4, `personFocus`): while a
// person's verb card is open the place card and the minimap (the `map`
// anchor) step away, as in dialogue, and the command region goes `inert` and
// dims to about 35%.
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
//   fades the command card in (rising at `full`) as the flash releases
//   (webclient-combat-command-card-centred D6); leaving combat fades the veil
//   out and turns the band's returning content back (a short horizontal
//   wipe and fade, webclient-band-material-pass; design D2).
//
// The open-surface registry (design D9): a drawer or full-screen overlay
// marks the stage `menu-open` so the surfaces behind it are visually
// recessed; the mark clears only when no open surface remains.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { bindPlateGroup } from "./plate-group.js";

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
  // The terminal-round hold (webclient-combat-beat-choreography D6,
  // `view.beatHold`): while the round that ended the fight still plays, the
  // decorative combat veil stays; every committed surface has already
  // followed the committed mode.
  beatHold: { type: Boolean, default: false },
  // An exploration card (the verb card or the overflow card) is open in the
  // `choices` anchor (exploration-presence-rail).
  cardOpen: { type: Boolean, default: false },
  // A person's verb card is open: the cockpit steps away around it.
  personFocus: { type: Boolean, default: false },
  // The combat formation stands (webclient-combat-formation D1): in combat
  // and while a round that ended the fight still plays. The portrait anchors
  // then span the stage and the `plates` layer shows.
  formation: { type: Boolean, default: false },
});

// The open-surface registry drives the `menu-open` mark (design D9): the
// mark clears only when no surface remains open.
const menuOpen = computed(() => props.openSurfaces.length > 0);

// The command panel's flip (webclient-mode-transitions D2) is one-shot. The
// `data-mode-change` attribute persists until the next live change, and a
// CSS animation plays whenever a matching element is inserted, so keying the
// flip on it would replay the flip if the dock remounted mid-combat. The
// flip is keyed on `data-flip` instead: set in the patch of a live change
// into or out of combat, cleared when the flip's own animation ends.
// Entering combat no longer flips the band: the dock leaves it for the
// centred card, whose own entrance plays (webclient-combat-command-card-centred
// D2/D6).
const flip = ref(null);
watch(
  () => props.modeChange,
  (change) => {
    flip.value = change === "combat-exploration" ? change : null;
  },
);
function onFlipEnd(event) {
  if (event.animationName?.startsWith("elosern-panel-flip")) {
    flip.value = null;
  }
}

// The plates' keyboard group (webclient-combat-figure-plates D4): one tab
// stop while the formation stands and no ended round is held; the anchor
// leaves the tab order while focus is inside it, so Tab and Shift+Tab leave
// the group. plate-group.js moves focus and rescues it when its element
// goes away or inert.
const plateGroup = computed(() => props.formation && !props.beatHold);
const plateFocusInside = ref(false);
const platesRef = ref(null);
let unbindPlateGroup = null;
onMounted(() => {
  if (platesRef.value) {
    unbindPlateGroup = bindPlateGroup(platesRef.value, {
      onInside: (inside) => {
        plateFocusInside.value = inside;
      },
    });
  }
});
onBeforeUnmount(() => {
  unbindPlateGroup?.();
});

// The combat command card's host (webclient-combat-command-card-centred D1):
// one element per stage, created here so the Teleport has a real target at
// the first render — attached to the document or not, and in combat at mount —
// and appended into this stage's own `choices` anchor by its function ref.
// The Teleport is enabled only in combat; Vue then moves the band-command
// slot's existing nodes into the host and back, so the dock keeps its node,
// its component state, and its test ids.
const cardHost = typeof document === "undefined" ? null : document.createElement("div");
if (cardHost) {
  cardHost.className = "stage-card-host";
  cardHost.setAttribute("data-testid", "stage-card-host");
}
function mountCardHost(el) {
  if (el && cardHost && cardHost.parentNode !== el) {
    el.appendChild(cardHost);
  }
}

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
    :data-beat-hold="beatHold ? 'combat' : null"
    :data-card-open="cardOpen ? 'true' : null"
    :data-person-focus="personFocus ? 'true' : null"
    :data-formation="formation ? 'true' : null"
  >
    <!-- The stage metrics probe (webclient-combat-formation D1): boxes whose
         heights resolve the shell's length tokens, which their computed
         custom properties do not, so the formation input reads real px. -->
    <div class="stage-metrics" data-testid="stage-metrics" aria-hidden="true">
      <span data-metric="--actor-h"></span>
      <span data-metric="--header-h"></span>
      <span data-metric="--band-h"></span>
      <span data-metric="--command-line-h"></span>
    </div>
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
      data-anchor="presence"
      data-testid="anchor-presence"
    >
      <slot name="presence" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="vitals"
      data-testid="anchor-vitals"
      :inert="mode === 'dialogue' || null"
      :aria-hidden="mode === 'dialogue' ? 'true' : null"
    >
      <slot name="vitals" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="map"
      data-testid="anchor-map"
      :inert="mode === 'dialogue' || personFocus || null"
      :aria-hidden="mode === 'dialogue' || personFocus ? 'true' : null"
    >
      <slot name="map" />
    </div>
    <div
      class="stage-anchor"
      data-anchor="choices"
      data-testid="anchor-choices"
      :ref="mountCardHost"
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
        :data-flip="flip"
        @animationend="onFlipEnd"
        :inert="mode === 'dialogue' || personFocus || null"
      >
        <Teleport :to="cardHost" :disabled="mode !== 'combat' || !cardHost">
          <slot name="band-command" />
        </Teleport>
      </div>
    </div>
    <!-- The figure plates (webclient-combat-formation D4): filled only
         while the formation stands (a leaving plate fades out inert); inert
         and hidden from assistive technology while a round that ended the
         fight is held. The anchor is the plates' keyboard group
         (webclient-combat-figure-plates D4): after the band in DOM order, so
         Tab from the action dock reaches it next; its paint order is its
         explicit z-index (3), above the portraits and the flash and below
         the islands and the band. -->
    <div
      ref="platesRef"
      class="stage-anchor"
      data-anchor="plates"
      data-testid="anchor-plates"
      :role="plateGroup ? 'group' : null"
      :aria-label="plateGroup ? '戰場' : null"
      :tabindex="plateGroup ? (plateFocusInside ? -1 : 0) : null"
      :inert="beatHold || null"
      :aria-hidden="beatHold ? 'true' : null"
    >
      <slot name="plates" />
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
/* `overflow: clip`, not `hidden`: the stage clips its layers the same way but
   is never a scroll container. With `hidden` the stage stays programmatically
   scrollable, so the command region parked off the right edge in dialogue
   (webclient-mode-transitions D1) widened its scroll area by a whole panel,
   and focusing the returning dock scrolled the entire stage sideways, then
   dragged it back as the slide shrank the overflow. A clip container has no
   scroll position for a focus move or `scrollIntoView` to change. */
.elosern-stage {
  position: absolute;
  inset: 0;
  overflow: clip;
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
/* The terminal-round hold (webclient-combat-beat-choreography D6): the
   round that ended the fight still plays in front of the combat stage, so
   the veil keeps its combat opacity and its pulse until the round ends; then
   it fades out on the combat exit's own veil transition. The pulse is one
   rule for both states, so its resolved value never changes across the mode
   flip and the running animation continues unbroken. The veil is decorative
   and `aria-hidden`; nothing committed waits for it. */
.elosern-stage[data-beat-hold="combat"] .stage-combat-veil {
  opacity: 1;
}
.elosern-stage[data-elosern-mode="combat"] .stage-combat-veil::before,
.elosern-stage[data-beat-hold="combat"] .stage-combat-veil::before {
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

/* vitals / map: the island stacks. Bounded between the top band and the
   bottom band (never the band's content) and scrolling internally. `map`
   begins directly below the top band; `vitals` is the lower-left dock
   (vitals-bar-redesign design D1): bottom-anchored on the band's top edge,
   growing upward only as far as its compact content. The
   `.elosern-root` override in app-shell.css repeats these offsets (it sets
   the column widths); keep the two in step. */
.elosern-stage [data-anchor="vitals"] {
  bottom: var(--band-h);
  left: calc(16px * var(--ui-scale));
  width: var(--vitals-dock-w);
  z-index: 4;
  display: flex;
  flex-direction: column;
  gap: calc(9px * var(--ui-scale));
  max-height: calc(100% - var(--header-h) - var(--band-h) - 2 * var(--stage-inset-y));
  overflow-y: auto;
  overflow-x: hidden;
}
.elosern-stage [data-anchor="map"] {
  top: calc(var(--header-h) + var(--stage-inset-y));
  right: calc(16px * var(--ui-scale));
  width: calc(230px * var(--ui-scale));
  z-index: 4;
  display: flex;
  flex-direction: column;
  gap: calc(9px * var(--ui-scale));
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
  height: min(62vh, 680px * var(--ui-scale), calc(100% - var(--header-h) - var(--band-h)));
  aspect-ratio: 2 / 3;
  z-index: 2;
  pointer-events: none;
}
/* The insets (webclient-dialogue-stage-actors): 6% of the stage width,
   grown where the island column on that side would cover the figure's face
   (`--actor-left-inset` / `--actor-right-inset` in tokens.css; at the
   1451x790 reference both take their column-clearance value, so the 6% term
   acts only as the floor). */
.elosern-stage [data-anchor="actor-left"] { left: var(--actor-left-inset); overflow: visible; }
.elosern-stage [data-anchor="actor-right"] { right: var(--actor-right-inset); }
/* The combat formation (webclient-combat-formation D1): both portrait
   anchors span the stage, so the line-ups' formation boxes are stage
   coordinates. Keyed on `data-formation`, not on the mode: a held round that
   ended the fight keeps the formation while the mode is already another. The
   anchors stay pointer-transparent; the figures' chest labels need no
   dock-clearing offset here (the formation keeps the dock off every face).
   A foe line-up still fading out after the formation ended keeps the
   right anchor spanning the stage, so its foes fade where they stood. */
.elosern-stage[data-formation="true"] [data-anchor="actor-left"],
.elosern-stage[data-formation="true"] [data-anchor="actor-right"],
.elosern-stage [data-anchor="actor-right"]:has(> [data-testid="foe-lineup"][data-formation="true"]) {
  inset: 0;
  height: auto;
  aspect-ratio: auto;
  overflow: visible;
  --actor-label-left: 18%;
}

/* The plates layer (design D4): stage-sized and non-scrolling, above the
   portrait anchors (and the flash, after it in DOM order) and below the
   islands, the band, the choices anchor and the command line. */
.elosern-stage [data-anchor="plates"] {
  inset: 0;
  z-index: 3;
  overflow: visible;
  pointer-events: none;
}

/* The metrics probe: laid out, never painted, never hit. */
.elosern-stage .stage-metrics {
  position: absolute;
  left: 0;
  top: 0;
  width: 0;
  visibility: hidden;
  pointer-events: none;
}
.elosern-stage .stage-metrics > span {
  position: absolute;
  left: 0;
  top: 0;
  width: 1px;
}
.elosern-stage .stage-metrics > [data-metric="--actor-h"] { height: var(--actor-h); }
.elosern-stage .stage-metrics > [data-metric="--header-h"] { height: var(--header-h); }
.elosern-stage .stage-metrics > [data-metric="--band-h"] { height: var(--band-h); }
.elosern-stage .stage-metrics > [data-metric="--command-line-h"] { height: var(--command-line-h); }

/* choices (webclient-dialogue-choices-overlay D6): the dialogue choice
   list, horizontally centred on the stage at `min(560px, 40%)` wide and
   vertically centred in the span between the top band's inset and the
   scene caption row that sits on the expanded command-line row
   (`--stage-caption-top`), so the list clears the place card, the islands,
   the scene caption, the band, and the borrowed command line at every
   supported viewport. The anchor itself is pointer-transparent; the
   list inside it takes pointer events and scrolls when it is taller than
   the span. No transform, so the text never lands on half pixels. */
.elosern-stage [data-anchor="choices"] {
  top: calc(var(--header-h) + var(--stage-inset-y));
  bottom: calc(var(--stage-caption-top) + 8px * var(--ui-scale));
  left: calc(50% - min(280px * var(--ui-scale), 20%));
  width: min(560px * var(--ui-scale), 40%);
  z-index: 4;
  display: flex;
  flex-direction: column;
  justify-content: center;
  pointer-events: none;
}
.elosern-stage:not([data-elosern-mode="dialogue"]):not([data-elosern-mode="combat"]):not([data-card-open="true"]) [data-anchor="choices"] {
  display: none;
}
/* The combat command card (webclient-combat-command-card-centred D3): the
   anchor narrows to a fixed 264px·S column centred on the stage — the same
   width as the formation engine's `CARD_WIDTH` (components/combat-formation.js),
   whose dead-centre gap keeps every figure, plate and marker outside it —
   and the card stands at the anchor's top, `min(400px·S, the anchor's
   span)` tall. No frame resizes it: the rows scroll inside the card. */
.elosern-stage[data-elosern-mode="combat"] [data-anchor="choices"] {
  left: calc(50% - 132px * var(--ui-scale));
  width: calc(264px * var(--ui-scale));
  justify-content: flex-start;
}
.elosern-stage .stage-card-host {
  display: none;
}
.elosern-stage[data-elosern-mode="combat"] .stage-card-host {
  display: flex;
  flex-direction: column;
  flex: none;
  height: min(calc(400px * var(--ui-scale)), 100%);
  min-height: 0;
}
/* The stage target step (webclient-combat-stage-target-picking D3): the card
   collapses to its target prompt at the same centre, width and top — the
   host shrinks to the prompt, at most 136px·S tall. */
.elosern-stage[data-elosern-mode="combat"] .stage-card-host:has(> .action-dock--target) {
  height: auto;
  max-height: calc(136px * var(--ui-scale));
}

/* presence (exploration-presence-rail design D4; redesign §4.1): the
   presence rail stands on the stage floor, right-aligned and inset left of
   the right-hand island column (whose left edge is `--right-column - 12px`
   from the stage's right edge), its baseline just above the band. The anchor
   is pointer-transparent; the rail inside it takes pointer events. */
.elosern-stage [data-anchor="presence"] {
  right: calc(var(--right-column, 258px * var(--ui-scale)) + 12px * var(--ui-scale));
  bottom: calc(var(--band-h) + 10px * var(--ui-scale));
  z-index: 4;
  display: flex;
  justify-content: flex-end;
  pointer-events: none;
}
.elosern-stage:not([data-elosern-mode="exploration"]) [data-anchor="presence"] {
  display: none;
}

/* Person focus (design D4): the place card and the minimap step away like
   the dialogue screen's, and the command panel dims to about 35% while
   `inert` (bound above). The fade uses the reveal token, so `off` resolves
   it in the commit frame. */
.elosern-stage [data-anchor="map"],
.elosern-stage [data-anchor="band-command"] {
  transition: opacity var(--motion-reveal) var(--ease-standard);
}
.elosern-stage[data-person-focus="true"] [data-anchor="map"] {
  opacity: 0;
  pointer-events: none;
}
.elosern-stage[data-person-focus="true"] [data-anchor="band-command"] {
  opacity: 0.35;
}

/* The bottom band (design D1): one fixed-height container spanning the
   stage bottom. It carries the band material once across both regions, so
   no seam and no stage background ever shows inside it: a deep ink ground
   (never lighter than the narrative's contrast reference) under a fine gold
   edge (webclient-band-material-pass). Its height is the `--band-h` token
   alone; the seam decoration overhangs its top edge and never takes space. */
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
  background:
    radial-gradient(60% 120% at 50% 0%, rgba(185, 154, 96, 0.07), transparent 70%),
    linear-gradient(0deg, #0b090d, #120f16 62%, #16131b);
  box-shadow: inset 0 1px 0 rgba(0, 0, 0, 0.6);
  /* The command region's dialogue slide travels past the band's right edge
     (webclient-mode-transitions D1). Clip it horizontally here so it never
     adds to the stage's scrollable width; `clip` (unlike `hidden`) leaves
     the vertical axis `visible`, so whatever overhangs the band's top edge
     (the seam, the name plate, the dock's popovers) still shows. */
  overflow-x: clip;
}
/* The stage seam (webclient-band-material-pass): decoration only, inert to
   the pointer and absent from the accessibility tree. `::before` is the
   feather that settles the lowest strip of the art into the band (it
   overlays the art; the stage box keeps its full height). `::after` is the
   fine gold edge — brightest at the centre, fading out towards both sides —
   with a small lozenge ornament at its centre. */
.elosern-stage .stage-band {
  --band-edge-line: linear-gradient(90deg, transparent 0%, var(--band-edge-dim) 12%, var(--band-edge) 38%, var(--band-edge) calc(50% - 22px * var(--ui-scale)), transparent calc(50% - 16px * var(--ui-scale)), transparent calc(50% + 16px * var(--ui-scale)), var(--band-edge) calc(50% + 22px * var(--ui-scale)), var(--band-edge) 62%, var(--band-edge-dim) 88%, transparent 100%) center / 100% 1px no-repeat;
}
.elosern-stage .stage-band::before,
.elosern-stage .stage-band::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  pointer-events: none;
}
.elosern-stage .stage-band::before {
  bottom: 100%;
  height: var(--band-seam-feather);
  background: linear-gradient(0deg, rgba(11, 9, 13, 0.62), rgba(11, 9, 13, 0.22) 55%, transparent);
}
.elosern-stage .stage-band::after {
  top: calc(-5px * var(--ui-scale));
  height: calc(11px * var(--ui-scale));
  background: var(--band-ornament) center / calc(30px * var(--ui-scale)) calc(11px * var(--ui-scale)) no-repeat, var(--band-edge-line);
}
/* The expanded command-line row stands on the seam's centre; the ornament
   steps aside so no half of it peeks out below the row. */
.elosern-stage:has([data-anchor="command-line"][data-expanded="true"]) .stage-band::after {
  background: var(--band-edge-line);
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
  padding: calc(10px * var(--ui-scale)) calc(12px * var(--ui-scale)) var(--band-pad-bottom) calc(18px * var(--ui-scale));
}
.elosern-stage [data-anchor="band-command"] {
  padding: calc(10px * var(--ui-scale)) calc(18px * var(--ui-scale)) var(--band-pad-bottom) calc(6px * var(--ui-scale));
}
/* The region divider (webclient-band-material-pass): one subdued vertical
   rule between the message and command regions, fading out at both ends.
   It belongs to the command region, so it leaves with it in dialogue and
   never shows in creation (where the region spans the band). */
.elosern-stage:not([data-elosern-mode="creation"]) [data-anchor="band-command"]::before {
  content: "";
  position: absolute;
  left: 0;
  top: calc(18px * var(--ui-scale));
  bottom: calc(18px * var(--ui-scale));
  width: 1px;
  background: linear-gradient(180deg, transparent, var(--ink-600) 22%, rgba(143, 113, 60, 0.55) 50%, var(--ink-600) 78%, transparent);
  pointer-events: none;
}

/* command-line: one row docked on the message region's top edge (design
   D3), from 16px past the vitals dock's right edge (the dock stands on the
   same band edge — vitals-bar-redesign design D1) to the message region's
   right edge. It overlays the lowest strip of the stage box, never the band. */
.elosern-stage [data-anchor="command-line"] {
  left: calc(var(--vitals-dock-w) + 32px * var(--ui-scale));
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
   matrix: the message region, both island anchors (`vitals` and `map`, with
   every island in them, the place card included), and the command line are hidden in
   creation, where the command region spans the whole band; the command
   region and both island anchors are hidden in dialogue, where the message region spans the whole
   band; the minimap is hidden in combat; the objective line shows only in
   exploration; the scene backdrop stays visible in every mode. */
.elosern-stage[data-elosern-mode="creation"] [data-anchor="band-message"],
.elosern-stage[data-elosern-mode="creation"] [data-anchor="vitals"],
.elosern-stage[data-elosern-mode="creation"] [data-anchor="map"],
.elosern-stage[data-elosern-mode="creation"] [data-anchor="command-line"] {
  display: none;
}
.elosern-stage[data-elosern-mode="creation"] .stage-band {
  grid-template-columns: minmax(0, 1fr);
}
/* Cockpit islands recede around the conversation. Discrete display keeps
   the exit paint alive only for the existing reveal duration; inert and
   aria-hidden remove interaction at commit. Mount/reconnect hide at once.
   Older browsers without discrete transitions also hide at once. */
.elosern-stage[data-elosern-mode="dialogue"] [data-anchor="vitals"],
.elosern-stage[data-elosern-mode="dialogue"] [data-anchor="map"] {
  display: none !important;
  opacity: 0;
}
.elosern-stage[data-mode-change][data-elosern-mode="dialogue"] [data-anchor="vitals"],
.elosern-stage[data-mode-change][data-elosern-mode="dialogue"] [data-anchor="map"] {
  transition:
    opacity var(--motion-reveal) var(--ease-exit),
    display var(--motion-reveal) allow-discrete;
}
/* Dialogue (webclient-dialogue-stage-actors design D4): the message region
   spans the whole band at the same fixed height, from the commit's frame.
   The command region collapses by a slide instead of `display:none`
   (webclient-mode-transitions D1): it leaves the grid for an absolute layer
   over the band's right third, inert from the commit (HudFrame binds
   `inert`), slides out to the right and fades over the widened message
   region, then turns `visibility: hidden` — which also keeps the still-
   mounted `#action-dock` out of the accessibility tree. The stage root's
   own `overflow: clip` clips the slide at the stage edge without making the
   stage scrollable, so no focus move can scroll the stage towards it. */
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
/* Combat (webclient-combat-command-card-centred D2): the command region's
   content is the centred card, so the region leaves the layout and the
   message region spans the band at the same fixed height from the commit's
   frame; the message page keeps its reading measure. */
.elosern-stage[data-elosern-mode="combat"] .stage-band {
  grid-template-columns: minmax(0, 1fr);
}
.elosern-stage[data-elosern-mode="combat"] [data-anchor="band-command"] {
  display: none;
}
.elosern-stage[data-elosern-mode="combat"] .local-map {
  display: none !important;
}
/* The `map` anchor in combat (webclient-combat-formation D2): the place
   card and everything else in the right column leave while the mode is
   combat, because the formation stands there. A held round that ended the
   fight follows the committed mode at the commit, so the column returns at
   once (the held foes are inert decoration over it until the round ends). */
.elosern-stage[data-elosern-mode="combat"] [data-anchor="map"] {
  display: none;
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
/* Leaving combat, the dock that has just moved back from the card turns the
   exploration overview over in the band (a wipe and fade). It switched its
   content at the commit; the flip only reveals it. Keyed on the one-shot
   `data-flip` (see the script), so a dock remounted later in the same mode
   never flips again. */
.elosern-stage [data-anchor="band-command"][data-flip="combat-exploration"] > * {
  animation: elosern-panel-flip-out var(--motion-panel) var(--ease-enter) 1;
}

/* The combat card's entrance (webclient-combat-command-card-centred D6):
   on a live change into combat the card fades in while it rises the small
   shift, starting once the flash has played. `data-mode-change` is never set
   on a mount or a reconnect, so those render the card at rest; at `reduced`
   the tokens leave a 150ms fade with no delay and no rise, at `off` nothing.
   `backwards` only holds the paint: the rows take keys and pointer from the
   commit's frame. */
.elosern-stage[data-mode-change$="-combat"] [data-anchor="choices"] .stage-card-host > .action-dock--card {
  animation: elosern-combat-card-in var(--motion-reveal) var(--ease-enter) var(--motion-flash) backwards;
}
@keyframes elosern-combat-card-in {
  from {
    opacity: 0;
    transform: translateY(calc(var(--motion-shift-sm) * var(--motion-travel)));
  }
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
