<script setup>
import { computed, ref } from "vue";
import HudDrawer from "./HudDrawer.vue";
import ArtworkPreview from "./ArtworkPreview.vue";
import { GALLERY_FIELDS, GALLERY_SLOTS } from "./gallery-copy.js";
import { pageShape } from "./gallery-window-model.js";
import "./gallery.css";

const props = defineProps({
  model: { type: Object, required: true },
  preview: { type: Object, default: null },
  disabled: { type: Boolean, default: false },
  rejected: { type: Boolean, default: false },
  // creation-draft-portrait: the host context. "creation" switches the
  // contextual copy for a character that does not exist yet and suppresses
  // the gallery-only character link, equipment and gallery notes; the
  // absent prop keeps every gallery behaviour.
  context: { type: String, default: "gallery" },
  // creation-draft-portrait: the server's unavailability reason from the
  // committed creation portrait (empty otherwise). In creation context it
  // disables submit, keeps the prompt editable and offers a status refresh.
  unavailableReason: { type: String, default: "" },
});
const emit = defineEmits(["close", "submit", "character", "log", "refresh-status"]);
const creation = computed(() => props.context === "creation");
// Server unavailability blocks only the submission; the prompt stays editable.
const offline = computed(() => creation.value && props.unavailableReason !== "");
const submitBlocked = computed(() => props.disabled || offline.value);
const fields = ref([]);
const prompt = ref("");
const count = computed(() => [...prompt.value].length);
// The committed subject tile of the selection.
const subject = computed(() => props.model.groups
  ?.flatMap((group) => group.subjects)
  .find((row) => row.subject_key === props.model.selected) ?? null);
// The character-data link belongs only to the live character: its tile is
// marked `is_current`.
const puppet = computed(() => subject.value?.is_current === true);
// A scene (change gallery-scene-category) is a landscape: the reference shows
// the background in effect at 16:9 — the stored card, else the subject's
// committed tile artwork (its bundled image) — and the copy speaks of a
// background shared by every traveller, not of a portrait.
const landscape = computed(() => pageShape(subject.value?.kind) === "landscape");
const reference = computed(() => {
  if (props.preview?.artwork) return { artwork: props.preview.artwork, id: props.preview.image_id, alt: props.preview.label };
  if (landscape.value && subject.value?.artwork) {
    return { artwork: subject.value.artwork, id: subject.value.subject_key, alt: subject.value.display_name };
  }
  return null;
});

function submit() {
  if (!submitBlocked.value) emit("submit", {
    fields: props.model.capabilities?.supports_field_selection ? [...fields.value] : [],
    custom_prompt: props.model.capabilities?.supports_free_text ? prompt.value : "",
  });
}
</script>

<template>
  <div class="gallery-ui" :class="{ 'gallery-ui--creation': creation }">
    <HudDrawer :open="true" :title="creation ? '繪製肖像' : '生成新圖'" :drawer-key="creation ? 'creation-portrait' : 'gallery-generate'" @close="emit('close')">
      <template v-if="landscape">
      <p class="gallery-muted">依照這個場景的設定，重新繪製它的背景圖。</p>
      <figure class="gallery-editor-scene" data-testid="gallery-generate__scene">
        <ArtworkPreview v-if="reference" class="gallery-editor-scene__art" :artwork="reference.artwork" :panel="model" :view-subject-id="reference.id" :alt="reference.alt" />
        <p v-else class="gallery-editor-placeholder gallery-editor-scene__art">新的風景<br>即將展開</p>
        <figcaption>
          <strong>{{ subject?.display_name }}</strong>
          <span class="gallery-muted">{{ preview?.artwork ? "目前的背景" : "目前使用官方內建圖" }}</span>
        </figcaption>
      </figure>
      </template>
      <template v-else-if="creation">
      <!-- Creation context (creation-draft-portrait): the character does not
           exist yet, so the drawer is a focused two-column page — the
           current portrait (or an empty plate) beside the one free-text
           prompt, the server's unavailability, the notes and the feedback. -->
      <p class="gallery-muted">依照目前填寫的種族、血統、性別與外觀年齡，為角色繪製肖像。</p>
      <div class="gallery-editor-layout gallery-creation">
        <aside class="gallery-editor-reference gallery-creation__reference">
          <ArtworkPreview v-if="preview?.artwork" class="gallery-editor-portrait" :artwork="preview.artwork" :panel="model" :view-subject-id="preview.image_id" :alt="preview.label" />
          <p v-else class="gallery-editor-placeholder">肖像<br>將在此現身</p>
          <p class="gallery-muted">{{ preview?.artwork ? "目前的肖像" : "尚未繪製肖像" }}</p>
        </aside>
        <div class="gallery-creation__form">
          <section class="gallery-creation__prompt">
            <h4><label for="gallery-prompt">補充提示詞</label></h4>
            <p class="gallery-muted">可用自然語言描述想要的氛圍、構圖、光影、表情或場景等。（非必填）</p>
            <textarea id="gallery-prompt" v-model="prompt" :disabled="disabled" placeholder="例如：月光下的城牆、回頭凝視、微笑……"></textarea>
            <p class="gallery-counter">{{ count }} / 512</p>
          </section>
          <p v-if="offline" class="gallery-feedback gallery-feedback--offline" role="status" data-testid="gallery-generate__unavailable">
            <span>{{ unavailableReason }}</span>
            <button type="button" data-testid="gallery-generate__refresh" @click="emit('refresh-status')">重新檢查</button>
          </p>
          <p v-if="rejected" class="gallery-feedback" role="status">操作未完成，輸入已保留。<button @click="emit('log')">查看伺服器訊息</button></p>
          <p class="gallery-note">肖像只保留一張；重新繪製完成後會取代目前的肖像。送出後可以繼續填寫，完成的肖像會出現在左側的肖像欄。</p>
        </div>
      </div>
      </template>
      <template v-else-if="!creation">
      <p class="gallery-muted">透過目前的角色資料，生成全新的角色肖像。</p>
      <div class="gallery-editor-layout">
      <aside class="gallery-editor-reference">
        <ArtworkPreview v-if="preview?.artwork" class="gallery-editor-portrait" :artwork="preview.artwork" :panel="model" :view-subject-id="preview.image_id" :alt="preview.label" />
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
      </template>
      <template v-if="!creation">
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
      <p v-if="landscape" class="gallery-note">背景只保留一張，生成完成後會替換原圖；這是世界共用的背景，所有旅人看到的都會一起改變。</p>
      <p v-else-if="model.capabilities?.max_cards === 1" class="gallery-note">此圖庫保留一張肖像，生成完成後會替換原圖。</p>
      <p class="gallery-note">送出後會在圖庫中顯示生成中卡片，完成時自動加入圖庫。</p>
      <p v-if="rejected" class="gallery-feedback" role="status">操作未完成，輸入已保留。<button @click="emit('log')">查看伺服器訊息</button></p>
      </template>
      <template #foot>
        <div class="gallery-actions">
          <button @click="emit('close')">取消</button>
          <button class="gallery-primary" data-testid="gallery-generate__submit" :disabled="submitBlocked" @click="submit">開始生成</button>
        </div>
      </template>
    </HudDrawer>
  </div>
</template>
