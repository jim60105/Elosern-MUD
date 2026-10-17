<script setup>
// Approved visual prototype (party member management): the MemberRail
// primitive. Commander first, then companions in party order; no "you"
// marker; ▼倒地 is shape plus text; the dot is the session unread-unlock
// flag; 空位 ends the rail on the 成員 tab while a slot is free.
import PmGlyph from "./PmGlyph.vue";

defineProps({
  members: { type: Array, required: true },
  selected: { type: [Number, String], default: null },
  unread: { type: Set, default: () => new Set() },
  showEmpty: { type: Boolean, default: false },
});
const emit = defineEmits(["select"]);
</script>

<template>
  <nav class="pm-rail" role="tablist" aria-orientation="vertical" aria-label="隊伍成員">
    <button
      v-for="m in members"
      :key="m.id"
      type="button"
      role="tab"
      class="pm-rail__tab"
      :class="{ 'is-active': selected === m.id, 'pm-rail__ko-dim': m.knocked_out }"
      :aria-selected="selected === m.id"
      @click="emit('select', m.id)"
    >
      <span class="pm-avatar">{{ m.initial }}</span>
      {{ m.name }}
      <span v-if="m.knocked_out" class="pm-rail__ko"><PmGlyph name="knocked_out" />倒地</span>
      <span v-if="unread.has(m.id)" class="pm-rail__dot" aria-label="有新解鎖的技能" />
    </button>
    <button
      v-if="showEmpty"
      type="button"
      role="tab"
      class="pm-rail__tab pm-rail__tab--empty"
      :class="{ 'is-active': selected === 'empty' }"
      :aria-selected="selected === 'empty'"
      @click="emit('select', 'empty')"
    >
      <span class="pm-avatar"><PmGlyph name="plus" /></span>
      空位
    </button>
  </nav>
</template>
