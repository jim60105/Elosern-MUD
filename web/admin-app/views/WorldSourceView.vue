<script setup>
// One YAML source file (gm-portal-s4-world-data §4.3/§4.5): the file as it is
// on disk, line-numbered and read-only. A prompt file also offers 重新載入,
// which re-reads ``prompts/`` into the in-memory prompt library through the
// loader and shows its diagnostics; it changes no world state or file, so it is
// a neutral action, never seal-red. Rulebook edits apply by restart only.
import { computed, inject, nextTick, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import GmError from "../components/GmError.vue";
import GmPanel from "../components/GmPanel.vue";
import GmProvenanceNote from "../components/GmProvenanceNote.vue";
import GmSourceText from "../components/GmSourceText.vue";
import GmStatusBadge from "../components/GmStatusBadge.vue";
import GmTable from "../components/GmTable.vue";
import { formatClock } from "../lib/format.js";
import { PROMPT_RELOAD_PATH, WORLD_ROUTE, joinParam, sourcePath, sourceTarget } from "../lib/world.js";

const api = inject("gmApi");
const route = useRoute();
const router = useRouter();

const name = computed(() => joinParam(route.params.name));
const highlight = computed(() => {
  const match = String(route.hash ?? "").match(/^#L(\d+)$/);
  return match ? Number(match[1]) : null;
});
const state = reactive({ status: "loading", data: null, error: null });
const reload = reactive({ status: "idle", result: null, at: null, error: null, stale: false });
const resultHeading = ref(null);

async function load() {
  state.status = "loading";
  try {
    state.data = await api.get(sourcePath(name.value));
    state.status = "ready";
    state.error = null;
  } catch (error) {
    state.status = "error";
    state.error = error;
  }
}

async function reloadPrompts() {
  if (reload.status === "loading") return;
  reload.status = "loading";
  reload.stale = Boolean(reload.result);
  try {
    reload.result = await api.post(PROMPT_RELOAD_PATH);
    reload.at = Date.now() / 1000;
    reload.error = null;
    reload.stale = false;
    reload.status = "ready";
  } catch (error) {
    reload.error = error;
    reload.status = "error";
  }
  await nextTick();
  resultHeading.value?.focus?.();
}

function selectLine(number) {
  router.replace({ path: route.path, query: route.query, hash: `#L${number}` });
}

const reloadable = computed(() => Boolean(state.data?.reloadable));
const fileName = computed(() => name.value.split("/").pop());
const unavailable = computed(() =>
  (reload.result?.unavailable ?? []).map((item) => ({ ...item, id: item.key })),
);
const UNAVAILABLE_COLUMNS = Object.freeze([
  { key: "key", label: "提示詞 key", mono: true },
  { key: "file", label: "檔案", mono: true },
  { key: "problem", label: "問題" },
]);

watch(name, () => {
  reload.status = "idle";
  reload.result = null;
  load();
}, { immediate: true });
</script>

<template>
  <div class="gm-world-source">
    <nav class="gm-crumbs" aria-label="位置">
      <RouterLink :to="{ name: WORLD_ROUTE.home }">世界資料</RouterLink>
      <span aria-hidden="true">／</span>
      <span>原始檔</span>
      <span aria-hidden="true">／</span>
      <span class="gm-mono" aria-current="page">{{ name }}</span>
    </nav>

    <header class="gm-world-source__head">
      <div class="gm-world-source__titles">
        <p class="gm-world-source__eyebrow">原始檔</p>
        <h2 class="gm-world-source__title gm-mono">{{ fileName }}</h2>
      </div>
      <div v-if="reloadable" class="gm-world-source__actions" :aria-busy="reload.status === 'loading' ? 'true' : null">
        <button
          type="button"
          class="ui-btn ui-btn--sm"
          aria-describedby="gm-world-source-reload-note"
          :aria-disabled="reload.status === 'loading' ? 'true' : null"
          @click="reloadPrompts"
        >
          <span class="gm-world-source__spin" :class="{ 'is-spinning': reload.status === 'loading' }" aria-hidden="true">↻</span>
          {{ reload.status === "loading" ? "重新載入中…" : "重新載入提示詞庫" }}
        </button>
      </div>
    </header>

    <GmError
      v-if="state.status === 'error'"
      :title="state.error.code === 'source_not_found' ? '找不到這個原始檔' : '無法載入原始檔'"
      :message="state.error.message"
      :code="state.error.code"
    >
      <template #actions>
        <RouterLink class="ui-btn ui-btn--sm" :to="{ name: WORLD_ROUTE.home }">回到世界資料</RouterLink>
      </template>
    </GmError>

    <template v-else>
      <div v-if="state.data" id="gm-world-source-reload-note">
        <GmProvenanceNote :path="state.data.source_path" :variant="reloadable ? 'reloadable' : 'disk'" />
      </div>

      <section
        v-if="reload.status !== 'idle'"
        class="gm-world-source__result"
        :class="{ 'is-stale': reload.stale || (reload.status === 'error' && reload.result) }"
      >
        <GmPanel title="重新載入結果" :busy="reload.status === 'loading'">
          <h3 ref="resultHeading" class="gm-visually-hidden" tabindex="-1">重新載入結果</h3>
          <p class="gm-visually-hidden" role="status">
            <template v-if="reload.status === 'ready'">
              重新載入完成：可用 {{ reload.result.available }} ／ 共 {{ reload.result.total }}
            </template>
            <template v-else-if="reload.status === 'error'">重新載入失敗</template>
          </p>
          <GmError
            v-if="reload.status === 'error'"
            compact
            title="重新載入失敗"
            :message="reload.error.message"
            :code="reload.error.code"
          >
            <template #actions>
              <button type="button" class="ui-btn ui-btn--sm" @click="reloadPrompts">重試</button>
            </template>
          </GmError>
          <p v-if="reload.status === 'loading'" class="gm-skeleton" style="width: 45%"></p>
          <div v-if="reload.result" class="gm-world-source__outcome">
            <p v-if="reload.stale || reload.status === 'error'" class="gm-muted">上一次結果</p>
            <div class="gm-world-source__summary">
              <GmStatusBadge
                :status="reload.result.outcome === 'ok' ? 'ok' : 'warn'"
                :label="reload.result.outcome === 'ok' ? '載入正常' : '部分不可用'"
              />
              <div class="gm-stats gm-world-source__stats">
                <div class="gm-stat">
                  <span class="gm-stat__value">{{ reload.result.available }}</span>
                  <span class="gm-stat__label">可用</span>
                </div>
                <div class="gm-stat">
                  <span class="gm-stat__value">{{ reload.result.total }}</span>
                  <span class="gm-stat__label">共</span>
                </div>
              </div>
              <p class="gm-world-source__meta">
                來源目錄 <code class="gm-chip">{{ reload.result.root }}</code>
                <template v-if="reload.at">· 重新載入於 <time class="gm-mono">{{ formatClock(reload.at) }}</time></template>
              </p>
            </div>
            <p v-if="unavailable.length === 0" class="gm-world-source__all-good">✓ 全部提示詞皆可用。</p>
            <template v-else>
              <p class="gm-world-source__degraded">
                這份載入結果已取代先前的提示詞庫：下列提示詞目前不可用，使用它們的功能會改走離線降級路徑，直到修正檔案並再次重新載入。
              </p>
              <GmTable
                :columns="UNAVAILABLE_COLUMNS"
                :rows="unavailable"
                row-key="key"
                caption="不可用的提示詞"
              >
                <template #cell-file="{ value }">
                  <RouterLink v-if="value" :to="sourceTarget(`prompts/${value}`)" class="gm-mono">{{ value }}</RouterLink>
                  <span v-else class="gm-muted">—</span>
              </template>
            </GmTable>
            </template>
          </div>
        </GmPanel>
      </section>

      <div v-if="state.status === 'loading'" class="gm-world-source__skeleton" aria-busy="true">
        <p v-for="n in 12" :key="n" class="gm-skeleton" :style="{ width: `${30 + ((n * 37) % 50)}%` }"></p>
      </div>
      <GmSourceText
        v-else-if="state.data"
        :text="state.data.text"
        :name="state.data.source_path"
        :highlight="highlight"
        @select-line="selectLine"
      />
      <p v-if="reloadable && state.status === 'ready'" class="gm-world-source__reread">
        <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm" @click="load">重新讀取檔案</button>
        <span class="gm-muted">重新載入只更新記憶體中的提示詞庫；檔案內容需另外重新讀取。</span>
      </p>
    </template>
  </div>
</template>

<style scoped>
.gm-world-source {
  display: grid;
  gap: var(--sp-4);
  min-width: 0;
}

.gm-crumbs {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-world-source__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-3);
}

.gm-world-source__titles {
  min-width: 0;
}

.gm-world-source__eyebrow {
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  color: var(--gold-400);
}

.gm-world-source__title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--paper-50);
  overflow-wrap: anywhere;
}

.gm-world-source__spin {
  display: inline-block;
}

.gm-world-source__spin.is-spinning {
  animation: gm-source-spin var(--motion-spin) linear infinite;
}

@keyframes gm-source-spin {
  to {
    transform: rotate(360deg);
  }
}

.gm-world-source__result {
  animation: gm-source-reveal var(--motion-reveal) var(--ease-enter);
}

.gm-world-source__result.is-stale .gm-world-source__outcome {
  opacity: 0.6;
}

@keyframes gm-source-reveal {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .gm-world-source__spin.is-spinning,
  .gm-world-source__result {
    animation: none;
  }
}

.gm-world-source__outcome {
  display: grid;
  gap: var(--sp-3);
  transition: opacity var(--motion-fast) var(--ease-standard);
}

.gm-world-source__summary {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-3) var(--sp-5);
}

.gm-world-source__stats {
  grid-template-columns: repeat(2, minmax(72px, auto));
}

.gm-world-source__meta {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-world-source__all-good {
  font-size: var(--text-sm);
  color: var(--ok);
}

.gm-world-source__degraded {
  padding-left: var(--sp-3);
  font-size: var(--text-xs);
  line-height: 1.7;
  color: var(--paper-300);
  border-left: 2px solid var(--warn);
}

.gm-world-source__skeleton {
  display: grid;
  gap: var(--sp-2);
}

.gm-world-source__reread {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-3);
  font-size: var(--text-xs);
}
</style>
