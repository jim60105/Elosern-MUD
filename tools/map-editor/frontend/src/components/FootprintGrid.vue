<script setup>
// The footprint mask's explicit cell control (frontend design §4.1): a
// monospace #/. grid, north row first, with a one-cell margin so neighbours
// can be filled. Arrow keys move the focused cell, Space (or Enter) toggles
// it; each toggle is one command on the owning settlement document. Rows and
// columns are labelled with their wilderness cell indices (1 km 格).
import { computed, nextTick, ref } from "vue";
import { footprintGrid } from "../lib/continent.js";

const props = defineProps({
  footprint: { type: Object, required: true },
  settlementId: { type: String, required: true },
});
const emit = defineEmits(["toggle"]);
const grid = computed(() => footprintGrid(props.footprint));
const cursor = ref(null);
const root = ref(null);

const current = computed(() => {
  const g = grid.value;
  if (!g) return null;
  const c = cursor.value;
  if (c && c.x >= g.west && c.x <= g.east && c.y >= g.south && c.y <= g.north) return c;
  const [x, y] = props.footprint.origin;
  return { x, y };
});

function isCurrent(cell) {
  return current.value && cell.x === current.value.x && cell.y === current.value.y;
}

const MOVES = { ArrowUp: [0, 1], ArrowDown: [0, -1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };

async function onKeydown(event) {
  const g = grid.value;
  if (!g || event.ctrlKey || event.metaKey || event.altKey) return;
  const move = MOVES[event.key];
  if (move) {
    event.preventDefault();
    event.stopPropagation();
    const x = Math.min(g.east, Math.max(g.west, current.value.x + move[0]));
    const y = Math.min(g.north, Math.max(g.south, current.value.y + move[1]));
    cursor.value = { x, y };
    await nextTick();
    root.value?.querySelector("[data-footprint-cell][tabindex='0']")?.focus();
    return;
  }
  if (event.key === " " || event.key === "Enter") {
    event.preventDefault();
    event.stopPropagation();
    toggle(current.value);
  }
}

function filledAt(cell) {
  return grid.value.rows.some((row) => row.cells.some((item) => item.x === cell.x && item.y === cell.y && item.filled));
}

function toggle(cell) {
  cursor.value = { x: cell.x, y: cell.y };
  emit("toggle", { cell: [cell.x, cell.y], filled: !filledAt(cell) });
}
</script>

<template>
  <div
    v-if="grid"
    ref="root"
    class="footprint-grid mono"
    role="grid"
    :aria-label="`${settlementId} 佔地遮罩（北在上，1 km 格）`"
    data-footprint-grid
    @keydown="onKeydown"
  >
    <div v-for="row in grid.rows" :key="row.y" class="footprint-grid__row" role="row">
      <span class="footprint-grid__axis" aria-hidden="true">{{ row.y }}</span>
      <button
        v-for="cell in row.cells"
        :key="`${cell.x},${cell.y}`"
        type="button"
        role="gridcell"
        class="footprint-grid__cell"
        :class="{ 'footprint-grid__cell--filled': cell.filled, 'footprint-grid__cell--current': isCurrent(cell) }"
        :tabindex="isCurrent(cell) ? 0 : -1"
        :aria-selected="cell.filled ? 'true' : 'false'"
        :aria-label="`格 (${cell.x}, ${cell.y}) ${cell.filled ? '佔地' : '非佔地'}`"
        :data-footprint-cell="`${cell.x},${cell.y}`"
        :data-filled="cell.filled ? 'true' : 'false'"
        @click="toggle(cell)"
      >
        {{ cell.filled ? "#" : "." }}
      </button>
    </div>
    <p class="footprint-grid__legend">欄 {{ grid.west }}–{{ grid.east }} · 列 {{ grid.south }}–{{ grid.north }}（1 km 格）· 方向鍵移動 · 空白鍵切換</p>
  </div>
</template>
