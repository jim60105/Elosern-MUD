<script setup>
// Inspector column (frontend design §2, §4, §5.4): the selected object's
// name, copyable qualified ID and source path, fields with unit and frame,
// directed relationships, contextual actions and the inline delete
// explanation. A multi-selection lists every object and its owning document;
// a cross-document selection is inspect/copy only, with the reason in place
// of mutation actions. Nothing here uses a confirmation dialog.
// Authored text renders through text interpolation only.
import { ref } from "vue";
import { CROSS_DOCUMENT, INDEX_UNAVAILABLE, REFERENCED } from "../lib/deletion.js";

defineProps({
  record: { type: Object, default: null },
  summary: { type: Object, default: null },
  relations: { type: Object, default: null },
  refusal: { type: Object, default: null },
  removed: { type: Array, default: () => [] },
  copyHint: { type: String, default: "" },
});
const emit = defineEmits(["follow", "copy", "delete"]);
const root = ref(null);

function focusHeading() {
  root.value?.querySelector("[data-inspector-title]")?.focus();
}

// The first editable field, else the heading (Enter from the canvas).
function focusFirstField() {
  const field = root.value?.querySelector("input:not([type='checkbox']), textarea, select");
  if (field) field.focus();
  else focusHeading();
}

defineExpose({ focusHeading, focusFirstField });
</script>

<template>
  <div ref="root" class="inspector">
    <template v-if="summary && summary.count > 1">
      <h2 class="section-label">檢查器 · 多重選取</h2>
      <h3 class="inspector__title" tabindex="-1" data-inspector-title>已選取 {{ summary.count }} 個物件</h3>
      <p class="inspector__owners" data-selection-owners>
        {{ summary.crossDocument ? `${summary.owners.length} 份文件` : "同一文件" }}
      </p>
      <ul class="plain inspector__members">
        <li v-for="entry in summary.entries" :key="entry.ref" data-selection-member>
          <span>{{ entry.label }}</span>
          <span class="mono inspector__id">{{ entry.ref }}</span>
          <span class="mono inspector__path">{{ entry.relativePath }}</span>
        </li>
      </ul>
      <p v-if="summary.reason" class="inspector__reason" data-selection-reason>{{ summary.reason }}</p>
      <div class="inspector__actions">
        <button type="button" class="button" data-action="copy" aria-keyshortcuts="Control+C Meta+C" @click="emit('copy')">⧉ 複製 OMP 脈絡</button>
      </div>
    </template>

    <template v-else-if="record">
      <h2 class="section-label">檢查器</h2>
      <h3 class="inspector__title" tabindex="-1" data-inspector-title>{{ record.title }}</h3>
      <p class="mono inspector__id" data-inspector-ref>{{ record.qualifiedRef }}</p>
      <p class="mono inspector__path" data-inspector-path>{{ record.relativePath }}</p>
      <dl class="inspector__fields">
        <template v-for="(field, index) in record.fields" :key="index">
          <dt>{{ field.label }}</dt>
          <dd :data-field="field.label">{{ field.value }}</dd>
        </template>
      </dl>
      <slot />
      <template v-if="relations">
        <h3 class="section-label">關係 · 有向</h3>
        <p v-if="!relations.outgoing.length && !relations.incoming.length" class="inspector__muted">沒有記錄的關係。</p>
        <ul class="plain relations">
          <li v-for="(row, index) in relations.outgoing" :key="`o${index}`" data-relation="out">
            <span class="relations__kind">{{ row.kind }}</span>
            <button v-if="row.ref" type="button" class="link" :data-follow="row.ref" @click="emit('follow', row.ref)">{{ row.label }}</button>
            <span v-else>{{ row.label }}</span>
            <span class="mono relations__source">{{ row.source }}</span>
          </li>
          <li v-for="(row, index) in relations.incoming" :key="`i${index}`" data-relation="in" :data-external="row.external ? 'true' : null">
            <span class="relations__kind">← {{ row.kind }}</span>
            <button v-if="row.ref" type="button" class="link" :data-follow="row.ref" @click="emit('follow', row.ref)">{{ row.label }}</button>
            <span v-else>{{ row.label }}</span>
            <span class="mono relations__source">{{ row.source }}</span>
          </li>
        </ul>
      </template>
      <div class="inspector__actions">
        <button type="button" class="button" data-action="copy" :aria-keyshortcuts="copyHint" @click="emit('copy')">⧉ 複製 OMP 脈絡</button>
        <button type="button" class="button" data-action="delete" aria-keyshortcuts="Delete" @click="emit('delete')">✕ 刪除</button>
      </div>
    </template>

    <p v-else-if="removed.length" class="inspector__empty" data-selection-removed>
      已選取的 <span class="mono">{{ removed.join("、") }}</span> 在新版檔案中已不存在，選取已清除。
    </p>
    <template v-else>
      <h2 class="section-label">檢查器</h2>
      <p class="inspector__empty">尚未選取。在畫布或物件清單中選取物件，或在畫布上用方向鍵巡覽、Enter 選取。</p>
    </template>

    <div v-if="refusal" class="refusal" role="status" :data-delete-refusal="refusal.key">
      <template v-if="refusal.key === CROSS_DOCUMENT">
        <strong>跨文件的選取只能檢視與複製，不能刪除。</strong>
      </template>
      <template v-else-if="refusal.key === INDEX_UNAVAILABLE">
        <strong>▲ 外部索引不可用，無法確認外部引用，因此不能刪除。</strong>
        <p class="inspector__muted">檢視、移動與編輯欄位不受影響。沒有寫入任何檔案。</p>
        <p v-for="(reason, index) in refusal.reasons" :key="index" class="mono refusal__reason">{{ reason }}</p>
      </template>
      <template v-else-if="refusal.key === REFERENCED">
        <strong>✕ 無法刪除：仍有 {{ refusal.external.length }} 個外部引用</strong>
        <ul class="plain">
          <li v-for="(row, index) in refusal.external" :key="index" data-refusal-reference>
            {{ row.kind }} · {{ row.label }} <span class="mono refusal__reason">{{ row.source }}</span>
          </li>
        </ul>
        <p class="inspector__muted">不會連帶刪除。沒有寫入任何檔案。</p>
      </template>
      <template v-else>
        <strong>這個版本尚未提供刪除此類物件的指令。</strong>
        <p class="inspector__muted">沒有寫入任何檔案；刪除會由各領域工具提供，並由服務端檢查引用。</p>
      </template>
      <template v-if="refusal.internal?.length">
        <p class="inspector__muted">同時仍被地圖資料引用（刪除會留下失效引用，不會連帶刪除）：</p>
        <ul class="plain">
          <li v-for="(row, index) in refusal.internal" :key="index" data-refusal-internal>
            {{ row.kind }} ·
            <button v-if="row.ref" type="button" class="link" :data-follow="row.ref" @click="emit('follow', row.ref)">{{ row.label }}</button>
            <span v-else>{{ row.label }}</span>
            <span class="mono refusal__reason">{{ row.source }}</span>
          </li>
        </ul>
      </template>
    </div>
  </div>
</template>
