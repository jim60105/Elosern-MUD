<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useId } from "vue";
import DrawerHeader from "./DrawerHeader.vue";
import { createFocusTrap } from "./focus-trap.js";
import { clampStage, editStageField, moveStage } from "./stage-transform-edit.js";
import { galleryCardName } from "./gallery-copy.js";
import "./gallery.css";
const props = defineProps({ card: { type: Object, required: true }, disabled: Boolean, rejected: Boolean });
const emit = defineEmits(["close", "submit", "log"]);
const titleId = useId();
const root = ref(null);
const image = ref(null);
const draft = ref(clampStage(props.card.stage));
const numberDraft = ref(Object.fromEntries(Object.entries(draft.value).map(([field, value]) => [field, String(value)])));
const loaded = ref(false);
const failed = ref(false);
const submitted = ref(false);
let trap;
let drag = null;
const axes = [
  { field: "scale", label: "比例", min: 0.2, max: 2, hint: "0.20–2.00，預設 1.00" },
  { field: "x", label: "水平", min: -0.5, max: 0.5, hint: "−0.50–0.50，預設 0.00" },
  { field: "y", label: "垂直", min: -0.5, max: 0.5, hint: "−0.50–0.50，預設 0.00" },
];
const locked = computed(() => props.disabled || (submitted.value && !props.rejected));
const figureStyle = computed(() => ({ "--stage-scale": draft.value.scale, "--stage-x": draft.value.x, "--stage-y": draft.value.y }));
onMounted(() => {
  trap = createFocusTrap(root.value, { openerEl: document.activeElement });
  trap.enter();
  if (image.value?.complete && image.value.naturalWidth > 0) loaded.value = true;
});
onBeforeUnmount(() => trap?.restore());
function keydown(event) {
  event.stopPropagation();
  if (event.key === "Escape") { event.preventDefault(); emit("close"); }
  else trap?.onKeydown(event);
}
function edit(field, event) {
  if (locked.value) return;
  draft.value = editStageField(draft.value, field, event.target.valueAsNumber);
  numberDraft.value[field] = String(draft.value[field]);
  submitted.value = false;
}
function editNumber(field, event) {
  if (locked.value) return;
  numberDraft.value[field] = event.target.value;
  draft.value = editStageField(draft.value, field, event.target.valueAsNumber);
  submitted.value = false;
}
function finishNumber(field) { numberDraft.value[field] = String(draft.value[field]); }
function start(event) {
  if (locked.value || !loaded.value || event.button !== 0 || drag) return;
  const bounds = event.currentTarget.getBoundingClientRect();
  if (!bounds.width || !bounds.height) return;
  event.preventDefault();
  drag = { id: event.pointerId, x: event.clientX, y: event.clientY, bounds, stage: { ...draft.value } };
  event.currentTarget.setPointerCapture(event.pointerId);
}
function move(event) {
  if (!drag || drag.id !== event.pointerId || locked.value) return;
  draft.value = moveStage(drag.stage, (event.clientX - drag.x) / drag.bounds.width, (event.clientY - drag.y) / drag.bounds.height);
  numberDraft.value = Object.fromEntries(Object.entries(draft.value).map(([field, value]) => [field, String(value)]));
  submitted.value = false;
}
function end(event) { if (drag?.id === event.pointerId) drag = null; }
function reset() { if (!locked.value) { draft.value = clampStage(null); numberDraft.value = { scale: "1", x: "0", y: "0" }; submitted.value = false; } }
function submit() {
  if (locked.value || !loaded.value || failed.value) return;
  submitted.value = true;
  emit("submit", { stage: { ...draft.value } });
}
function readout(field) {
  const value = draft.value[field];
  return field === "scale" ? `${value.toFixed(2)} ×` : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(0)} %`;
}
</script>

<template>
  <div class="stage-transform-scrim" @click.self="emit('close')">
    <section ref="root" class="gallery-ui stage-transform" role="dialog" aria-modal="true" :aria-labelledby="titleId" @keydown="keydown">
      <DrawerHeader icon="gallery" title="比例調整" subtitle="全身肖像的舞臺位置" surface="gallery-stage-transform" :title-id="titleId" @close="emit('close')" />
      <div class="stage-transform__body">
        <section class="stage-transform__comparison">
          <div class="stage-transform__caption"><h4>{{ galleryCardName(card) }}</h4><span class="gallery-muted">成人身形參照</span></div>
          <div class="stage-transform__well">
            <div class="stage-transform__frame" :class="{ 'is-ready': loaded && !locked }" @pointerdown="start" @pointermove="move" @pointerup="end" @pointercancel="end" @lostpointercapture="end">
              <span class="stage-transform__adult" aria-hidden="true"></span>
              <img v-if="!failed" ref="image" class="stage-transform__figure" :src="card.url" :alt="galleryCardName(card)" :style="figureStyle" draggable="false" @load="loaded = true" @error="failed = true; loaded = false">
              <span class="stage-transform__floor" aria-hidden="true"></span>
            </div>
          </div>
          <p class="gallery-muted">拖曳肖像調整位置。背景成人身形維持原比例。</p>
        </section>
        <section class="stage-transform__instruments" aria-label="舞臺比例與位置">
          <p class="stage-transform__intro">調整舞臺與全身肖像的呈現，不影響頭像裁切。儲存的只有數值，不會產生新圖片。</p>
          <div v-for="axis in axes" :key="axis.field" class="stage-transform__instrument">
            <div class="stage-transform__label"><label :for="`${titleId}-${axis.field}-range`">{{ axis.label }}</label><output aria-hidden="true">{{ readout(axis.field) }}</output></div>
            <div class="stage-transform__pair">
              <div class="stage-transform__track"><input :id="`${titleId}-${axis.field}-range`" type="range" :min="axis.min" :max="axis.max" step="0.01" :value="draft[axis.field]" :disabled="locked" :aria-describedby="`${titleId}-${axis.field}-bounds`" @input="edit(axis.field, $event)"><span class="stage-transform__ticks" aria-hidden="true"></span></div>
              <input type="number" :aria-label="`${axis.label}數值`" :aria-describedby="`${titleId}-${axis.field}-bounds`" :min="axis.min" :max="axis.max" step="0.01" :value="numberDraft[axis.field]" :disabled="locked" @input="editNumber(axis.field, $event)" @change="finishNumber(axis.field)">
            </div>
            <p :id="`${titleId}-${axis.field}-bounds`" class="gallery-muted">{{ axis.hint }}</p>
          </div>
          <button :disabled="locked" class="stage-transform__reset" @click="reset">重設</button>
          <div class="stage-transform__state" role="status">
            <p v-if="failed" class="stage-transform__error">圖片載入失敗，無法儲存調整。</p>
            <p v-else-if="!loaded" class="gallery-muted">圖片載入中，暫時無法儲存。</p>
            <p v-else-if="locked" class="gallery-muted">調整暫時無法操作，請等待儲存完成或連線恢復。</p>
            <p v-if="rejected" class="gallery-feedback">操作未完成，調整已保留。<button class="gallery-link" @click="emit('log')">查看伺服器訊息</button></p>
          </div>
        </section>
      </div>
      <footer class="stage-transform__footer"><span class="gallery-muted">儲存後套用至此張肖像。</span><div class="gallery-actions"><button @click="emit('close')">取消</button><button class="gallery-primary" :disabled="locked || !loaded || failed" @click="submit">{{ locked && submitted ? '儲存中…' : '儲存調整' }}</button></div></footer>
    </section>
  </div>
</template>

<style scoped>
.stage-transform-scrim { position: fixed; inset: 0; z-index: var(--z-surface-modal, 3000); display: grid; place-items: center; padding: calc(24px * var(--ui-scale)); background: #080a10cf; backdrop-filter: blur(calc(3px * var(--ui-scale))); }
.stage-transform { width: min(calc(980px * var(--ui-scale)), 100%); max-height: 94vh; overflow: auto; border: 1px solid #d4b979; border-radius: var(--radius); background: linear-gradient(120deg, #1a1c24, #0b1017); box-shadow: 0 calc(18px * var(--ui-scale)) calc(90px * var(--ui-scale)) #000c; }
.stage-transform__body { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: calc(28px * var(--ui-scale)); padding: calc(24px * var(--ui-scale)); }
.stage-transform__caption, .stage-transform__label { display: flex; align-items: baseline; justify-content: space-between; gap: calc(10px * var(--ui-scale)); }
.stage-transform__caption h4 { margin: 0; }
.stage-transform__caption h4 { min-width: 0; overflow-wrap: anywhere; font-size: var(--text-md); }
.stage-transform__caption { flex-wrap: wrap; }
.stage-transform__instruments { position: relative; z-index: 1; background: linear-gradient(120deg, #131820, #0e141c); }
.stage-transform__well { padding: calc(24px * var(--ui-scale)) calc(42px * var(--ui-scale)) calc(12px * var(--ui-scale)); margin-top: calc(14px * var(--ui-scale)); background: radial-gradient(ellipse at 55% 45%, #22232b, #090c12 75%); border: 1px solid #bda66b33; border-radius: var(--radius-sm); }
.stage-transform__frame { position: relative; aspect-ratio: 3 / 4; touch-action: none; overflow: visible; }
.stage-transform__frame.is-ready { cursor: grab; }
.stage-transform__frame.is-ready:active { cursor: grabbing; }
.stage-transform__adult { position: absolute; bottom: 0; left: 12.5%; width: 75%; height: 100%; background: #17191f; mask: url('/art/defaults/man.webp') bottom center / contain no-repeat; -webkit-mask: url('/art/defaults/man.webp') bottom center / contain no-repeat; transform: translateX(-50%); pointer-events: none; }
.stage-transform__figure { --stage-scale: 1; --stage-x: 0; --stage-y: 0; position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; object-position: center bottom; transform: translate(calc(var(--stage-x) * 100%), calc(var(--stage-y) * 100%)) scale(var(--stage-scale)); transform-origin: 50% 100%; filter: drop-shadow(0 calc(5px * var(--ui-scale)) calc(9px * var(--ui-scale)) #0009); user-select: none; pointer-events: none; }
.stage-transform__floor { position: absolute; bottom: 0; left: -15%; right: -15%; height: 1px; background: linear-gradient(90deg, transparent, #bda66b70, transparent); pointer-events: none; }
.stage-transform__intro { margin: 0 0 calc(18px * var(--ui-scale)); color: var(--paper-300); font-size: var(--text-sm); }
.stage-transform__instrument { padding: calc(14px * var(--ui-scale)) 0; border-top: 1px solid #bda66b55; }
.stage-transform__label label { font-family: var(--f-serif); color: var(--gold-300); font-size: var(--text-lg); }
.stage-transform__label output { color: var(--paper-100); font-family: var(--f-num); font-variant-numeric: tabular-nums; }
.stage-transform__pair { display: grid; grid-template-columns: minmax(0, 1fr) calc(92px * var(--ui-scale)); align-items: center; gap: calc(18px * var(--ui-scale)); margin-top: calc(10px * var(--ui-scale)); }
.stage-transform__track { position: relative; }
.stage-transform input[type='range'] { width: 100%; accent-color: #d4b979; cursor: pointer; }
.stage-transform__ticks { display: block; height: calc(5px * var(--ui-scale)); margin: 0 calc(8px * var(--ui-scale)); background: repeating-linear-gradient(90deg, #bda66b65 0 1px, transparent 1px 10%); pointer-events: none; }
.stage-transform input[type='number'] { min-width: 0; width: 100%; padding: calc(7px * var(--ui-scale)); border: 1px solid #bda66b55; border-radius: var(--radius-sm); background: #0c1017; color: var(--paper-100); font-family: var(--f-num); font-variant-numeric: tabular-nums; }
.stage-transform__instrument p { margin: calc(8px * var(--ui-scale)) 0 0; }
.stage-transform__state { min-height: calc(58px * var(--ui-scale)); font-size: var(--text-sm); }
.stage-transform__error { color: var(--seal-300, #f49595); }
.stage-transform__footer { display: flex; align-items: center; justify-content: space-between; gap: calc(18px * var(--ui-scale)); border-top: 1px solid #bda66b55; padding: calc(18px * var(--ui-scale)) calc(24px * var(--ui-scale)); background: #090d1455; }
.stage-transform__footer .gallery-actions { min-width: calc(260px * var(--ui-scale)); }
@media (max-width: 720px) { .stage-transform__body { grid-template-columns: 1fr; } .stage-transform__comparison { max-width: calc(420px * var(--ui-scale)); width: 100%; margin: auto; } .stage-transform__footer { align-items: stretch; flex-direction: column; } }
@media (max-width: 720px) { .stage-transform__footer .gallery-actions { min-width: 0; } }
</style>
