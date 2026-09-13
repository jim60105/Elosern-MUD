<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { createFocusTrap } from "./focus-trap.js";
import { clampFaceRect, faceCropStyle, moveFaceRect, resizeFaceRect } from "./face-rect-edit.js";
import { galleryTimestamp } from "./gallery-copy.js";
import "./gallery.css";

const props = defineProps({
  card: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
  rejected: { type: Boolean, default: false },
});
const emit = defineEmits(["close", "submit", "log"]);
const rect = ref(clampFaceRect(props.card.face_rect));
const root = ref(null);
const image = ref(null);
let trap;
let drag = null;
const loaded = ref(false);
const dimensions = ref({ width: 1, height: 1 });
const previewStyle = computed(() => {
  const ratio = dimensions.value.width * rect.value.w / (dimensions.value.height * rect.value.h);
  return ratio >= 1
    ? { width: "100%", height: `${100 / ratio}%` }
    : { width: `${100 * ratio}%`, height: "100%" };
});
const rectStyle = computed(() => ({
  left: `${rect.value.x * 100}%`, top: `${rect.value.y * 100}%`,
  width: `${rect.value.w * 100}%`, height: `${rect.value.h * 100}%`,
}));
onMounted(() => {
  trap = createFocusTrap(root.value, { openerEl: document.activeElement });
  trap.enter();
});
onBeforeUnmount(() => { trap?.restore(); });
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
  rect.value = drag.resize ? resizeFaceRect(drag.rect, dx, dy) : moveFaceRect(drag.rect, dx, dy);
}
function edit(field, event) {
  rect.value = clampFaceRect({ ...rect.value, [field]: event.target.valueAsNumber });
}
function imageLoaded() {
  loaded.value = true;
  dimensions.value = { width: image.value.naturalWidth || 1, height: image.value.naturalHeight || 1 };
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
            <img ref="image" :src="card.url" :alt="card.label" draggable="false" @load="imageLoaded" @error="loaded = false">
            <div v-if="loaded" class="gallery-face__rect" :style="rectStyle" @pointerdown="start($event)" @pointermove="move" @pointerup="drag = null" @pointercancel="drag = null" @lostpointercapture="drag = null">
              <span class="gallery-face__cross"></span>
              <button class="gallery-face__resize" aria-label="拖曳調整框選大小" :disabled="disabled" @pointerdown.stop="start($event, true)" @pointermove.stop="move" @pointerup="drag = null" @pointercancel="drag = null" @lostpointercapture="drag = null">↘</button>
            </div>
          </div>
        </section>
        <section>
          <h4>圖片資訊</h4>
          <strong>{{ card.label }}</strong>
          <p class="gallery-muted gallery-face__identity">{{ card.image_id }}<br>{{ galleryTimestamp(card.created_at) }}</p>
          <p class="gallery-note">拖曳左側框選範圍，或使用下方數值調整。儲存的只有框選座標，不會建立另一張圖片。</p>
          <div class="gallery-face__numbers">
            <label v-for="(label, field) in { x: '水平位置', y: '垂直位置', w: '寬度', h: '高度' }" :key="field">
              {{ label }}<input type="number" :aria-label="label" :value="rect[field]" min="0" max="1" step="0.01" :disabled="disabled" @input="edit(field, $event)">
            </label>
          </div>
          <h4>方形裁切預覽（1:1）</h4>
          <div class="gallery-face__preview"><div class="gallery-face__crop" :style="previewStyle"><img :src="card.url" :alt="`${card.label}，框選預覽`" :style="faceCropStyle(rect)"></div></div>
          <p class="gallery-muted">完整呈現框選範圍，保留原始比例。</p>
          <p v-if="!loaded" class="gallery-muted">圖片尚未載入，可使用數值調整框選。</p>
          <p v-if="rejected" class="gallery-feedback" role="status">操作未完成，框選已保留。<button @click="emit('log')">查看伺服器訊息</button></p>
        </section>
      </div>
      <footer class="gallery-actions"><button @click="close">取消</button><button class="gallery-primary" :disabled="disabled" @click="emit('submit', { face_rect: { ...rect } })">儲存框選</button></footer>
    </section>
  </div>
</template>

<style scoped>
.gallery-face-scrim { position: fixed; inset: 0; z-index: var(--z-surface-modal, 3000); background: #080a10bb; backdrop-filter: blur(3px); display: grid; place-items: center; padding: 24px; }
.gallery-face { width: min(1100px, 96vw); max-height: 92vh; overflow: auto; padding: 24px; border: 1px solid #d4b979; border-radius: 8px; background: linear-gradient(120deg, #1a1c24, #0b1017); box-shadow: 0 15px 90px #000c; }
.gallery-face__head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #bda66b55; margin-bottom: 20px; }
.gallery-face__head h2 { margin: 0; font-size: 32px; }
.gallery-face__head button { font-size: 28px; }
.gallery-face__body { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; }
.gallery-face__original { position: relative; width: fit-content; max-width: 100%; margin: auto; line-height: 0; }
.gallery-face__original > img { display: block; max-width: 100%; max-height: 57vh; width: auto; height: auto; border-radius: 5px; }
.gallery-face__rect { position: absolute; border: 2px solid #f7df78; box-shadow: 0 0 0 999px #0003; clip-path: inset(-100vmax); cursor: move; touch-action: none; }
.gallery-face__original { overflow: hidden; }
.gallery-face__cross { position: absolute; inset: 0; background: linear-gradient(transparent calc(50% - .5px), #ffe59b66 50%, transparent calc(50% + .5px)), linear-gradient(90deg, transparent calc(50% - .5px), #ffe59b66 50%, transparent calc(50% + .5px)); pointer-events: none; }
.gallery-face .gallery-face__resize { position: absolute; bottom: -10px; right: -10px; padding: 0; width: 22px; height: 22px; border-radius: 1px; background: #f7df78; color: #292010; cursor: nwse-resize; touch-action: none; }
.gallery-face__preview { display: flex; align-items: center; justify-content: center; overflow: hidden; width: min(210px, 100%); aspect-ratio: 1; margin: 14px auto; border: 2px solid #d8bd74; background: #090b10; }
.gallery-face__crop { position: relative; overflow: hidden; }
.gallery-face__preview img { position: absolute; max-width: none; object-fit: fill; }
.gallery-face__numbers { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 18px 0; }
.gallery-face__numbers label { color: var(--paper-500); font-size: 12px; }
.gallery-face__numbers input { width: 100%; background: #10121a; color: var(--paper-100); padding: 6px; border: 1px solid #a5967755; }
.gallery-face__identity { overflow-wrap: anywhere; }
.gallery-face footer { margin: 20px 0 0 auto; max-width: 480px; }
@media (max-width: 800px) { .gallery-face__body { grid-template-columns: 1fr; } }
</style>
