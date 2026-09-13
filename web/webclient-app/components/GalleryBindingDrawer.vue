<script setup>
import { ref } from "vue";
import HudDrawer from "./HudDrawer.vue";
import { GALLERY_SLOTS } from "./gallery-copy.js";
import "./gallery.css";

const props = defineProps({
  model: { type: Object, required: true },
  card: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
  rejected: { type: Boolean, default: false },
});
const emit = defineEmits(["close", "submit", "select-card", "log"]);
// v1 does not expose the stored mask; an unchecked draft makes no false claim.
const slots = ref([]);
</script>

<template>
  <div class="gallery-ui">
    <HudDrawer :open="true" title="裝備綁定" drawer-key="gallery-binding" @close="emit('close')">
      <p class="gallery-muted">僅符合指定的裝備條件時，將自動顯示此角色肖像。</p>
      <div class="gallery-editor-layout">
      <aside class="gallery-editor-reference">
      <img v-if="card.url" :src="card.url" :alt="card.label" class="gallery-editor-portrait">
      <p>{{ card.label }}</p>
      </aside>
      <div>
      <h4>裝備條件設定</h4>
      <p class="gallery-muted">勾選要綁定的裝備欄位。儲存時以目前穿戴的裝備為準，所有啟用的條件皆須符合。</p>
      <label v-for="slot in GALLERY_SLOTS" :key="slot.id" class="gallery-choice">
        <input v-model="slots" type="checkbox" :value="slot.id" :disabled="disabled">
        <span class="gallery-choice__glyph" aria-hidden="true">{{ slot.glyph }}</span>
        <span><strong>{{ slot.label }}</strong>
          <template v-if="slot.id === 'accessories'">
            <span v-for="(name, index) in model.equipment_summary?.accessories?.display_names" :key="index">{{ name }}</span>
            <span class="gallery-muted">已裝備 {{ model.equipment_summary?.accessories?.equipped_count }} / 5</span>
          </template>
          <span v-else>{{ model.equipment_summary?.[slot.id]?.display_name }}</span>
        </span>
      </label>
      <p class="gallery-muted">未勾選的欄位不參與判定；空欄位也可作為條件。</p>
      </div>
      </div>
      <section class="gallery-section">
        <h4>目前綁定條件</h4>
        <ul v-if="model.binding_warnings?.find((row) => row.image_id === card.image_id)">
          <li v-for="line in model.binding_warnings.find((row) => row.image_id === card.image_id).conditions" :key="line">{{ line }}</li>
        </ul>
        <p v-else class="gallery-muted">{{ card.binding_present ? '此肖像已綁定，尚無可顯示的條件資料。' : '尚未綁定裝備。' }}</p>
      </section>
      <section v-if="model.binding_warnings?.length" class="gallery-note">
        <h4>規則重疊提醒</h4>
        <p class="gallery-muted">以下為伺服器提供、符合目前裝備的肖像。</p>
        <article v-for="warning in model.binding_warnings" :key="warning.image_id" class="gallery-section">
          <strong>{{ warning.label }}</strong>
          <ul><li v-for="line in warning.conditions" :key="line">{{ line }}</li></ul>
          <button @click="emit('select-card', warning.image_id)">查看</button>
        </article>
      </section>
      <p v-if="rejected" class="gallery-feedback" role="status">操作未完成，選擇已保留。<button @click="emit('log')">查看伺服器訊息</button></p>
      <template #foot>
        <div class="gallery-actions">
          <button @click="emit('close')">取消</button>
          <button class="gallery-primary" :disabled="disabled || !slots.length || !model.capabilities?.supports_bindings" @click="emit('submit', { slots: [...slots] })">儲存綁定</button>
        </div>
      </template>
    </HudDrawer>
  </div>
</template>
