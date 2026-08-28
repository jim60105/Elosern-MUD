<script setup>
// HudDrawer (H4, webclient-hud-04-reference-drawers, design D1): the
// right-anchored drawer chrome shared by the six reference drawers. Fixed
// to the stage's right edge, its top edge inset one `--command-line-h`
// below the stage top (the reference's `.draw{top:46px}` clearance) and its
// bottom at the stage bottom, bounded to a width that
// never exceeds the viewport (`min(560px, 94vw)`), drawn on the solid panel
// background with a left border and a left-cast shadow so it reads as a
// surface laid over the stage, not a region of it. The head / body / foot
// are one column and the body is the drawer's only scrolling region. The
// enter/leave is a horizontal slide over a blurred scrim, both expressed
// through the `--motion-*` / `--ease-*` tokens so `prefers-reduced-motion`
// disables the transition at the token level while the open state still
// applies. At most one drawer is open at a time (structural: the store
// publishes a single `view.hudDrawer` name). Focus is trapped while open;
// Escape / the close control / the scrim each close and restore focus to
// the control that opened it.
import { onMounted, ref } from "vue";
import { createFocusTrap } from "./focus-trap.js";
import { glyphAttrs, glyphPath } from "./dock-icons.js";

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, required: true },
  subtitle: { type: String, default: "" },
  // The drawer's `data-testid` identity key (the drawer name) so browser
  // assertions can target the open drawer.
  drawerKey: { type: String, default: "" },
  // Optional leading head icon: a `dock-icons.js` glyph key. Unset (the
  // default) renders no icon — the other five drawers keep today's head.
  icon: { type: String, default: null },
  // Optional body modifier class (e.g. `hud-drawer__body--dock` when the
  // drawer hosts a dock service frame). The drawer root is a fragment while
  // open (scrim + panel), so the modifier is threaded explicitly rather than
  // left to attribute fallthrough (remove-redundant-dock-menu-layout).
  bodyClass: { type: String, default: "" },
});

const emit = defineEmits(["close"]);

const drawerEl = ref(null);
const closeBtnEl = ref(null);
let trap = null;

// The parent (`AppClient`) mounts this component only while a drawer is open
// (`v-if="store.view.hudDrawer"`, `:open="true"`), so a fresh mount means a
// drawer has just opened. By the time `onMounted` runs the template refs
// (`drawerEl` / `closeBtnEl`) are assigned, so create the shared focusable-
// query trap here (design D5) and move focus into the drawer; the close
// control is the natural first target.
onMounted(() => {
  if (drawerEl.value) {
    trap = createFocusTrap(drawerEl.value, {
      initialFocusEl: closeBtnEl.value || drawerEl.value,
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
       play (a `translateX(100%)` -> `translateX(0)` slide). While closed it
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
    <div class="hud-drawer__head">
      <svg
        v-if="icon && glyphPath(icon)"
        class="hud-drawer__icon"
        aria-hidden="true"
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
      >
        <path
          :d="glyphPath(icon)"
          stroke="currentColor"
          stroke-width="1.8"
          v-bind="glyphAttrs(icon)"
        />
      </svg>
      <h3 class="hud-drawer__title" data-testid="hud-drawer__title">
        {{ title }}
      </h3>
      <p v-if="subtitle" class="hud-drawer__subtitle">{{ subtitle }}</p>
      <button
        ref="closeBtnEl"
        type="button"
        class="hud-drawer__close"
        data-testid="hud-drawer-close"
        :tabindex="open ? 0 : -1"
        aria-label="關閉"
        @click="close"
      >
        <svg aria-hidden="true" width="17" height="17" viewBox="0 0 24 24" fill="none">
          <path
            :d="glyphPath('close')"
            stroke="currentColor"
            stroke-width="1.8"
            v-bind="glyphAttrs('close')"
          />
        </svg>
      </button>
    </div>
    <div class="hud-drawer__body" :class="bodyClass">
      <slot />
    </div>
    <div v-if="$slots.foot" class="hud-drawer__foot">
      <slot name="foot" />
    </div>
  </div>
</template>

<style>
/* The blurred scrim over the whole stage (the draft's `.draw` scrim). */
.hud-drawer-scrim {
  position: fixed;
  inset: 0;
  z-index: calc(var(--z-surface-modal) - 100);
  background: rgba(8, 7, 10, 0.5);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
}

/* The right-anchored drawer (the draft's `.draw` chrome). The top edge is
   inset one command-line strip height from the stage top, reproducing the
   reference's `top:46px` clearance (index.html:404) through the shared 46px
   token; the scrim keeps covering the whole stage. */
.hud-drawer {
  position: fixed;
  top: var(--command-line-h);
  right: 0;
  bottom: 0;
  width: min(560px, 94vw);
  z-index: var(--z-surface-modal);
  display: flex;
  flex-direction: column;
  background: var(--panel-solid);
  border-left: var(--line);
  box-shadow: -18px 0 44px -26px rgba(0, 0, 0, 0.9);
  transform: translateX(100%);
  transition: transform var(--motion-base) var(--ease-standard);
  outline: none;
}

.hud-drawer.open {
  transform: translateX(0);
}

.hud-drawer__head {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-4) var(--sp-4) var(--sp-3);
  border-bottom: var(--line);
}

/* The head title (the reference's `.dhead h3`: 20px display type with
   `.04em` tracking, index.html:410). */
.hud-drawer__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 20px;
  letter-spacing: .04em;
  flex: 1;
}

/* The head subtitle (the reference's `.dhead .sub`: 11px muted,
   index.html:411). */
.hud-drawer__subtitle {
  margin: 0;
  color: var(--paper-500);
  font-size: 11px;
}

/* The head icon (the reference's `.dhead .ic`, index.html:409-410). */
.hud-drawer__icon {
  width: 20px;
  height: 20px;
  color: var(--gold-400);
  flex: none;
}

/* The icon-only close control (the reference's `.closebtn`, 34x34 square). */
.hud-drawer__close {
  width: 34px;
  height: 34px;
  flex: none;
  display: grid;
  place-items: center;
  color: var(--paper-300);
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: 9px;
  cursor: pointer;
}

.hud-drawer__close:hover {
  border-color: var(--seal-500);
  color: var(--paper-50);
}

/* The skill drawer's static cast-syntax hint (the reference's footer copy). */
.hud-drawer__cast-hint {
  margin: 0;
  color: var(--paper-500);
  font-size: 0.85em;
}

/* The body is the drawer's only scrolling region; the head and foot are
   fixed, so a long reference surface scrolls inside the body only. */
.hud-drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: var(--sp-4);
  font-family: var(--f-sans);
  min-height: 0;
}

.hud-drawer__foot {
  border-top: var(--line);
  padding: var(--sp-3) var(--sp-4);
}
</style>
