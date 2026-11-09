<script setup>
// CodexEmblem (prototype): one stroked emblem per codex category and per title
// category, in the dock-icons.js 24-unit stroke style. It is the tile face for
// art-less categories, the medal face, the rail glyph, and the hero fallback
// while art is pending or failed. The real component would add these paths to
// dock-icons.js.
import { computed } from "vue";

const EMBLEMS = {
  // Codex categories
  monster: "M4 20c1-6 3-9 6-11M9 20c1-5 3-8 6-10M14 20c1-4 3-6 6-8M6 4l2 3M11 3l1 3.5M16 4l-1 3",
  race: "M12 3.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM5 20.5c.6-4.5 3.4-7 7-7s6.4 2.5 7 7M3 10.5l2.5 1M21 10.5l-2.5 1",
  nation: "M4 20.5h16M5.5 20.5V11l3-2 3 2V7l3-3 3 3v4l1.5 1v8.5M14.5 4V1.8l3 1-3 1M9 20.5v-3.5h3v3.5",
  region: "M2.5 19.5 8.5 9l3.5 6 2.5-4 7 8.5zM8.5 9l1.8 3.2M15.5 6.5a1.6 1.6 0 1 0 0-.1",
  anchor: "M12 21s-6.5-6.4-6.5-11.2A6.5 6.5 0 0 1 18.5 9.8C18.5 14.6 12 21 12 21zM12 7a2.8 2.8 0 1 0 0 5.6A2.8 2.8 0 0 0 12 7z",
  element: "M12 2.8c2.5 3.5 5.5 6.3 5.5 10.2a5.5 5.5 0 0 1-11 0c0-2 1-3.6 2.2-4.8.2 1.8 1 2.8 2.1 3.2C10.3 8.6 10.8 5.6 12 2.8z",
  magic: "M12 2.5 14 9.6 21 12l-7 2.4-2 7.1-2-7.1L3 12l7-2.4zM18.5 3.5l.8 1.7 1.7.8-1.7.8-.8 1.7-.8-1.7-1.7-.8 1.7-.8z",
  guild: "M12 2.8 4.5 5.6v6c0 4.8 3.2 8 7.5 9.6 4.3-1.6 7.5-4.8 7.5-9.6v-6zM8 11h8M12 7v10M9.5 14.5h5",
  // Title categories
  combat: "M4.5 4.5 15 15M15 15l1.5-.5L19.5 17.5l-2 2L14.5 16.5zM19.5 4.5 9 15M9 15l-1.5-.5-3 3 2 2 3-3z",
  spell: "M12 2.5 14 9.6 21 12l-7 2.4-2 7.1-2-7.1L3 12l7-2.4z",
  explore: "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM15.5 8.5l-2 5-5 2 2-5zM12 3v2M12 19v2M3 12h2M19 12h2",
  clergy: "M12 3v18M7 8h10M12 3a2 2 0 0 0 0 0M8.5 21h7M5.5 12.5c2 1.5 4.2 2.2 6.5 2.2s4.5-.7 6.5-2.2",
  romance: "M12 20.5s-7.5-4.6-7.5-10.1A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.8c0 5.5-7.5 10.1-7.5 10.1zM12 7.6V4M10 3.5h4",
  epithet: "M19.5 3.5C13 4 8.5 8.6 7.2 15.3L6 19l3.6-1.3C16 16.2 20 11.5 20.5 4.5ZM7.2 15.3 13.5 9M4 21h9",
  ballot: "M4 6h16v13H4zM4 6l8 6.5L20 6M8 3h8",
  unknown: "M9.2 9a2.8 2.8 0 1 1 4.1 2.5c-.8.4-1.3 1.2-1.3 2.1v.6M12 17.2v.3",
};

const props = defineProps({
  name: { type: String, required: true },
  strokeWidth: { type: Number, default: 1.6 },
});

const d = computed(() => EMBLEMS[props.name] ?? EMBLEMS.unknown);
</script>

<template>
  <svg class="codex-emblem" viewBox="0 0 24 24" fill="none" aria-hidden="true">
    <path :d="d" stroke="currentColor" :stroke-width="strokeWidth" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
</template>

<style scoped>
.codex-emblem {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
