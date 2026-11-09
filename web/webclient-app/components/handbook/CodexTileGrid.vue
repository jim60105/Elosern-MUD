<script setup>
// CodexTileGrid (handbook-codex-tab, design D4): the codex tab's wall column
// over the shared roving-focus TileWall (variant "tile"), after the approved
// prototype's `.hb-wall` and `.hb-tile` (docs/design/handbook-codex-titles/
// CodexTabProto.vue). The column is the wall's own scroller: the head, the
// grouped tiles, and — on the monster wall only — the stage legend as its
// last child, pinned to the bottom edge while the tiles scroll.
//
// A tile face is one of three: an entry (its art or emblem, the title caption
// and, for a researched monster, a filled or hollow diamond stage mark), or a
// placeholder (a hatched dashed tile marked ？). The marks differ by shape,
// not only colour. TileWall owns the option cell (role, roving tabindex,
// aria-selected, aria-disabled, `data-tile`); the face inside it carries the
// `handbook__tile--<id>` testid.
import CodexArt from "./CodexArt.vue";
import TileWall from "./TileWall.vue";

defineProps({
  // codexGroups() view models (lore-codex-model.js).
  groups: { type: Array, required: true },
  selectedId: { type: String, default: null },
  // The category key (the emblem of art-less tiles).
  category: { type: String, default: null },
  heading: { type: String, default: "" },
  discovered: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  // Whether this is the monster wall (it carries the stage legend).
  legend: { type: Boolean, default: false },
  // The committed panel the art descriptors came from.
  panel: { type: Object, default: null },
});

const emit = defineEmits(["select"]);

const DIAMOND = "M6 1 11 6 6 11 1 6Z";
</script>

<template>
  <div class="codex-wall" data-testid="handbook__codex-wall" role="tabpanel" :aria-label="heading">
    <header class="codex-wall__head">
      <span class="codex-wall__kicker">{{ heading }}</span>
      <span class="codex-wall__rule" aria-hidden="true"></span>
      <span class="codex-wall__n"><b>{{ discovered }}</b> / {{ total }}</span>
    </header>
    <TileWall
      variant="tile"
      :groups="groups"
      :selected-id="selectedId"
      :aria-label="`${heading}條目`"
      @select="(id) => emit('select', id)"
    >
      <template #tile="{ item, selected }">
        <div
          v-if="item.placeholder"
          class="codex-tile codex-tile--unknown"
          :data-testid="`handbook__tile--${item.id}`"
        >
          <span class="codex-tile__q" data-stage="unknown" aria-hidden="true">？</span>
        </div>
        <div
          v-else
          class="codex-tile"
          :class="{ 'is-selected': selected, 'is-sighted': item.stage === 'sighted' }"
          :data-testid="`handbook__tile--${item.id}`"
        >
          <CodexArt class="codex-tile__art" :art="item.art" :panel="panel" :emblem="category" variant="tile" />
          <span class="codex-tile__name">{{ item.title }}</span>
          <span v-if="item.stage" class="codex-tile__stage" :data-stage="item.stage" aria-hidden="true">
            <svg viewBox="0 0 12 12"><path :d="DIAMOND" :fill="item.stage === 'defeated' ? 'currentColor' : 'none'" /></svg>
          </span>
        </div>
      </template>
    </TileWall>
    <p v-if="legend" class="codex-wall__legend" data-testid="handbook__codex-legend" aria-hidden="true">
      <span class="codex-legend codex-legend--defeated">
        <svg class="codex-legend__mark" data-stage="defeated" viewBox="0 0 12 12"><path :d="DIAMOND" fill="currentColor" /></svg>已擊敗
      </span>
      <span class="codex-legend codex-legend--sighted">
        <svg class="codex-legend__mark" data-stage="sighted" viewBox="0 0 12 12"><path :d="DIAMOND" fill="none" /></svg>僅目擊
      </span>
      <span class="codex-legend codex-legend--unknown">
        <span class="codex-legend__mark codex-legend__q" data-stage="unknown">？</span>未記錄
      </span>
    </p>
  </div>
</template>

<style scoped>
/* Copied from the prototype's `.hb-wall`, `.hb-wall__legend`, `.hb-legend`
   (legend fix 08406a57: fixed 12px marks, sticky at the wall's bottom edge)
   and `.hb-tile` families. */
.codex-wall {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-4);
  background: #15171c;
  border-right: 1px solid rgba(185, 154, 96, 0.28);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
}

.codex-wall__head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

.codex-wall__kicker {
  color: var(--gold-400);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.12em;
}

.codex-wall__rule {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

.codex-wall__n {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.codex-wall__n b {
  color: var(--gold-300);
  font-size: var(--text-md);
  font-weight: 500;
}

/* The legend stays pinned to the wall's bottom edge while the tiles scroll,
   so the stage marks are always explained. */
.codex-wall__legend {
  position: sticky;
  bottom: calc(-1 * var(--sp-4));
  z-index: 1;
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-4);
  margin: auto calc(-1 * var(--sp-4)) calc(-1 * var(--sp-4));
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-400);
  font-size: var(--text-xs);
  background: #15171c;
  border-top: 1px solid rgba(185, 154, 96, 0.18);
  box-shadow: 0 -8px 12px -6px rgba(0, 0, 0, 0.6);
}

.codex-legend {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
}

.codex-legend__mark {
  display: block;
  flex: none;
  width: calc(12px * var(--ui-scale));
  height: calc(12px * var(--ui-scale));
}

.codex-legend__q {
  display: grid;
  place-items: center;
  color: var(--paper-700);
  font-size: var(--text-xs);
  line-height: 1;
}

.codex-tile {
  position: relative;
  display: grid;
  aspect-ratio: 1;
  overflow: hidden;
  background: radial-gradient(circle at 50% 38%, #3d3526, #15130f 72%);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.5);
  transition: border-color var(--motion-fast) ease;
}

.codex-tile:hover {
  border-color: var(--gold-400);
}

.codex-tile.is-selected {
  border-color: var(--seal-400);
  box-shadow: inset 0 0 0 1px var(--seal-500), 0 0 14px var(--seal-glow);
}

.codex-tile__art {
  grid-area: 1 / 1;
}

/* A sighted entry's art is desaturated: researched, not yet defeated. */
.codex-tile.is-sighted .codex-tile__art {
  filter: grayscale(1) brightness(0.8);
}

.codex-tile__name {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: var(--sp-4) var(--sp-1) var(--sp-1);
  overflow: hidden;
  color: var(--paper-50);
  font: var(--text-xs) / 1.3 var(--f-serif);
  text-align: center;
  white-space: nowrap;
  text-overflow: ellipsis;
  background: linear-gradient(180deg, transparent, rgba(8, 9, 11, 0.92) 60%);
}

.codex-tile__stage {
  position: absolute;
  top: var(--sp-1);
  right: var(--sp-1);
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
  filter: drop-shadow(0 1px 2px #000);
}

.codex-tile__stage svg {
  display: block;
  width: 100%;
  height: 100%;
}

/* Defeated: a filled gold diamond; sighted: a hollow one. Shape, not colour. */
.codex-tile__stage[data-stage="defeated"],
.codex-legend--defeated .codex-legend__mark {
  color: var(--gold-400);
}

.codex-tile__stage[data-stage="defeated"] path,
.codex-legend--defeated path {
  stroke: var(--ink-950);
  stroke-width: 1;
}

.codex-tile__stage[data-stage="sighted"] path,
.codex-legend--sighted path {
  stroke: var(--paper-300);
  stroke-width: 1.4;
}

.codex-tile--unknown {
  background: repeating-linear-gradient(45deg, #121418 0 6px, #17191e 6px 12px);
  border: 1px dashed var(--ink-600);
  box-shadow: none;
}

.codex-tile__q {
  grid-area: 1 / 1;
  place-self: center;
  color: var(--paper-700);
  font: var(--text-xl) var(--f-display);
}

@media (prefers-reduced-motion: reduce) {
  .codex-tile {
    transition: none;
  }
}
</style>
