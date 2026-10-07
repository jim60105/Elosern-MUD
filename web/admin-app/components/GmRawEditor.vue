<script setup>
import { reactive, ref } from 'vue';
import GmConsolePrompt from './GmConsolePrompt.vue';
import GmJsonTree from './GmJsonTree.vue';
const props = defineProps({ target: { type: String, required: true }, raw: { type: Object, required: true }, api: { type: Object, required: true } });
const emit = defineEmits(['done']);
const editing = ref(false), operations = ref([]), request = ref(null), error = ref('');
const draft = reactive({ op: 'set_attr', key: '', category: '', value: 'null' });
function selectAttribute(row) { draft.op = 'set_attr'; draft.key = row.key; draft.category = row.category ?? ''; draft.value = JSON.stringify(row.value, null, 2); }
function selectTag(row) { draft.op = 'remove_tag'; draft.key = row.key; draft.category = row.category ?? ''; }
function append() {
  error.value = '';
  try {
    const op = { op: draft.op };
    if (draft.op !== 'set_location') { op.key = draft.key; op.category = draft.category || null; }
    if (['set_attr', 'set_location'].includes(draft.op)) op.value = JSON.parse(draft.value);
    operations.value.push(op);
  } catch { error.value = 'value 必須是有效的 JSON。'; }
}
function done(result) { request.value = null; operations.value = []; emit('done', result); }
</script>
<template>
  <button type="button" class="ui-btn" @click="editing = !editing">{{ editing ? '結束編輯' : '編輯' }}</button>
  <section v-if="editing" aria-label="原始資料編輯">
    <p role="note" class="gm-raw-warning">繞過規則層：原始位置變更不會處理對話、隊伍、實例釘選或時間。typeclass 與 components 僅供檢視。</p>
    <div><button v-for="row in raw.attributes ?? []" :key="`${row.category}:${row.key}`" type="button" class="ui-btn ui-btn--sm" @click="selectAttribute(row)">{{ row.category || '無分類' }} · {{ row.key }}</button></div>
    <div><button v-for="row in raw.tags ?? []" :key="`${row.category}:${row.key}`" type="button" class="ui-btn ui-btn--sm" @click="selectTag(row)">{{ row.category || '無分類' }} · {{ row.key }}</button></div>
    <form @submit.prevent="append">
      <label>操作<select v-model="draft.op"><option v-for="op in ['set_attr','del_attr','add_tag','remove_tag','set_location']" :key="op">{{ op }}</option></select></label>
      <label v-if="draft.op !== 'set_location'">key<input v-model="draft.key" required /></label>
      <label v-if="draft.op !== 'set_location'">category<input v-model="draft.category" placeholder="空白代表 null" /></label>
      <label v-if="['set_attr','set_location'].includes(draft.op)">value（JSON）<textarea v-model="draft.value" required /></label>
      <button type="submit" class="ui-btn">加入批次</button>
    </form>
    <p v-if="error" role="alert">{{ error }}</p>
    <ol><li v-for="(operation, index) in operations" :key="index"><GmJsonTree :value="operation" /><button type="button" @click="operations.splice(index,1)">移除</button></li></ol>
    <button type="button" class="ui-btn ui-btn--danger" :disabled="!operations.length" @click="request = {path: `/state/object/${target.replace(/^#/, '')}/raw`, body: {operations: operations.map(op => ({...op}))}, label: `raw_edit · ${target}`}">確認批次</button>
  </section>
  <GmConsolePrompt :request="request" :api="api" @cancel="request = null" @done="done" />
</template>
<style scoped>
.gm-raw-warning { color: var(--paper-100); padding: var(--sp-3); border: 1px solid var(--seal-600); position: sticky; top: 0; background: var(--ink-860); } form, label { display: grid; gap: var(--sp-2); } input, select, textarea { color: var(--paper-100); background: var(--ink-950); border: var(--line); padding: var(--sp-2); }
</style>
