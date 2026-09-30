<script setup>
// HudDrawer (H4, webclient-hud-04-reference-drawers; framing unified by
// webclient-drawer-frame-unification): the drawer chrome shared by the
// reference drawers and the gallery's nested editors. It fills the reference
// workspace (under the top navigation, inside both side insets, above the
// band's lowest control strip) as a fully opaque ink panel, so it reads as a
// surface laid over the stage, not a region of it. The shared DrawerHeader /
// body / foot are one column and the body is the drawer's only scrolling
// region. The enter/leave is a horizontal slide over a dark scrim, both expressed
// through the `--motion-*` / `--ease-*` tokens so the motion level's
// `reduced` and `off` blocks resolve the transition to 0ms while the open
// state still applies. At most one drawer is open at a time (structural: the store
// publishes a single `view.hudDrawer` name). Focus is trapped while open;
// Escape / the close control / the scrim each close and restore focus to
// the control that opened it.
import { onMounted, ref } from "vue";
import { createFocusTrap } from "./focus-trap.js";
import DrawerHeader from "./DrawerHeader.vue";

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  // The drawer's `data-testid` identity key (the drawer name) so browser
  // assertions can target the open drawer.
  drawerKey: { type: String, default: "" },
  // The leading head glyph: a `dock-icons.js` registry key, drawn by the
  // shared DrawerHeader. Every reference drawer declares one.
  icon: { type: String, default: null },
});

const emit = defineEmits(["close"]);

const drawerEl = ref(null);
const headerRef = ref(null);
let trap = null;

// The parent (`AppClient`) mounts this component only while a drawer is open
// (`v-if="store.view.hudDrawer"`, `:open="true"`), so a fresh mount means a
// drawer has just opened. By the time `onMounted` runs the template refs
// (`drawerEl` / the header's exposed `closeButton`) are assigned, so create the shared focusable-
// query trap here (design D5) and move focus into the drawer; the close
// control is the natural first target.
onMounted(() => {
  if (drawerEl.value) {
    trap = createFocusTrap(drawerEl.value, {
      initialFocusEl: headerRef.value?.closeButton || drawerEl.value,
      openerEl: document.activeElement,
    });
    trap.enter();
  }
});

function close() {
  if (trap) {
    trap.restore();
    trap = null;
  }
  emit("close");
}

function onKeydown(event) {
  if (event.key === "Escape") {
    // The drawer owns Escape while open (design D4): it closes and pops
    // exactly one menu level if it hosts a router frame (the store handles
    // the pop); the stage behind it keeps the recession cleared once the
    // last surface closes (AppClient's open-surfaces registry).
    event.preventDefault();
    event.stopPropagation();
    close();
    return;
  }
  if (event.key !== "Tab") {
    // A focus-trapped surface owns every key it receives
    // (webclient-pointer-activation): stop propagation so the document-level
    // keyboard bridge (and the router behind the drawer) never consumes
    // navigation keys while the drawer holds trapped focus.
    event.stopPropagation();
  }
  if (event.key === "Tab" && trap) {
    trap.onKeydown(event);
  }
}

function onScrimClick() {
  close();
}
</script>

<template>
  <!-- The blurred scrim covers the whole stage while any drawer is open. -->
  <div
    v-if="open"
    class="hud-drawer-scrim"
    data-testid="hud-drawer-scrim"
    @click="onScrimClick"
  ></div>

  <!-- The drawer chrome is kept mounted so both the enter and leave slides
       play (an off-screen-right -> `translateX(0)` slide). While closed it
       sits off-screen; the close control leaves the tab order via a
       dynamic `tabindex`. The body content (the reference surface) is
       `v-if`'d by the parent, so a closed drawer holds no surface in the
       DOM or the tab order. -->
  <div
    ref="drawerEl"
    :class="open ? 'hud-drawer open' : 'hud-drawer'"
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    data-testid="hud-drawer"
    :data-drawer-key="drawerKey"
    :data-open="String(open)"
    @keydown="onKeydown"
  >
    <DrawerHeader
      ref="headerRef"
      surface="hud-drawer"
      :icon="icon"
      :title="title"
      :subtitle="subtitle"
      :close-tabindex="open ? 0 : -1"
      @close="close"
    />
    <div class="hud-drawer__workspace">
      <aside v-if="$slots.art" class="hud-drawer__art">
        <slot name="art" />
      </aside>
      <div class="hud-drawer__body">
        <slot />
      </div>
    </div>
    <div v-if="$slots.foot" class="hud-drawer__foot">
      <slot name="foot" />
    </div>
  </div>
</template>

<style>
/* The scrim over the whole viewport. Its dark fill alone recesses what lies
   behind the drawer; the blur is progressive decoration only
   (webclient-drawer-frame-unification), so a browser without
   backdrop-filter shows the same opaque panel over the same dark scrim. */
.hud-drawer-scrim {
  position: fixed;
  inset: 0;
  z-index: calc(var(--z-surface-modal) - 100);
  background: var(--surface-scrim);
}
@supports (backdrop-filter: blur(1px)) {
  .hud-drawer-scrim { backdrop-filter: blur(2px) saturate(.8); }
}

/* The reference workspace (webclient-drawer-frame-unification): 12px under
   the top navigation, 16px inside each side, `--workspace-bottom` above the
   viewport bottom — over the stage, the band and the command-line row. A
   fully opaque ink panel with a fine gold-tinted border; it slides in from
   the right edge through the motion tokens. */
.hud-drawer {
  position: fixed;
  inset: calc(var(--header-h) + 12px * var(--ui-scale)) calc(16px * var(--ui-scale)) var(--workspace-bottom) calc(16px * var(--ui-scale));
  z-index: var(--z-surface-modal);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--surface-panel);
  border: 1px solid #bca57966;
  border-radius: var(--radius);
  box-shadow: 0 calc(16px * var(--ui-scale)) calc(64px * var(--ui-scale)) #000a, inset 0 1px 0 #e8d8aa14;
  /* Fully off-screen while closed, shadow included. */
  transform: translateX(calc(100% + 96px * var(--ui-scale)));
  transition: transform var(--motion-base) var(--ease-standard);
  outline: none;
}

.hud-drawer.open {
  transform: translateX(0);
}

/* The skill drawer's static cast-syntax hint (the reference's footer copy). */
.hud-drawer__cast-hint {
  margin: 0;
  color: var(--paper-500);
  font-size: max(var(--text-xs), 0.85em);
}

/* The workspace row under the header: an optional art column beside the
   content body. */
.hud-drawer__workspace {
  display: flex;
  flex: 1;
  min-height: 0;
}

/* The art column (webclient-drawer-content-polish): only drawers about the
   current character provide it. It is bounded to min(360px, 28%) of the
   workspace, so the content keeps the larger share at every desktop width,
   and it sits on plain ink — no stand-in scene illustration behind the
   portrait. */
.hud-drawer__art {
  flex: 0 0 min(360px * var(--ui-scale), 28%);
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(180deg, #15171b, #0c0e11);
  border-right: 1px solid #bca57926;
}
.hud-drawer__art .reference-artwork { height: 100%; }
.hud-drawer__art .reference-artwork img { object-fit: cover; object-position: center top; }

/* The body is the drawer's only scrolling region; the head and foot are
   fixed, so a long reference surface scrolls inside the body only. */
.hud-drawer__body {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-5);
  font-family: var(--f-sans);
  scrollbar-color: var(--ink-600) transparent;
  scrollbar-width: thin;
}

@media (max-width: 1350px) {
  .hud-drawer__body { padding: calc(14px * var(--ui-scale)); }
}

.hud-drawer__foot {
  border-top: var(--line);
  padding: var(--sp-3) var(--sp-4);
}
</style>
