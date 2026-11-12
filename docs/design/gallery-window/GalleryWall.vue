<script setup>
// GalleryWall (Design/GalleryWindow prototype): the subject wall of the
// gallery window. Subjects are aspect-true tiles (9:16 portraits, 16:9
// scenes). Selecting a subject that may hold several images opens a tray
// directly under that subject's row, listing its images at the same tile
// size; a subject capped at one image selects that image without a tray.
// Group headings appear only when a group carries a label; a heading may
// count the subjects seen out of the group's total, and unseen subjects get
// no tile. Reference only.
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

const props = defineProps({
  // [{ key, label | null, discovered?, total?, slots: [subject] }]
  groups: { type: Array, required: true },
  subjectKey: { type: String, default: null },
  imageId: { type: String, default: null },
  // "portrait" | "landscape"
  shape: { type: String, default: "portrait" },
  ariaLabel: { type: String, required: true },
});
const emit = defineEmits(["select-subject", "select-image", "generate"]);

const root = ref(null);
const cols = ref(5);
let observer = null;
function measure() {
  const el = root.value;
  if (!el) return;
  const style = getComputedStyle(el);
  const scale = parseFloat(style.getPropertyValue("--ui-scale")) || 1;
  const min = (props.shape === "landscape" ? 168 : 92) * scale;
  const gap = 8 * scale;
  const width = el.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
  cols.value = Math.max(2, Math.floor((width + gap) / (min + gap)));
}
onMounted(() => {
  measure();
  observer = new ResizeObserver(measure);
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());

const hasTray = (subject) => subject.maxCards !== 1;

// The tray sits after the last tile of the open subject's row.
function trayIndex(group) {
  const open = group.slots.findIndex((slot) => slot.key === props.subjectKey && hasTray(slot));
  if (open < 0) return -1;
  return Math.min(group.slots.length - 1, (Math.floor(open / cols.value) + 1) * cols.value - 1);
}
const openColumn = (group) =>
  group.slots.findIndex((slot) => slot.key === props.subjectKey) % cols.value;
const openSubject = computed(() =>
  props.groups.flatMap((group) => group.slots).find((slot) => slot.key === props.subjectKey) ?? null,
);

const STATUS_TEXT = { pending: "生成中", failed: "生成失敗" };
function imageLabel(image, index) {
  const parts = [`第 ${index + 1} 張`, image.label];
  if (image.isDefault) parts.push("目前預設");
  return parts.join("，");
}
</script>

<template>
  <div ref="root" class="gwall" :class="`gwall--${shape}`" :style="{ '--gwall-cols': cols }" role="tabpanel" :aria-label="ariaLabel">
    <section v-for="group in groups" :key="group.key" class="gwall__group" :aria-label="group.label || ariaLabel">
      <h4 v-if="group.label" class="gwall__head">
        <span>{{ group.label }}</span>
        <span class="gwall__rule" aria-hidden="true"></span>
        <span v-if="group.total" class="gwall__n"><b>{{ group.discovered }}</b> / {{ group.total }}</span>
      </h4>
      <div class="gwall__grid">
        <template v-for="(slot, index) in group.slots" :key="slot.key">
          <button
            type="button"
            class="gtile"
            :class="{ 'is-selected': slot.key === subjectKey, 'is-open': slot.key === subjectKey && hasTray(slot) }"
            :aria-pressed="String(slot.key === subjectKey)"
            :aria-expanded="hasTray(slot) ? String(slot.key === subjectKey) : undefined"
            :aria-label="`${slot.name}${slot.current ? '，操作中' : ''}${hasTray(slot) ? `，${slot.cards.length} 張圖` : ''}`"
            @click="emit('select-subject', slot.key)"
          >
            <img v-if="slot.cards.length || slot.kind === 'scene'" class="gtile__art" :src="slot.art" alt="" />
            <span v-else class="gtile__blank" aria-hidden="true">尚無圖片</span>
            <span v-if="slot.current" class="gtile__current">操作中</span>
            <span v-if="hasTray(slot)" class="gtile__count" aria-hidden="true">{{ slot.cards.length }}</span>
            <span class="gtile__name">{{ slot.name }}</span>
          </button>

          <div
            v-if="index === trayIndex(group)"
            class="gtray"
            :style="{ '--gtray-col': openColumn(group) }"
            role="group"
            :aria-label="`${openSubject.name}的圖片`"
          >
            <span class="gtray__notch" aria-hidden="true"></span>
            <div class="gwall__grid">
              <button
                v-for="(image, n) in openSubject.cards"
                :key="image.id"
                type="button"
                class="gtile gtile--image"
                :class="{ 'is-selected': image.id === imageId, [`is-${image.status}`]: true }"
                :aria-pressed="String(image.id === imageId)"
                :aria-label="imageLabel(image, n)"
                @click="emit('select-image', image.id)"
              >
                <img v-if="image.status === 'card'" class="gtile__art" :src="image.url" alt="" />
                <span v-else class="gtile__status" :data-status="image.status">
                  <svg v-if="image.status === 'pending'" class="gtile__spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M12 3a9 9 0 1 0 9 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M12 4 21 20H3zM12 10v5M12 17.5v.5" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
                  </svg>
                  {{ STATUS_TEXT[image.status] }}
                </span>
                <span v-if="image.isDefault" class="gtile__crown">
                  <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5z" /></svg>預設
                </span>
              </button>
              <button type="button" class="gtile gtile--new" @click="emit('generate')">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
                生成新圖
              </button>
            </div>
            <template v-if="openSubject.official.length">
              <h5 class="gtray__label">官方圖片<small>唯讀</small></h5>
              <div class="gwall__grid">
                <button
                  v-for="image in openSubject.official"
                  :key="image.id"
                  type="button"
                  class="gtile gtile--image gtile--official"
                  :class="{ 'is-selected': image.id === imageId }"
                  :aria-pressed="String(image.id === imageId)"
                  :aria-label="image.label"
                  @click="emit('select-image', image.id)"
                >
                  <img class="gtile__art" :src="image.url" alt="" />
                </button>
              </div>
            </template>
          </div>
        </template>
      </div>
    </section>
  </div>
</template>

<style scoped>
.gwall {
  --gwall-gap: calc(8px * var(--ui-scale));
  --gwall-pad: var(--sp-4);
  --gwall-ratio: 9 / 16;
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  padding: var(--gwall-pad);
  background: #15171c;
  border-right: 1px solid rgba(185, 154, 96, 0.28);
  scrollbar-width: thin;
  scrollbar-color: var(--ink-600) transparent;
  /* The gutter is always reserved, so a wall that grows past one page never
     reflows its tiles when the scrollbar appears. */
  scrollbar-gutter: stable;
}

.gwall--landscape {
  --gwall-ratio: 16 / 9;
}

.gwall__head {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  margin: 0 0 var(--sp-2);
  color: var(--gold-400);
  font: var(--text-md) var(--f-display);
  letter-spacing: 0.12em;
}

.gwall__rule {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.28), transparent);
}

.gwall__n {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  letter-spacing: 0;
}

.gwall__n b {
  color: var(--gold-300);
  font-size: var(--text-md);
  font-weight: 500;
}

.gwall__grid {
  display: grid;
  grid-template-columns: repeat(var(--gwall-cols), minmax(0, 1fr));
  gap: var(--gwall-gap);
}

.gtile {
  position: relative;
  display: grid;
  aspect-ratio: var(--gwall-ratio);
  min-width: 0;
  padding: 0;
  overflow: hidden;
  color: var(--paper-200);
  font: inherit;
  background: radial-gradient(circle at 50% 30%, #3d3526, #15130f 72%);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.5);
  cursor: pointer;
  transition: border-color var(--motion-fast) ease;
}

.gtile:hover {
  border-color: var(--gold-400);
}

.gtile:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.gtile.is-selected {
  border-color: var(--seal-400);
  box-shadow: inset 0 0 0 1px var(--seal-500), 0 0 14px var(--seal-glow);
}

/* The open subject joins its tray: the same seal wash, no glow. */
.gtile.is-open {
  box-shadow: inset 0 0 0 1px var(--seal-500);
}

.gtile__art {
  grid-area: 1 / 1;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 50% 0;
}

.gtile__blank {
  grid-area: 1 / 1;
  place-self: center;
  color: var(--paper-500);
  font-size: var(--text-xs);
}

.gtile__name {
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

.gtile__count {
  position: absolute;
  top: var(--sp-1);
  right: var(--sp-1);
  min-width: calc(18px * var(--ui-scale));
  padding: 0 var(--sp-1);
  color: var(--gold-300);
  font: var(--text-xs) / 1.5 var(--f-num);
  text-align: center;
  background: rgba(8, 9, 11, 0.82);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
}

.gtile__current {
  position: absolute;
  top: var(--sp-1);
  left: 0;
  padding: 1px var(--sp-2) 1px var(--sp-1);
  color: var(--paper-50);
  font: var(--text-xs) var(--f-display);
  background: linear-gradient(180deg, var(--seal-600), var(--seal-700));
  clip-path: polygon(0 0, 100% 0, calc(100% - 6px) 50%, 100% 100%, 0 100%);
}

.gtile__crown {
  position: absolute;
  top: var(--sp-1);
  left: var(--sp-1);
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0 var(--sp-1);
  color: var(--gold-300);
  font: var(--text-xs) / 1.5 var(--f-display);
  background: rgba(8, 9, 11, 0.82);
  border: 1px solid var(--gold-500);
  border-radius: var(--radius-sm);
}

.gtile__crown svg {
  width: calc(12px * var(--ui-scale));
  height: calc(12px * var(--ui-scale));
}

.gtile__status {
  grid-area: 1 / 1;
  place-self: center;
  display: grid;
  justify-items: center;
  gap: var(--sp-1);
  color: var(--paper-400);
  font-size: var(--text-xs);
}

.gtile__status[data-status="failed"] {
  color: var(--seal-300, #e08a8a);
}

.gtile__status svg {
  width: calc(26px * var(--ui-scale));
  height: calc(26px * var(--ui-scale));
}

.gtile__spin {
  animation: gtile-spin 1.2s linear infinite;
}

@keyframes gtile-spin {
  to {
    transform: rotate(360deg);
  }
}

.gtile.is-failed {
  background: radial-gradient(circle at 50% 40%, #3a1f20, #15100f 72%);
  border-color: var(--seal-600);
}

.gtile--new {
  place-items: center;
  align-content: center;
  gap: var(--sp-1);
  color: var(--paper-400);
  font-size: var(--text-xs);
  background: none;
  border: 1px dashed var(--gold-600);
  box-shadow: none;
}

.gtile--new:hover {
  color: var(--gold-300);
}

.gtile--new svg {
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
}

/* The tray bleeds into the wall padding by its own padding, so its tiles
   keep exactly the subject tiles' column width. */
.gtray {
  --gtray-pad: var(--sp-2);
  position: relative;
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  margin: calc(4px * var(--ui-scale)) calc(-1 * var(--gtray-pad)) var(--sp-2);
  padding: var(--gtray-pad);
  background: linear-gradient(180deg, rgba(169, 50, 42, 0.2), rgba(169, 50, 42, 0.08));
  border: 1px solid var(--seal-600);
  border-radius: var(--radius-sm);
  box-shadow: inset 0 0 24px rgba(0, 0, 0, 0.45);
  animation: gtray-in var(--motion-reveal) ease-out;
}

@keyframes gtray-in {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
}

/* A notch under the open subject ties the tray to its owner. */
.gtray__notch {
  --col-w: calc((100% - 2 * var(--gtray-pad) - (var(--gwall-cols) - 1) * var(--gwall-gap)) / var(--gwall-cols));
  position: absolute;
  top: calc(-7px * var(--ui-scale));
  left: calc(var(--gtray-pad) + var(--gtray-col) * (var(--col-w) + var(--gwall-gap)) + var(--col-w) / 2);
  width: calc(12px * var(--ui-scale));
  height: calc(12px * var(--ui-scale));
  background: #2b1717;
  border-top: 1px solid var(--seal-600);
  border-left: 1px solid var(--seal-600);
  transform: translateX(-50%) rotate(45deg);
}

.gtray__label {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  margin: var(--sp-1) 0 0;
  color: var(--paper-300);
  font: var(--text-xs) var(--f-display);
  letter-spacing: 0.2em;
}

.gtray__label small {
  color: var(--paper-500);
  font-size: var(--text-xs);
  letter-spacing: 0;
}

.gtile--official {
  border-style: double;
  border-width: 3px;
}

@media (prefers-reduced-motion: reduce) {
  .gtile,
  .gtray {
    transition: none;
    animation: none;
  }

  .gtile__spin {
    animation: none;
  }
}
</style>
