<script setup>
// CodexMedalGrid (handbook-titles-tab, design D7): the titles tab's medal
// wall over the shared roving-focus TileWall (variant "medal"), after the
// approved prototype's `.hb-medal` (docs/design/handbook-codex-titles/
// TitlesTabProto.vue). An unlocked medal's face is the guild grade gem when
// the row has a grade, else its category emblem; a locked medal keeps its
// name but draws a dashed silhouette with a lock. The equipped medal carries
// a ★ badge. TileWall owns the option cell (role, roving tabindex,
// aria-selected, `data-tile`); the face inside it carries the
// `handbook__medal--<key>` testid and the locked marker.
import GradeGem from "../GradeGem.vue";
import CodexEmblem from "./CodexEmblem.vue";
import TileWall from "./TileWall.vue";

const props = defineProps({
  // medalItems() view models (title-codex-model.js).
  items: { type: Array, required: true },
  selectedId: { type: String, default: null },
  ariaLabel: { type: String, required: true },
});

const emit = defineEmits(["select"]);
</script>

<template>
  <TileWall
    class="codex-medal-grid"
    variant="medal"
    :groups="[{ key: 'medals', label: null, items: props.items }]"
    :selected-id="selectedId"
    :aria-label="ariaLabel"
    @select="(id) => emit('select', id)"
  >
    <template #tile="{ item, selected }">
      <div
        class="codex-medal"
        :class="{ 'is-selected': selected, 'is-locked': item.locked }"
        :data-testid="`handbook__medal--${item.id}`"
        :data-locked="item.locked ? 'true' : 'false'"
      >
        <span class="codex-medal__disc">
          <template v-if="!item.locked">
            <GradeGem v-if="item.grade" :grade="item.grade" size="md" />
            <span v-else class="codex-medal__emblem"><CodexEmblem :name="item.row.category" :stroke-width="1.4" /></span>
          </template>
          <svg v-else class="codex-medal__lock" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M8 11V8a4 4 0 0 1 8 0v3M5.5 11h13v9.5h-13zM12 14.5v2.5" stroke="currentColor" stroke-width="1.6" />
          </svg>
          <span v-if="item.equipped" class="codex-medal__eq" aria-hidden="true">★</span>
        </span>
        <span class="codex-medal__name">{{ item.row.display }}</span>
      </div>
    </template>
  </TileWall>
</template>

<style scoped>
/* Copied from the prototype's `.hb-medal` family. */
.codex-medal {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-2) 0;
  border-radius: var(--radius-sm);
}

.codex-medal.is-selected {
  background: linear-gradient(180deg, rgba(169, 50, 42, 0.26), transparent);
}

.codex-medal__disc {
  position: relative;
  display: grid;
  place-items: center;
  width: calc(60px * var(--ui-scale));
  height: calc(60px * var(--ui-scale));
  border-radius: 50%;
  background: radial-gradient(circle at 40% 35%, #5c4c2c, #1a160f 70%);
  border: 2px solid var(--gold-500);
  box-shadow: 0 0 0 3px #15171c, 0 0 0 4px var(--gold-600);
  transition: box-shadow var(--motion-fast) ease;
}

.codex-medal.is-selected .codex-medal__disc {
  box-shadow: 0 0 0 3px #15171c, 0 0 0 5px var(--seal-400), 0 0 16px var(--seal-glow);
}

.codex-medal__emblem {
  width: 56%;
  height: 56%;
  color: var(--gold-300);
}

.codex-medal.is-locked .codex-medal__disc {
  background: repeating-linear-gradient(45deg, #121418 0 5px, #17191e 5px 10px);
  border: 2px dashed var(--ink-600);
  box-shadow: none;
}

.codex-medal.is-locked.is-selected .codex-medal__disc {
  box-shadow: 0 0 0 3px #15171c, 0 0 0 5px var(--seal-400);
}

.codex-medal__lock {
  width: 40%;
  height: 40%;
  color: var(--paper-700);
}

.codex-medal__eq {
  position: absolute;
  right: -4px;
  bottom: -4px;
  display: grid;
  place-items: center;
  width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
  color: var(--ink-950);
  font-size: var(--text-xs);
  background: var(--gold-400);
  border: 2px solid #15171c;
  border-radius: 50%;
}

.codex-medal__name {
  max-width: 100%;
  overflow: hidden;
  color: var(--paper-100);
  font: var(--text-xs) / 1.3 var(--f-serif);
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.codex-medal.is-locked .codex-medal__name {
  color: var(--paper-500);
}

@media (prefers-reduced-motion: reduce) {
  .codex-medal__disc {
    transition: none;
  }
}
</style>
