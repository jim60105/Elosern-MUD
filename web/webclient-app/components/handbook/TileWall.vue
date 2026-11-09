<script setup>
// TileWall (handbook-primitives, design D2): the grouped tile wall shared by
// the codex (CodexTileGrid) and the titles medal wall (CodexMedalGrid),
// ported unchanged from docs/design/handbook-codex-titles/TileWall.vue. One
// listbox, one roving tab stop; arrow keys walk the tiles in reading order (Up/Down
// jump a measured row), Home/End go to the ends, Enter/Space/click select.
// A tile with `selectable: false` (a codex placeholder) stays focusable and is
// announced by its own label, but never selects.
import { computed, nextTick, ref } from "vue";

const props = defineProps({
  // [{ key, label | null, items: [{ id, selectable, label }] }]
  groups: { type: Array, required: true },
  selectedId: { type: String, default: null },
  ariaLabel: { type: String, required: true },
  // "tile" (square art tiles) or "medal" (round medals with a caption).
  variant: { type: String, default: "tile" },
});
const emit = defineEmits(["select"]);

const flat = computed(() => props.groups.flatMap((group) => group.items));
const focusId = ref(null);
const rovingId = computed(() => {
  const ids = flat.value.map((item) => item.id);
  if (focusId.value && ids.includes(focusId.value)) return focusId.value;
  if (props.selectedId && ids.includes(props.selectedId)) return props.selectedId;
  return ids[0] ?? null;
});

const els = new Map();
function setEl(id, el) {
  if (el) els.set(id, el);
  else els.delete(id);
}

function columnsOf(el) {
  const grid = el?.parentElement;
  if (!grid) return 1;
  return getComputedStyle(grid).gridTemplateColumns.split(" ").filter(Boolean).length || 1;
}

async function focusAt(index) {
  const items = flat.value;
  if (!items.length) return;
  const clamped = Math.max(0, Math.min(items.length - 1, index));
  focusId.value = items[clamped].id;
  await nextTick();
  els.get(focusId.value)?.focus();
}

function select(item) {
  if (!item.selectable) return;
  focusId.value = item.id;
  emit("select", item.id);
}

function onKeydown(event) {
  const items = flat.value;
  const index = items.findIndex((item) => item.id === rovingId.value);
  if (index < 0) return;
  const cols = columnsOf(els.get(items[index].id));
  const moves = {
    ArrowRight: index + 1,
    ArrowLeft: index - 1,
    ArrowDown: index + cols,
    ArrowUp: index - cols,
    Home: 0,
    End: items.length - 1,
  };
  if (event.key in moves) {
    event.preventDefault();
    focusAt(moves[event.key]);
  } else if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    select(items[index]);
  }
}
</script>

<template>
  <div
    class="tile-wall"
    :class="`tile-wall--${variant}`"
    data-testid="tile-wall"
    role="listbox"
    :aria-label="ariaLabel"
    @keydown="onKeydown"
  >
    <section
      v-for="group in groups"
      :key="group.key"
      class="tile-wall__group"
      role="group"
      :aria-label="group.label || ariaLabel"
    >
      <h4 v-if="group.label" class="tile-wall__group-head" aria-hidden="true">
        <span>{{ group.label }}</span>
        <span class="tile-wall__rule"></span>
      </h4>
      <div class="tile-wall__grid">
        <div
          v-for="item in group.items"
          :key="item.id"
          :ref="(el) => setEl(item.id, el)"
          role="option"
          class="tile-wall__cell"
          :class="{ 'is-selected': item.id === selectedId, 'is-inert': !item.selectable }"
          :tabindex="item.id === rovingId ? 0 : -1"
          :aria-selected="String(item.id === selectedId)"
          :aria-disabled="item.selectable ? undefined : 'true'"
          :aria-label="item.label"
          :data-tile="item.id"
          @click="select(item)"
          @focus="focusId = item.id"
        >
          <slot name="tile" :item="item" :selected="item.id === selectedId" />
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.tile-wall {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  outline: none;
}

.tile-wall__group-head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin: 0 0 var(--sp-2);
  color: var(--gold-500);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.24em;
}

.tile-wall__rule {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

.tile-wall__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(calc(92px * var(--ui-scale)), 1fr));
  gap: var(--sp-2);
}

.tile-wall--medal .tile-wall__grid {
  grid-template-columns: repeat(auto-fill, minmax(calc(100px * var(--ui-scale)), 1fr));
  gap: var(--sp-4) var(--sp-2);
}

.tile-wall__cell {
  position: relative;
  min-width: 0;
  border-radius: var(--radius-sm);
  outline: none;
  cursor: pointer;
}

.tile-wall__cell.is-inert {
  cursor: default;
}

.tile-wall__cell:focus-visible {
  box-shadow: var(--focus);
}
</style>
