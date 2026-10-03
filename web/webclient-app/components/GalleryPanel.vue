<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import GalleryDetailRail from "./GalleryDetailRail.vue";
import GalleryGenerateDrawer from "./GalleryGenerateDrawer.vue";
import GalleryBindingDrawer from "./GalleryBindingDrawer.vue";
import GalleryFaceRectModal from "./GalleryFaceRectModal.vue";
import GalleryStageTransformModal from "./GalleryStageTransformModal.vue";
import { GALLERY_FILTERS, galleryCardName, galleryDate } from "./gallery-copy.js";
import { faceObjectPosition } from "./face-rect.js";
import "./gallery.css";

const props = defineProps({
  model: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
  dispatch: { type: Function, default: null },
  result: { type: Object, default: null },
  revision: { type: Number, default: 0 },
});
const emit = defineEmits(["character", "log"]);
const root = ref(null);
const filter = ref("all");
const layout = ref("grid");
const selected = ref(null);
const editor = ref(null);
const pending = ref(null);
const rejected = ref(false);
let opener = null;
// The minute clock for the cards' relative dates: it ticks only while the
// gallery is mounted (open) and stops with it.
const now = ref(Date.now());
let clock = null;
onMounted(() => {
  now.value = Date.now();
  clock = setInterval(() => { now.value = Date.now(); }, 60_000);
});
onBeforeUnmount(() => clearInterval(clock));
const available = computed(() => props.model?.available === true);
const locked = computed(() => props.disabled || !available.value);
const cards = computed(() => available.value ? props.model.cards || [] : []);
const selectedCard = computed(() => cards.value.find((row) => row.image_id === selected.value) || null);
const cardDates = computed(() => new Map(cards.value.map((card) => [card.image_id, galleryDate(card.created_at, now.value)])));
const visibleCards = computed(() => cards.value.filter((card) => {
  if (filter.value === "all") return true;
  if (filter.value === "defaults") return card.is_default;
  if (filter.value === "bound") return card.binding_present;
  return card.status === filter.value;
}));
watch([() => props.model?.selected, available], () => {
  closeEditor();
  selected.value = cards.value[0]?.image_id ?? null;
  filter.value = "all";
}, { immediate: true });
watch(cards, () => {
  if (!selectedCard.value) {
    if (selected.value !== null) closeEditor();
    selected.value = cards.value[0]?.image_id ?? null;
  }
});
watch(() => [props.result, props.revision], () => {
  const request = pending.value;
  const result = props.result;
  if (!request || result?.requestId !== request.id) return;
  if (result.outcome !== "success") {
    pending.value = null;
    rejected.value = true;
  } else if (result.presentationRevision != null && props.revision >= result.presentationRevision) {
    pending.value = null;
    if (request.editor && request.editor === editor.value) closeEditor();
  }
});
function openEditor(name) {
  if (locked.value || pending.value || (name !== "generate" && selectedCard.value?.status !== "card")) return;
  opener = document.activeElement;
  rejected.value = false;
  editor.value = name;
}
function closeEditor() {
  if (!editor.value) return;
  editor.value = null;
  pending.value = null;
  rejected.value = false;
  const target = opener;
  void nextTick().then(() => {
    if (target?.isConnected) target.focus();
    else root.value?.querySelector("button:not(:disabled)")?.focus();
  });
}
function selectCard(id) {
  closeEditor();
  selected.value = id;
}
function send(action, extra = {}) {
  if (locked.value || pending.value || !props.dispatch) return;
  const isCard = !["gallery.generate", "gallery.subject.select"].includes(action);
  if (isCard && selectedCard.value?.status !== "card") return;
  const payload = { subject_key: props.model.selected, ...extra };
  if (isCard) payload.image_id = selectedCard.value.image_id;
  const id = props.dispatch(action, payload);
  if (id) {
    rejected.value = false;
    pending.value = { id, editor: editor.value };
  }
}
function selectSubject(subject) {
  if (!locked.value) send("gallery.subject.select", { subject_key: subject.subject_key });
}
</script>

<template>
  <section ref="root" class="gallery-ui gallery-panel" data-testid="gallery-panel">
    <p v-if="!available" class="gallery-note" role="status">{{ model?.reason?.message || '肖像圖庫目前無法使用。' }}</p>
    <template v-else>
      <div class="gallery-panel__workspace">
        <!-- The overlay host's shared header names the gallery and owns its
             close control; this row carries only the guidance and the
             primary action. -->
        <div class="gallery-panel__heading">
          <span class="gallery-muted">依裝備狀態管理切換，或手動指定預設圖。</span>
          <button class="gallery-primary" :disabled="locked" @click="openEditor('generate')">生成新圖</button>
        </div>
        <nav class="gallery-panel__subjects" aria-label="肖像圖庫角色">
          <button v-for="subject in model.subjects" :key="subject.subject_key" :aria-pressed="subject.subject_key === model.selected" :disabled="locked" @click="selectSubject(subject)">{{ subject.display_name }}</button>
        </nav>
        <div class="gallery-panel__toolbar">
          <div class="gallery-panel__filters" role="group" aria-label="肖像篩選">
            <button v-for="tab in GALLERY_FILTERS" :key="tab.id" :aria-pressed="filter === tab.id" @click="filter = tab.id">{{ tab.label }}<template v-if="model.filters?.[tab.id] !== undefined">（{{ model.filters[tab.id] }}）</template></button>
          </div>
          <span class="gallery-muted">最新優先</span>
          <div class="gallery-panel__view" role="group" aria-label="顯示方式">
            <button aria-label="網格檢視" :aria-pressed="layout === 'grid'" @click="layout = 'grid'">▦</button>
            <button aria-label="清單檢視" :aria-pressed="layout === 'list'" @click="layout = 'list'">☷</button>
          </div>
        </div>
        <div class="gallery-panel__cards" :class="{ 'gallery-panel__cards--list': layout === 'list' }">
          <button v-for="card in visibleCards" :key="card.image_id" class="gallery-card" :class="`gallery-card--${card.status}`" :aria-pressed="selected === card.image_id" :data-image-id="card.image_id" @click="selectCard(card.image_id)">
            <div class="gallery-card__visual">
              <img v-if="card.status === 'card' && card.url" :src="card.url" :alt="galleryCardName(card)" :style="{ objectPosition: faceObjectPosition(card.face_rect) }">
              <span v-else-if="card.status === 'pending'" class="gallery-card__spinner" aria-hidden="true"></span>
              <span v-else-if="card.status === 'failed'" class="gallery-card__failure" aria-hidden="true">△</span>
              <span v-if="card.is_default" class="gallery-card__crown">♛ 目前預設</span>
              <div class="gallery-chips"><span v-for="chip in card.chips" :key="chip" class="gallery-chip">{{ chip }}</span></div>
            </div>
            <div class="gallery-card__caption">
              <strong>{{ card.label }}</strong>
              <time class="gallery-muted gallery-card__date" :datetime="cardDates.get(card.image_id)?.iso" :title="cardDates.get(card.image_id)?.exact">{{ cardDates.get(card.image_id)?.relative }}<span v-if="cardDates.get(card.image_id)?.exact" class="gallery-visually-hidden">（{{ cardDates.get(card.image_id).exact }}）</span></time>
            </div>
          </button>
        </div>
        <p v-if="!visibleCards.length" class="gallery-panel__empty">此分類尚無肖像。選擇「生成新圖」，記錄角色的模樣。</p>
        <p v-if="rejected && !editor" class="gallery-feedback" role="status">操作未完成。<button @click="emit('log')">查看伺服器訊息</button></p>
      </div>
      <GalleryDetailRail :card="selectedCard" :now="now" :capabilities="model.capabilities" :warnings="model.binding_warnings" :disabled="locked"
        @default="send('gallery.default.set')" @delete="send('gallery.card.delete')"
        @generate="openEditor('generate')" @binding="openEditor('binding')" @face="openEditor('face')" @stage="openEditor('stage')" />
      <Teleport to="body">
        <GalleryGenerateDrawer v-if="editor === 'generate'" :model="model" :preview="selectedCard" :disabled="locked" :rejected="rejected"
          @close="closeEditor" @submit="send('gallery.generate', $event)" @character="emit('character')" @log="emit('log')" />
        <GalleryBindingDrawer v-if="editor === 'binding' && selectedCard" :model="model" :card="selectedCard" :disabled="locked" :rejected="rejected"
          @close="closeEditor" @submit="send('gallery.binding.save', $event)" @select-card="selectCard" @log="emit('log')" />
        <GalleryFaceRectModal v-if="editor === 'face' && selectedCard" :card="selectedCard" :disabled="locked" :rejected="rejected"
          @close="closeEditor" @submit="send('gallery.face_rect.update', $event)" @log="emit('log')" />
        <GalleryStageTransformModal v-if="editor === 'stage' && selectedCard?.status === 'card'" :card="selectedCard" :disabled="locked || !!pending" :rejected="rejected"
          @close="closeEditor" @submit="send('gallery.stage.update', $event)" @log="emit('log')" />
      </Teleport>
    </template>
  </section>
</template>

<style scoped>
.gallery-panel { display: grid; grid-template-columns: minmax(0, 1fr) calc(290px * var(--ui-scale)); min-height: 100%; background: linear-gradient(115deg, #191a21, #101119 60%); }
.gallery-panel__workspace { min-width: 0; padding: calc(22px * var(--ui-scale)); }
.gallery-panel__heading { display: flex; align-items: center; justify-content: space-between; gap: calc(18px * var(--ui-scale)); margin-bottom: calc(18px * var(--ui-scale)); }
.gallery-panel__heading .gallery-muted { font-size: var(--text-md); }
.gallery-panel__heading > button { min-width: calc(140px * var(--ui-scale)); min-height: calc(44px * var(--ui-scale)); font-size: var(--text-lg); letter-spacing: .06em; }
.gallery-panel__subjects { display: flex; flex-wrap: wrap; gap: calc(7px * var(--ui-scale)); margin: 0 0 calc(18px * var(--ui-scale)); }
.gallery-panel__subjects button { padding: calc(5px * var(--ui-scale)) calc(11px * var(--ui-scale)); font-size: var(--text-xs); border-radius: var(--radius); }
.gallery-panel__toolbar { display: flex; align-items: center; gap: calc(12px * var(--ui-scale)); margin-bottom: calc(14px * var(--ui-scale)); flex-wrap: wrap; }
.gallery-panel__filters { display: flex; flex-wrap: wrap; flex: 1; }
.gallery-panel__filters button { padding: calc(8px * var(--ui-scale)) calc(10px * var(--ui-scale)); font-size: var(--text-xs); border-radius: 0; }
.gallery-panel button[aria-pressed="true"] { border-color: #d2b56e; color: #ecd596; background-color: #6d522526; box-shadow: inset 0 0 0 1px #d2b56e25; }
.gallery-panel__view { display: flex; }
.gallery-panel__view button { padding: calc(3px * var(--ui-scale)) calc(9px * var(--ui-scale)); font-size: var(--text-xl); }
.gallery-panel__cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: calc(15px * var(--ui-scale)); }
.gallery-panel .gallery-card { display: flex; flex-direction: column; padding: calc(4px * var(--ui-scale)); min-width: 0; text-align: left; overflow: hidden; background: #14151c; border: 1px solid #6e6a665e; border-radius: var(--radius); }
.gallery-panel .gallery-card[aria-pressed="true"] { box-shadow: 0 0 calc(12px * var(--ui-scale)) #c6a96240, inset 0 0 0 1px #d2b56e55; }
.gallery-card__visual { position: relative; width: 100%; height: clamp(150px * var(--ui-scale), 20vh, 215px * var(--ui-scale)); background: radial-gradient(ellipse at top, #2b2c3d, #11131b); display: grid; place-items: center; border-radius: var(--radius-sm); overflow: hidden; }
.gallery-card__visual > img { width: 100%; height: 100%; object-fit: cover; position: absolute; }
.gallery-card__visual .gallery-chips { position: absolute; bottom: calc(6px * var(--ui-scale)); left: calc(5px * var(--ui-scale)); right: calc(5px * var(--ui-scale)); }
.gallery-card__crown { position: absolute; top: calc(5px * var(--ui-scale)); left: calc(5px * var(--ui-scale)); padding: calc(3px * var(--ui-scale)) calc(7px * var(--ui-scale)); background: #221c0fe8; border: 1px solid #cfb16b; color: #e5c982; border-radius: var(--radius); font-size: var(--text-xs); }
.gallery-card__caption { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: calc(4px * var(--ui-scale)) calc(10px * var(--ui-scale)); padding: calc(9px * var(--ui-scale)) calc(6px * var(--ui-scale)); overflow-wrap: anywhere; }
.gallery-card__date { white-space: nowrap; font-variant-numeric: tabular-nums lining-nums; }
.gallery-card__caption strong { font-size: var(--text-sm); font-weight: 500; }
.gallery-card__caption .gallery-muted { font-size: var(--text-xs); }
.gallery-card__spinner { width: calc(42px * var(--ui-scale)); height: calc(42px * var(--ui-scale)); border: calc(4px * var(--ui-scale)) solid #596fd82b; border-top-color: #8499ef; border-radius: 50%; animation: gallery-spin var(--motion-spin) linear infinite; }
.gallery-card__failure { color: #ed7e82; font-size: var(--text-initial); }
.gallery-card--failed .gallery-card__visual { background: radial-gradient(ellipse at top, #40242c, #18151d); }
.gallery-card--failed strong { color: #f29699; }
.gallery-panel__empty { padding: calc(60px * var(--ui-scale)) calc(20px * var(--ui-scale)); text-align: center; color: var(--paper-500); border: 1px dashed #a5967755; }
.gallery-panel__cards--list { grid-template-columns: 1fr; }
.gallery-panel__cards--list .gallery-card { flex-direction: row; gap: calc(14px * var(--ui-scale)); }
.gallery-panel__cards--list .gallery-card__visual { width: calc(100px * var(--ui-scale)); height: calc(100px * var(--ui-scale)); flex: none; }
.gallery-panel__cards--list .gallery-card__caption { justify-content: center; }
@keyframes gallery-spin { to { transform: rotate(360deg); } }
@media (max-width: 1250px) { .gallery-panel__cards { grid-template-columns: repeat(3, minmax(0, 1fr)); } .gallery-panel__cards--list { grid-template-columns: 1fr; } .gallery-panel { grid-template-columns: minmax(0, 1fr) calc(245px * var(--ui-scale)); } }
@media (max-width: 850px) { .gallery-panel { grid-template-columns: 1fr; } .gallery-panel__cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } .gallery-panel__cards--list { grid-template-columns: 1fr; } }
</style>
