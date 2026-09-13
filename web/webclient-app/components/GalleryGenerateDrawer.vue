<script setup>
import { computed, ref } from "vue";
import HudDrawer from "./HudDrawer.vue";
import { GALLERY_FIELDS, GALLERY_SLOTS } from "./gallery-copy.js";
import "./gallery.css";

const props = defineProps({
  model: { type: Object, required: true },
  preview: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
  rejected: { type: Boolean, default: false },
});
const emit = defineEmits(["close", "submit", "character", "log"]);
const fields = ref([]);
const prompt = ref("");
const count = computed(() => [...prompt.value].length);
const puppet = computed(() => props.model.subjects?.find((row) => row.subject_key === props.model.selected)?.is_puppet);
function submit() {
  if (!props.disabled) emit("submit", {
    fields: props.model.capabilities?.supports_field_selection ? [...fields.value] : [],
    custom_prompt: props.model.capabilities?.supports_free_text ? prompt.value : "",
  });
}
</script>

<template>
  <div class="gallery-ui">
    <HudDrawer :open="true" title="生成新圖" drawer-key="gallery-generate" @close="emit('close')">
      <p class="gallery-muted">透過目前的角色資料，生成全新的角色肖像。</p>
      <div class="gallery-editor-layout">
      <aside class="gallery-editor-reference">
        <img v-if="preview?.url" :src="preview.url" :alt="preview.label" class="gallery-editor-portrait">
        <p v-else class="gallery-editor-placeholder">新的相遇<br>即將誕生</p>
        <p class="gallery-muted">用文字描繪想像<br>讓角色在此刻現身。</p>
      </aside>
      <div>
      <h4 v-if="model.capabilities?.supports_field_selection">納入生成的資料</h4>
      <label v-for="field in model.capabilities?.supports_field_selection ? GALLERY_FIELDS : []" :key="field.id" class="gallery-choice">
        <input v-model="fields" type="checkbox" :value="field.id" :disabled="disabled">
        <span class="gallery-choice__glyph" aria-hidden="true">{{ field.glyph }}</span>
        <span><strong>{{ field.label }}</strong><span class="gallery-muted">{{ field.note }}</span></span>
      </label>
      <p v-if="model.capabilities?.supports_field_selection" class="gallery-counter">已選 {{ fields.length }} / 5</p>
      </div>
      </div>
      <section v-if="model.equipment_summary" class="gallery-section">
        <h4>目前裝備摘要</h4>
        <button v-if="puppet" class="gallery-link" @click="emit('character')">從角色資料檢視</button>
        <div class="gallery-equipment">
          <div v-for="slot in GALLERY_SLOTS" :key="slot.id">
            <span class="gallery-muted">{{ slot.label }}</span>
            <template v-if="slot.id === 'accessories'">
              <p>已裝備 {{ model.equipment_summary[slot.id]?.equipped_count }} / 5</p>
              <ul><li v-for="(name, index) in model.equipment_summary[slot.id]?.display_names" :key="index">{{ name }}</li></ul>
            </template>
            <p v-else>{{ model.equipment_summary[slot.id]?.display_name }}</p>
          </div>
        </div>
      </section>
      <section v-if="model.capabilities?.supports_free_text" class="gallery-section">
        <h4><label for="gallery-prompt">補充提示詞</label></h4>
        <p class="gallery-muted">可用自然語言描述想要的氛圍、構圖、光影、表情或場景等。（非必填）</p>
        <textarea id="gallery-prompt" v-model="prompt" :disabled="disabled" placeholder="例如：月光下的城牆、回頭凝視、微笑……"></textarea>
        <p class="gallery-counter">{{ count }} / 512</p>
      </section>
      <p v-if="model.capabilities?.max_cards === 1" class="gallery-note">此圖庫保留一張肖像，生成完成後會替換原圖。</p>
      <p class="gallery-note">送出後會在圖庫中顯示生成中卡片，完成時自動加入圖庫。</p>
      <p v-if="rejected" class="gallery-feedback" role="status">操作未完成，輸入已保留。<button @click="emit('log')">查看伺服器訊息</button></p>
      <template #foot>
        <div class="gallery-actions">
          <button @click="emit('close')">取消</button>
          <button class="gallery-primary" :disabled="disabled" @click="submit">開始生成</button>
        </div>
      </template>
    </HudDrawer>
  </div>
</template>
