<script setup>
// DockBreadcrumb (H3 webclient-hud-03-action-dock, task 4.6): the draft's
// `.crumb` strip. Hidden at depth 1 (no parent frame to return to); at
// depth ≥ 2 it renders `parent › current` from `view.dockTrail` (the router
// frame stack titles, task 3.1) with a back chevron that pops exactly one
// level — matching the keyboard Escape path (the store's `focusEscape()`).
import { computed } from "vue";

const props = defineProps({
  // The full frame-stack titles (root -> current), committed from the
  // router's `trail()`.
  trail: { type: Array, default: () => [] },
  // The router's menu depth (1 = root frame, 2+ = a submenu frame).
  depth: { type: Number, default: 1 },
  // The per-surface guidance prefix (legacy dock chrome); when set, the
  // crumb row carries it before the trail.
  guidancePrefix: { type: String, default: null },
  // The committed focus key: when the keyboard router's focus is on the
  // move frame's non-rendered `back` item, the back control carries the
  // focused presentation (fill + ring, not color alone).
  focusedKey: { type: String, default: null },
});

const emit = defineEmits(["back"]);

// The crumb is visible only when a deeper frame is active (depth ≥ 2).
const visible = computed(() => props.depth >= 2 && props.trail.length >= 2);
// `parent › current`: the trail minus the last entry, joined by " › ".
const parents = computed(() =>
  visible.value ? props.trail.slice(0, -1).join(" › ") : "",
);
const current = computed(() =>
  visible.value ? props.trail[props.trail.length - 1] : "",
);

function onBack() {
  // The back chevron pops exactly one router frame (the store's
  // `focusEscape()` path — the keyboard and pointer parity, task 8.6).
  emit("back");
}
</script>

<template>
  <div
    class="dock-crumb"
    :hidden="!visible"
    data-testid="dock-crumb"
  >
    <button
      type="button"
      class="dock-crumb__back"
      :class="{ 'dock-crumb__back--focused': focusedKey === 'back' }"
      aria-label="返回上一層"
      @click="onBack"
    >‹</button>
    <span v-if="guidancePrefix" class="dock-crumb__prefix">{{ guidancePrefix }}</span>
    <span class="dock-crumb__trail">
      <template v-if="parents">{{ parents }} › </template>
      <span class="dock-crumb__current">{{ current }}</span>
    </span>
  </div>
</template>

<style scoped>
/* The draft's `.crumb` strip: parent › current, the current segment in the
   accent colour. Hidden (display:none) at depth 1 (the root frame has no
   parent to return to). */
.dock-crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: none;
  font-size: 12px;
  color: var(--paper-500);
}

.dock-crumb[hidden] {
  display: none;
}

.dock-crumb__back {
  background: transparent;
  border: 0;
  color: var(--paper-300);
  font-size: 18px;
  line-height: 1;
  padding: 0 6px;
  cursor: pointer;
}

.dock-crumb__back:hover {
  color: var(--paper-50);
}

/* The focused back control: a fill + ring (box-shadow, no layout shift)
   — the same non-color-alone treatment the dock rows use, so the
   non-rendered `back` row keeps a visible focus carrier. */
.dock-crumb__back--focused {
  background: var(--panel-hi);
  box-shadow: 0 0 0 1px var(--gold-500);
  color: var(--paper-50);
}

.dock-crumb__prefix {
  color: var(--paper-500);
}

.dock-crumb__current {
  color: var(--gold-400);
  font-weight: 600;
}
</style>
