<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue';
import GmConsolePrompt from './GmConsolePrompt.vue';
import { KIND_VERBS, VERB_FIELDS, NUMERIC_FIELDS, argumentsFor } from '../lib/console.js';
const props = defineProps({ kind: { type: String, required: true }, target: { type: String, required: true }, api: { type: Object, required: true } });
const emit = defineEmits(['done']);
const open = ref(false), verb = ref(''), request = ref(null), draft = reactive({});
const launcher = ref(null), drawer = ref(null);
watch(open, async (value) => {
  await nextTick();
  if (value) drawer.value?.focus();
  else launcher.value?.focus();
});
const verbs = computed(() => KIND_VERBS[props.kind] ?? []);
const fields = computed(() => VERB_FIELDS[verb.value] ?? []);
watch(() => [props.kind, props.target], () => { open.value = false; request.value = null; verb.value = verbs.value[0] ?? ''; }, { immediate: true });
function prepare() { request.value = { path: `/console/${verb.value}`, body: argumentsFor(verb.value, props.target, draft), label: `${verb.value} · ${props.target}` }; }
function done(result) { request.value = null; emit('done', result); }
</script>
<template>
  <button v-if="verbs.length" ref="launcher" type="button" class="ui-btn ui-btn--danger" :aria-expanded="open" @click="open = !open">主控台</button>
  <aside v-if="open" ref="drawer" class="gm-console-drawer" aria-label="主控台" tabindex="-1" @keydown.esc.stop="!request && (open = false)">
    <header><h3>主控台 · {{ target }}</h3><button type="button" class="ui-btn" @click="open = false">關閉</button></header>
    <form @submit.prevent="prepare">
      <label>操作<select v-model="verb"><option v-for="name in verbs" :key="name" :value="name">{{ name }}</option></select></label>
      <label v-for="field in fields" :key="field">{{ field }}<input v-model="draft[field]" :name="field" :type="NUMERIC_FIELDS.has(field) ? 'number' : 'text'" required :step="NUMERIC_FIELDS.has(field) ? '1' : undefined" /></label>
      <button type="submit" class="ui-btn ui-btn--danger">確認操作</button>
    </form>
  </aside>
  <GmConsolePrompt :request="request" :api="api" @cancel="request = null" @done="done" />
</template>
<style scoped>
.gm-console-drawer { position: fixed; right: 0; top: 0; height: 100dvh; overflow: auto; width: min(30rem, 90vw); z-index: 40; background: var(--ink-860); border: var(--line); padding: var(--sp-5); }
header, form, label { display: grid; gap: var(--sp-3); } form { margin-top: var(--sp-4); } input, select { color: var(--paper-100); background: var(--ink-950); padding: var(--sp-2); border: var(--line); }
</style>
