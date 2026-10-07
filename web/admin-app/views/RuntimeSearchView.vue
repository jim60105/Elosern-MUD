<script setup>
// Global runtime search (gm-portal-s3-runtime-state §6): an exact #dbref opens
// its object (or raw inspection when uncurated); other text returns object-key
// matches, then quest ids, then narrative source ids, in that precedence. The
// matched tier is shown verbatim so an operator can see which rule answered.
import { computed, inject, reactive, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import GmEntityLink from "../components/GmEntityLink.vue";
import GmError from "../components/GmError.vue";
import { kindLabel, searchPath } from "../lib/runtime.js";

const MATCHED_LABELS = {
  dbref: "精確 dbref",
  object_key: "物件鍵",
  quest_id: "任務編號",
  source_id: "來源識別",
};

const api = inject("gmApi");
const route = useRoute();
const router = useRouter();

const query = ref(String(route.query.q ?? ""));
const state = reactive({ status: "idle", results: [], error: null });

const trimmed = computed(() => query.value.trim());

async function run(value) {
  const text = String(value ?? "").trim();
  if (!text) {
    state.status = "idle";
    state.results = [];
    state.error = null;
    return;
  }
  state.status = "loading";
  try {
    const data = await api.get(searchPath(text));
    state.results = data.results;
    state.status = "ready";
    state.error = null;
  } catch (error) {
    state.status = "error";
    state.error = error;
    state.results = [];
  }
}

function submit() {
  const text = trimmed.value;
  if (!text) return;
  router.replace({ name: "runtime-search", query: { q: text } });
  run(text);
}

watch(
  () => route.query.q,
  (value) => {
    if (value !== undefined) query.value = String(value);
    run(value);
  },
  { immediate: true },
);
</script>

<template>
  <div class="gm-search">
    <header class="gm-search__head">
      <p class="gm-search__eyebrow">執行期狀態</p>
      <h2 class="gm-search__title">全域搜尋</h2>
      <p class="gm-search__blurb">依序比對：精確 #dbref → 物件鍵 → 任務編號 → 來源識別。</p>
    </header>

    <form class="gm-search__form" role="search" @submit.prevent="submit">
      <input
        v-model="query"
        class="gm-search__input gm-mono"
        type="search"
        name="q"
        placeholder="#12、物件鍵、任務編號或來源識別"
        aria-label="搜尋文字"
      >
      <button type="submit" class="ui-btn ui-btn--sm" :aria-disabled="trimmed ? null : 'true'">
        搜尋
      </button>
    </form>

    <p v-if="state.status === 'loading'" class="gm-skeleton" style="width: 45%"></p>

    <GmError
      v-else-if="state.error"
      :title="state.error.code === 'invalid_query' ? '請輸入查詢文字' : '搜尋失敗'"
      :message="state.error.message"
      :code="state.error.code"
    />

    <p v-else-if="state.status === 'ready' && state.results.length === 0" class="gm-search__empty">
      沒有符合「{{ trimmed }}」的結果。
    </p>

    <ul v-else-if="state.results.length" class="gm-search__results">
      <li v-for="result in state.results" :key="`${result.matched}-${result.kind}-${result.id}`" class="gm-search__result">
        <span class="gm-search__tier gm-chip">{{ MATCHED_LABELS[result.matched] ?? result.matched }}</span>
        <span class="gm-search__kind">{{ kindLabel(result.kind) }}</span>
        <GmEntityLink class="gm-search__link" :link="result.link" :label="result.label" />
        <span class="gm-search__id gm-mono">{{ result.kind === "object" ? `#${result.id}` : result.id }}</span>
      </li>
    </ul>

    <RouterLink class="gm-search__back" :to="{ name: 'runtime-home' }">← 回到執行期狀態</RouterLink>
  </div>
</template>

<style scoped>
.gm-search {
  display: grid;
  gap: var(--sp-4);
  min-width: 0;
}

.gm-search__eyebrow {
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  color: var(--gold-400);
}

.gm-search__title {
  font-family: var(--f-serif);
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--paper-50);
}

.gm-search__blurb {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-search__form {
  display: flex;
  gap: var(--sp-3);
  padding: var(--sp-4);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-search__input {
  flex: 1 1 auto;
  min-width: 0;
  min-height: 32px;
  padding: 0 var(--sp-3);
  font-size: var(--text-sm);
  color: var(--paper-100);
  background: var(--ink-950);
  border: var(--line);
  border-radius: var(--radius-sm);
}

.gm-search__input:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-search__empty {
  padding: var(--sp-4);
  font-size: var(--text-sm);
  color: var(--paper-500);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-search__results {
  display: grid;
  gap: var(--sp-1);
  padding: 0;
  list-style: none;
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}

.gm-search__result {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-3);
  padding: var(--sp-3) var(--sp-4);
  border-bottom: 1px solid var(--ink-700);
}

.gm-search__result:last-child {
  border-bottom: 0;
}

.gm-search__tier {
  flex: none;
  color: var(--gold-300);
}

.gm-search__kind {
  flex: none;
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--paper-400);
}

.gm-search__id {
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-search__back {
  font-size: var(--text-sm);
  color: var(--paper-500);
  text-decoration: none;
}

.gm-search__back:hover {
  color: var(--gold-300);
}
</style>
