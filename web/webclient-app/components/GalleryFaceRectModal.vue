<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ArtworkFailure from "./ArtworkFailure.vue";
import { createFocusTrap } from "./focus-trap.js";
import {
  clampFaceRect,
  defaultFaceRect,
  editFaceRectField,
  faceCropStyle,
  moveFaceRect,
  refitFaceRectOnLoad,
  resizeFaceRect,
} from "./face-rect-edit.js";
import { galleryCardName, galleryDate } from "./gallery-copy.js";
import { useImageAttempts } from "../composables/useImageAttempts.js";
import "./gallery.css";

const props = defineProps({
  card: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
  rejected: { type: Boolean, default: false },
});
const emit = defineEmits(["close", "submit", "log"]);
const rect = ref(props.card.face_rect ? clampFaceRect(props.card.face_rect) : defaultFaceRect());
const root = ref(null);
const image = ref(null);
let trap;
let drag = null;

// One rank-10 original resource request built from the exact committed card
// facts this editor already receives (change unified-image-loading-core). This
// is ordinary internal loading input for one existing exact original: no
// subject descriptor, no panel-version parsing, and no reader accepts a new
// shape — the gallery v2 serializer and its active validator stay unchanged.
// The later gallery-v3 cutover replaces this caller input with its backend
// descriptor; the same resource driver remains.
const request = computed(() => {
  const url = typeof props.card.url === "string" && props.card.url ? props.card.url : null;
  if (!url) return null;
  return {
    subjectId: url,
    epoch: props.card.image_id,
    attempts: [{
      type: "image",
      source_id: `gallery.original:${props.card.image_id}`,
      rank: 10,
      resource: {
        resource_id: url,
        version: props.card.image_id,
        url,
        origin: "runtime",
        geometry: {
          face_rect: props.card.face_rect ?? null,
          image_size: props.card.image_size ?? null,
        },
      },
    }],
    terminal: null,
  };
});
const availability = computed(() => ({ state: "ready", view_subject_id: props.card.image_id }));
const { attempt, phase, dimensions, reachedFaults, saveEligible, onImageLoad, onImageError, dispose } = useImageAttempts(request, availability);

const loaded = computed(() => phase.value === "success");
const imageUrl = computed(() => attempt.value?.url ?? null);
// The crop preview reuses the already observed successful resource; it is never
// a second original that can fail on its own.
const previewUrl = computed(() => (loaded.value ? imageUrl.value : null));
const failure = computed(() => reachedFaults.value[reachedFaults.value.length - 1] ?? null);
const failureKind = computed(() => (failure.value ? "failure" : null));
const failureReason = computed(() => failure.value?.reason ?? null);
const previewStyle = computed(() => {
  // By construction rect is pixel-square when loaded, so aspect ratio is 1:1
  return { width: "100%", height: "100%" };
});
const rectStyle = computed(() => ({
  left: `${rect.value.x * 100}%`, top: `${rect.value.y * 100}%`,
  width: `${rect.value.w * 100}%`, height: `${rect.value.h * 100}%`,
}));
// Seed the draft from the committed rectangle once per decoded original: a new
// exact original recovers, while an unchanged one keeps the player's edits.
let seededKey = null;
watch([phase, () => attempt.value?.key], ([value, key]) => {
  if (value !== "success" || key == null || key === seededKey) return;
  seededKey = key;
  const anchor = props.card.face_rect;
  if (!anchor || (anchor.x === 0.25 && anchor.y === 0.06 && anchor.w === 0.5 && anchor.h === 0.5)) {
    rect.value = defaultFaceRect(dimensions.value);
  } else {
    rect.value = refitFaceRectOnLoad(rect.value, dimensions.value);
  }
}, { immediate: true });
onMounted(() => {
  trap = createFocusTrap(root.value, { openerEl: document.activeElement });
  trap.enter();
});
onBeforeUnmount(() => { trap?.restore(); dispose(); });
function close() { emit("close"); }
function keydown(event) {
  event.stopPropagation();
  if (event.key === "Escape") { event.preventDefault(); close(); }
  else trap?.onKeydown(event);
}
function start(event, resize = false) {
  if (props.disabled || !loaded.value || event.button !== 0) return;
  const bounds = image.value.getBoundingClientRect();
  if (!bounds.width || !bounds.height) return;
  event.preventDefault();
  drag = { rect: { ...rect.value }, x: event.clientX, y: event.clientY, bounds, resize, pointerId: event.pointerId };
  event.currentTarget.setPointerCapture(event.pointerId);
}
function move(event) {
  if (!drag || drag.pointerId !== event.pointerId || props.disabled) return;
  const dx = (event.clientX - drag.x) / drag.bounds.width;
  const dy = (event.clientY - drag.y) / drag.bounds.height;
  rect.value = drag.resize ? resizeFaceRect(drag.rect, dx, dy, dimensions.value) : moveFaceRect(drag.rect, dx, dy);
}
function edit(field, event) {
  rect.value = editFaceRectField(rect.value, field, event.target.valueAsNumber, dimensions.value);
}
function submit() {
  if (!saveEligible.value || !dimensions.value) return;
  const finalRect = clampFaceRect(rect.value, dimensions.value);
  emit("submit", { face_rect: finalRect });
}
</script>

<template>
  <div class="gallery-face-scrim" @click.self="close">
    <section ref="root" class="gallery-ui gallery-face" role="dialog" aria-modal="true" aria-label="臉部框選" @keydown="keydown">
      <header class="gallery-face__head">
        <div><h2>臉部框選</h2><p class="gallery-muted">設定此角色在各處顯示時的頭像裁切範圍</p></div>
        <button aria-label="關閉臉部框選" @click="close">×</button>
      </header>
      <div class="gallery-face__body">
        <section>
          <h4>原始圖片<span class="gallery-muted">（可拖曳調整框選範圍）</span></h4>
          <div class="gallery-face__original">
            <img v-if="imageUrl" :key="attempt.key" ref="image" :src="imageUrl" :alt="galleryCardName(card)" draggable="false" @load="onImageLoad" @error="onImageError">
            <ArtworkFailure v-else :kind="failureKind" :reason="failureReason" />
            <div v-if="loaded" class="gallery-face__rect" :style="rectStyle" @pointerdown="start($event)" @pointermove="move" @pointerup="drag = null" @pointercancel="drag = null" @lostpointercapture="drag = null">
              <span class="gallery-face__cross"></span>
              <button class="gallery-face__resize" aria-label="拖曳調整框選大小" :disabled="disabled" @pointerdown.stop="start($event, true)" @pointermove.stop="move" @pointerup="drag = null" @pointercancel="drag = null" @lostpointercapture="drag = null">↘</button>
            </div>
          </div>
        </section>
        <section>
          <h4>圖片資訊</h4>
          <strong>{{ card.label }}</strong>
          <p class="gallery-muted gallery-face__identity">{{ card.image_id }}<br>{{ galleryDate(card.created_at).exact ?? galleryDate(card.created_at).relative }}</p>
          <p class="gallery-note">拖曳左側框選範圍，或使用下方數值調整。儲存的只有框選座標，不會建立另一張圖片。</p>
          <div class="gallery-face__numbers">
            <label v-for="(label, field) in { x: '水平位置', y: '垂直位置', w: '寬度', h: '高度' }" :key="field">
              {{ label }}<input type="number" :aria-label="label" :value="rect[field]" min="0" max="1" step="0.01" :disabled="disabled" @input="edit(field, $event)">
            </label>
          </div>
          <h4>方形裁切預覽（1:1）</h4>
          <div v-if="previewUrl" class="gallery-face__preview"><div class="gallery-face__crop" :style="previewStyle"><img :src="previewUrl" :alt="`${galleryCardName(card)}，框選預覽`" :style="faceCropStyle(rect)"></div></div>
          <p class="gallery-muted">依真實比例呈顯方形頭像，鎖定等長像素範圍。</p>
          <p v-if="!loaded" class="gallery-muted">圖片尚未載入，無法儲存框選。</p>
          <p v-if="rejected" class="gallery-feedback" role="status">操作未完成，框選已保留。<button @click="emit('log')">查看伺服器訊息</button></p>
        </section>
      </div>
      <footer class="gallery-actions"><button @click="close">取消</button><button class="gallery-primary" :disabled="disabled || !loaded" @click="submit">儲存框選</button></footer>
    </section>
  </div>
</template>

<style scoped>
.gallery-face-scrim { position: fixed; inset: 0; z-index: var(--z-surface-modal, 3000); background: #080a10bb; backdrop-filter: blur(calc(3px * var(--ui-scale))); display: grid; place-items: center; padding: calc(24px * var(--ui-scale)); }
.gallery-face { width: min(1100px * var(--ui-scale), 96vw); max-height: 92vh; overflow: auto; padding: calc(24px * var(--ui-scale)); border: 1px solid #d4b979; border-radius: var(--radius); background: linear-gradient(120deg, #1a1c24, #0b1017); box-shadow: 0 calc(15px * var(--ui-scale)) calc(90px * var(--ui-scale)) #000c; }
.gallery-face__head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #bda66b55; margin-bottom: calc(20px * var(--ui-scale)); }
.gallery-face__head h2 { margin: 0; font-size: var(--text-4xl); }
.gallery-face__head button { font-size: var(--text-3xl); }
.gallery-face__body { display: grid; grid-template-columns: 1fr 1fr; gap: calc(28px * var(--ui-scale)); }
.gallery-face__original { position: relative; width: fit-content; max-width: 100%; margin: auto; line-height: 0; }
.gallery-face__original > img { display: block; max-width: 100%; max-height: 57vh; width: auto; height: auto; border-radius: var(--radius-sm); }
.gallery-face__rect { position: absolute; border: 2px solid #f7df78; box-shadow: 0 0 0 calc(999px * var(--ui-scale)) #0003; clip-path: inset(-100vmax); cursor: move; touch-action: none; }
.gallery-face__original { overflow: hidden; }
.gallery-face__cross { position: absolute; inset: 0; background: linear-gradient(transparent calc(50% - .5px), #ffe59b66 50%, transparent calc(50% + .5px)), linear-gradient(90deg, transparent calc(50% - .5px), #ffe59b66 50%, transparent calc(50% + .5px)); pointer-events: none; }
.gallery-face .gallery-face__resize { position: absolute; bottom: calc(-10px * var(--ui-scale)); right: calc(-10px * var(--ui-scale)); padding: 0; width: calc(22px * var(--ui-scale)); height: calc(22px * var(--ui-scale)); border-radius: 1px; background: #f7df78; color: #292010; cursor: nwse-resize; touch-action: none; }
.gallery-face__preview { display: flex; align-items: center; justify-content: center; overflow: hidden; width: min(210px * var(--ui-scale), 100%); aspect-ratio: 1; margin: calc(14px * var(--ui-scale)) auto; border: 2px solid #d8bd74; background: #090b10; }
.gallery-face__crop { position: relative; overflow: hidden; }
.gallery-face__preview img { position: absolute; max-width: none; object-fit: fill; }
.gallery-face__numbers { display: grid; grid-template-columns: 1fr 1fr; gap: calc(10px * var(--ui-scale)); margin: calc(18px * var(--ui-scale)) 0; }
.gallery-face__numbers label { color: var(--paper-500); font-size: var(--text-xs); }
.gallery-face__numbers input { width: 100%; background: #10121a; color: var(--paper-100); padding: calc(6px * var(--ui-scale)); border: 1px solid #a5967755; }
.gallery-face__identity { overflow-wrap: anywhere; }
.gallery-face footer { margin: calc(20px * var(--ui-scale)) 0 0 auto; max-width: calc(480px * var(--ui-scale)); }
@media (max-width: 800px) { .gallery-face__body { grid-template-columns: 1fr; } }
</style>
