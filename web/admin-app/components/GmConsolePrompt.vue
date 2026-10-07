<script setup>
import { ref, watch } from 'vue';
import GmConfirmDialog from './GmConfirmDialog.vue';
import GmError from './GmError.vue';
import GmJsonTree from './GmJsonTree.vue';
import GmConsoleResult from './GmConsoleResult.vue';
import { saveNotice } from '../lib/console.js';
const props = defineProps({ request: { type: Object, default: null }, api: { type: Object, required: true } });
const emit = defineEmits(['cancel', 'done']);
const status = ref(null), error = ref(null), result = ref(null), pending = ref(false);
watch(() => props.request, async (request, _old, onCleanup) => {
  let active = true;
  onCleanup(() => { active = false; });
  status.value = null; error.value = null;
  if (!request) return;
  result.value = null;
  try { const value = await props.api.get('/console/status'); if (active) status.value = value; }
  catch (failure) { if (active) error.value = failure; }
}, { immediate: true });
async function submit() {
  if (pending.value || !status.value || status.value.tick === null || error.value) return;
  pending.value = true;
  try {
    result.value = await props.api.post(props.request.path, props.request.body);
    emit('done', result.value);
  } catch (failure) { error.value = failure; }
  finally { pending.value = false; }
}
</script>
<template>
  <GmConfirmDialog :open="Boolean(request)" title="確認主控台操作" confirm-label="執行操作" danger
    :busy="pending" :confirm-disabled="!status || status.tick === null || Boolean(error)" @confirm="submit" @cancel="!pending && emit('cancel')">
    <p>{{ request?.label }}</p>
    <GmJsonTree v-if="request" :value="request.body" />
    <p data-save-notice>{{ saveNotice(status) }}</p>
    <p>存檔政策會在送出時重新判定。</p>
    <template v-if="error" #error><GmError :code="error.code" :message="error.message" title="操作失敗" /><GmConsoleResult :error="error" /></template>
  </GmConfirmDialog>
  <GmConsoleResult :result="result" />
</template>
