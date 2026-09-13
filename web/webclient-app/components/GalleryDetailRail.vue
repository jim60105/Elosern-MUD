<script setup>
import { computed, ref, watch } from "vue";
import { faceObjectPosition } from "./face-rect.js";
import { galleryTimestamp } from "./gallery-copy.js";
import "./gallery.css";

const props = defineProps({
  card: { type: Object, default: null },
  capabilities: { type: Object, default: () => ({}) },
  warnings: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["default", "delete", "generate", "binding", "face"]);
const confirming = ref(false);
const conditions = computed(() => props.warnings.find((row) => row.image_id === props.card?.image_id)?.conditions);
watch(() => props.card?.image_id, () => { confirming.value = false; });
function confirmDelete() {
  if (!props.disabled && confirming.value) {
    confirming.value = false;
    emit("delete");
  }
}
</script>

<template>
  <aside class="gallery-ui gallery-detail" data-testid="gallery-detail">
    <h3>肖像詳情</h3>
    <template v-if="card">
      <img v-if="card.status === 'card' && card.url" class="gallery-detail__image" :src="card.url" :alt="card.label" :style="{ objectPosition: faceObjectPosition(card.face_rect) }">
      <p v-else class="gallery-note">{{ card.label }}</p>
      <h4>{{ card.label }}</h4>
      <p class="gallery-muted">{{ galleryTimestamp(card.created_at) }}</p>
      <div class="gallery-chips"><span v-for="chip in card.chips" :key="chip" class="gallery-chip">{{ chip }}</span></div>
      <template v-if="card.status === 'card'">
        <section class="gallery-section">
          <h4>綁定條件</h4>
          <ul v-if="conditions"><li v-for="line in conditions" :key="line">{{ line }}</li></ul>
          <p v-else class="gallery-muted">{{ card.binding_present ? '此肖像已綁定，尚無可顯示的條件資料。' : '尚未綁定裝備。' }}</p>
          <h4>當前狀態</h4>
          <p>{{ card.is_default ? '目前預設' : '未設為預設' }}</p>
          <p class="gallery-muted">裝備變動時，將依符合的條件自動選擇肖像。</p>
        </section>
        <button class="gallery-primary gallery-detail__default" :disabled="disabled || card.is_default" @click="emit('default')">設為預設</button>
        <div class="gallery-actions">
          <button v-if="capabilities.supports_bindings" :disabled="disabled" @click="emit('binding')">編輯設定</button>
          <button :disabled="disabled" @click="emit('face')">臉部框選</button>
          <button class="gallery-danger" :disabled="disabled" @click="confirming = true">刪除</button>
        </div>
        <div v-if="confirming" class="gallery-note gallery-detail__confirm" role="group" aria-label="刪除確認">
          <p>刪除此肖像？圖片將無法復原。</p>
          <div class="gallery-actions">
            <button @click="confirming = false">取消</button>
            <button class="gallery-danger" :disabled="disabled" @click="confirmDelete">確認刪除</button>
          </div>
        </div>
      </template>
    </template>
    <p v-else class="gallery-muted">選擇一張肖像，查看圖片與設定。</p>
    <p v-if="capabilities.max_cards === 1" class="gallery-note">此圖庫保留一張肖像，生成完成後會替換原圖。</p>
    <button class="gallery-primary gallery-detail__generate" :disabled="disabled" @click="emit('generate')">生成新圖</button>
  </aside>
</template>

<style scoped>
.gallery-detail { min-width: 0; padding: 18px; border-left: 1px solid #bca57955; background: linear-gradient(150deg, #1d1e2520, #0a0e15); }
.gallery-detail h3 { padding-right: 36px; }
.gallery-detail__image { width: 100%; height: clamp(190px, 32vh, 360px); object-fit: cover; border: 1px solid #bca57988; border-radius: 5px; margin-bottom: 12px; }
.gallery-detail h4 { overflow-wrap: anywhere; margin-bottom: 6px; }
.gallery-detail ul { padding-left: 18px; }
.gallery-detail__default, .gallery-detail__generate { width: 100%; margin-bottom: 10px; }
.gallery-detail__generate { margin-top: 18px; }
.gallery-detail__confirm { margin-top: 14px; }
.gallery-detail .gallery-actions button { padding: 7px; font-size: 12px; }
</style>
