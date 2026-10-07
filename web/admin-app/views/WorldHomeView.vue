<script setup>
// 世界資料 home (gm-portal-s4-world-data §4.1/§4.2): the loaded registries
// grouped by display group, cross-registry search (every match, no paging),
// and the YAML source files the viewer can open. The search text lives in
// ``?q=`` so a result list survives reload and history.
import { computed, inject, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import GmEmpty from "../components/GmEmpty.vue";
import GmEntityLink from "../components/GmEntityLink.vue";
import GmError from "../components/GmError.vue";
import GmPanel from "../components/GmPanel.vue";
import GmProvenanceNote from "../components/GmProvenanceNote.vue";
import GmStatusBadge from "../components/GmStatusBadge.vue";
import {
  SOURCE_GROUPS,
  WORLD_ROUTE,
  groupHits,
  inventoryPath,
  registryTarget,
  searchPath,
  sourceTarget,
  sourcesPath,
} from "../lib/world.js";

const api = inject("gmApi");
const route = useRoute();
const router = useRouter();

//: Search hit groups longer than this collapse behind a disclosure.
const HIT_PREVIEW = 24;

const inventory = reactive({ status: "loading", data: null, error: null });
const sources = reactive({ status: "loading", items: [], error: null });
const search = reactive({ status: "idle", query: "", items: [], error: null });
const draft = ref(String(route.query.q ?? ""));
const openGroups = ref(new Set());

async function loadInventory() {
  inventory.status = "loading";
  try {
    inventory.data = await api.get(inventoryPath());
    inventory.status = "ready";
    inventory.error = null;
  } catch (error) {
    inventory.status = "error";
    inventory.error = error;
  }
}

async function loadSources() {
  sources.status = "loading";
  try {
    sources.items = (await api.get(sourcesPath())).items;
    sources.status = "ready";
    sources.error = null;
  } catch (error) {
    sources.status = "error";
    sources.error = error;
  }
}

async function runSearch(query) {
  search.query = query;
  openGroups.value = new Set();
  if (!query) {
    search.status = "idle";
    search.items = [];
    return;
  }
  search.status = "loading";
  try {
    search.items = (await api.get(searchPath(query))).items;
    search.status = "ready";
    search.error = null;
  } catch (error) {
    search.status = "error";
    search.error = error;
  }
}

function submit() {
  const query = draft.value.trim();
  router.push({ name: WORLD_ROUTE.home, query: query ? { q: query } : {} });
}

function clearSearch() {
  draft.value = "";
  router.push({ name: WORLD_ROUTE.home, query: {} });
}

function toggleGroup(registry) {
  const next = new Set(openGroups.value);
  if (next.has(registry)) next.delete(registry);
  else next.add(registry);
  openGroups.value = next;
}

const registries = computed(() => inventory.data?.items ?? []);
const byName = computed(() => Object.fromEntries(registries.value.map((item) => [item.name, item])));
const groups = computed(() =>
  (inventory.data?.groups ?? [])
    .map((label, index) => ({
      label,
      ordinal: String(index + 1).padStart(2, "0"),
      anchor: `group-${index + 1}`,
      items: registries.value.filter((item) => item.group === label),
    }))
    .filter((group) => group.items.length > 0),
);
const totalEntries = computed(() => registries.value.reduce((sum, item) => sum + item.entry_count, 0));
const hitGroups = computed(() => groupHits(search.items));
const sourceColumns = computed(() =>
  SOURCE_GROUPS.map((group) => ({ ...group, items: sources.items.filter((item) => item.group === group.key) })),
);

function hitKeys(group) {
  return openGroups.value.has(group.registry) ? group.keys : group.keys.slice(0, HIT_PREVIEW);
}

loadInventory();
loadSources();
watch(
  () => route.query.q,
  (value) => {
    draft.value = String(value ?? "");
    runSearch(String(value ?? "").trim());
  },
  { immediate: true },
);
</script>

<template>
  <div class="gm-world-home">
    <header class="gm-world-home__head">
      <div>
        <p class="gm-world-home__eyebrow">世界資料</p>
        <h2 class="gm-world-home__title">已載入的登錄表</h2>
      </div>
      <p v-if="inventory.status === 'ready'" class="gm-world-home__totals">
        <span class="gm-num">{{ registries.length }}</span> 個登錄表 ·
        共 <span class="gm-num">{{ totalEntries.toLocaleString("zh-TW") }}</span> 筆條目
      </p>
    </header>

    <GmProvenanceNote path="world/lore/registry_index.py" variant="loaded" />

    <form class="gm-world-search" role="search" @submit.prevent="submit">
      <label class="gm-world-search__label" for="gm-world-search-input">
        <span class="gm-world-search__glyph" aria-hidden="true">⌕</span>
        跨登錄表搜尋
      </label>
      <input
        id="gm-world-search-input"
        v-model="draft"
        class="gm-world-search__input"
        type="search"
        maxlength="200"
        autocomplete="off"
        spellcheck="false"
        placeholder="輸入條目 key 或文字欄位內容"
      >
      <button type="submit" class="ui-btn ui-btn--sm">搜尋</button>
      <p class="gm-world-search__hint">比對所有登錄表的 key 與每個文字欄位（含巢狀資料），列出全部符合的條目。</p>
    </form>

    <GmPanel
      v-if="search.status !== 'idle'"
      title="搜尋結果"
      :description="search.status === 'ready' ? `共 ${search.items.length} 筆符合「${search.query}」` : `搜尋「${search.query}」`"
      :busy="search.status === 'loading'"
    >
      <template #actions>
        <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm" @click="clearSearch">清除搜尋</button>
      </template>
      <p v-if="search.status === 'loading'" class="gm-visually-hidden" role="status">搜尋中…</p>
      <div v-if="search.status === 'loading'" class="gm-world-home__skeletons" aria-hidden="true">
        <p class="gm-skeleton" style="width: 42%"></p>
        <p class="gm-skeleton" style="width: 68%"></p>
        <p class="gm-skeleton" style="width: 55%"></p>
      </div>
      <GmError
        v-else-if="search.status === 'error'"
        compact
        title="搜尋失敗"
        :message="search.error.message"
        :code="search.error.code"
      >
        <template #actions>
          <button type="button" class="ui-btn ui-btn--sm" @click="runSearch(search.query)">重試</button>
        </template>
      </GmError>
      <GmEmpty
        v-else-if="hitGroups.length === 0"
        title="沒有符合的條目"
        message="試試較短的關鍵字，或改用條目 key。"
      />
      <div v-else class="gm-world-hits">
        <p class="gm-visually-hidden" role="status">共 {{ search.items.length }} 筆符合</p>
        <section v-for="group in hitGroups" :key="group.registry" class="gm-world-hits__group">
          <h3 class="gm-world-hits__heading">
            <RouterLink class="gm-world-hits__registry" :to="registryTarget(group.registry, { q: search.query })">
              {{ byName[group.registry]?.label ?? group.registry }}
            </RouterLink>
            <span class="gm-chip">{{ group.registry }}</span>
            <span class="gm-world-hits__count"><span class="gm-num">{{ group.keys.length }}</span> 筆</span>
          </h3>
          <ul class="gm-world-hits__keys">
            <li v-for="key in hitKeys(group)" :key="key">
              <GmEntityLink :link="{ kind: 'registry', registry: group.registry, id: key }" :label="key" />
            </li>
          </ul>
          <button
            v-if="group.keys.length > HIT_PREVIEW"
            type="button"
            class="ui-btn ui-btn--ghost ui-btn--sm"
            :aria-expanded="openGroups.has(group.registry) ? 'true' : 'false'"
            @click="toggleGroup(group.registry)"
          >
            {{ openGroups.has(group.registry) ? "收合" : `顯示其餘 ${group.keys.length - HIT_PREVIEW} 筆` }}
          </button>
        </section>
      </div>
    </GmPanel>

    <div v-if="inventory.status === 'loading'" class="gm-world-home__loading" aria-busy="true">
      <p class="gm-skeleton" style="width: 24%"></p>
      <div class="gm-world-cards">
        <p v-for="n in 3" :key="n" class="gm-skeleton gm-world-home__card-skeleton"></p>
      </div>
    </div>
    <GmError
      v-else-if="inventory.status === 'error'"
      title="無法載入登錄表索引"
      :message="inventory.error.message"
      :code="inventory.error.code"
    >
      <template #actions>
        <button type="button" class="ui-btn ui-btn--sm" @click="loadInventory">重試</button>
      </template>
    </GmError>
    <template v-else>
      <nav class="gm-world-toc" aria-label="登錄表分組">
        <a v-for="group in groups" :key="group.anchor" class="gm-world-toc__link" :href="`#${group.anchor}`">
          {{ group.label }} <span class="gm-num">{{ group.items.length }}</span>
        </a>
      </nav>

      <section
        v-for="group in groups"
        :id="group.anchor"
        :key="group.anchor"
        class="gm-world-group"
        :aria-labelledby="`${group.anchor}-title`"
      >
        <h3 :id="`${group.anchor}-title`" class="gm-world-group__heading">
          <span class="gm-world-group__ordinal" aria-hidden="true">{{ group.ordinal }}</span>
          <span class="gm-world-group__label">{{ group.label }}</span>
          <span class="gm-world-group__rule" aria-hidden="true"></span>
          <span class="gm-world-group__count">{{ group.items.length }} 個登錄表</span>
        </h3>
        <ul class="gm-world-cards">
          <li v-for="item in group.items" :key="item.name">
            <RouterLink class="gm-world-card" :to="registryTarget(item.name)">
              <span class="gm-visually-hidden">{{ item.label }}，{{ item.name }}，{{ item.entry_count }} 筆</span>
              <span class="gm-world-card__label" aria-hidden="true">{{ item.label }}</span>
              <span class="gm-world-card__count" aria-hidden="true">
                <span class="gm-world-card__number" :class="{ 'is-zero': item.entry_count === 0 }">{{ item.entry_count }}</span>
                <span class="gm-world-card__unit">筆</span>
              </span>
              <span class="gm-world-card__name gm-mono" aria-hidden="true">{{ item.name }}</span>
              <span class="gm-world-card__path gm-mono" :title="item.source_path" aria-hidden="true">{{ item.source_path }}</span>
            </RouterLink>
          </li>
        </ul>
      </section>
    </template>

    <GmPanel title="原始檔" description="規則書與提示詞的 YAML 原始檔，以唯讀方式顯示磁碟上的內容。">
      <p v-if="sources.status === 'loading'" class="gm-skeleton" style="width: 50%"></p>
      <GmError
        v-else-if="sources.status === 'error'"
        compact
        title="無法載入原始檔清單"
        :message="sources.error.message"
        :code="sources.error.code"
      />
      <div v-else class="gm-world-sources">
        <section v-for="column in sourceColumns" :key="column.key" class="gm-world-sources__column">
          <h3 class="gm-world-sources__heading">
            {{ column.label }}
            <GmStatusBadge v-if="column.key === 'prompts'" status="neutral" label="可重新載入" />
          </h3>
          <p v-if="column.items.length === 0" class="gm-muted">（沒有檔案）</p>
          <ul v-else class="gm-world-sources__list">
            <li v-for="item in column.items" :key="item.name">
              <RouterLink class="gm-world-sources__link gm-mono" :to="sourceTarget(item.name)" :title="item.source_path">
                {{ item.name.split("/").pop() }}
              </RouterLink>
            </li>
          </ul>
        </section>
      </div>
    </GmPanel>
  </div>
</template>

<style scoped>
.gm-world-home {
  display: grid;
  gap: var(--sp-5);
  min-width: 0;
}

.gm-world-home__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-3);
}

.gm-world-home__eyebrow {
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  color: var(--gold-400);
}

.gm-world-home__title {
  font-family: var(--f-serif);
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--paper-50);
}

.gm-world-home__totals {
  font-size: var(--text-sm);
  color: var(--paper-400);
}

.gm-world-home__totals .gm-num {
  color: var(--paper-100);
}

.gm-world-search {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--sp-2) var(--sp-3);
  padding: var(--sp-4) var(--sp-5);
  background:
    linear-gradient(90deg, var(--gold-glow), transparent 60%) no-repeat,
    var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
}

.gm-world-search:focus-within {
  border-color: var(--gold-600);
}

.gm-world-search__label {
  display: inline-flex;
  align-items: baseline;
  gap: var(--sp-2);
  font-family: var(--f-serif);
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--paper-100);
  white-space: nowrap;
}

.gm-world-search__glyph {
  font-size: var(--text-lg);
  color: var(--gold-400);
}

.gm-world-search__input {
  min-width: 0;
  padding: var(--sp-2) var(--sp-3);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  color: var(--paper-50);
  background: var(--ink-950);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius-sm);
}

.gm-world-search__input::placeholder {
  font-family: var(--f-sans);
  color: var(--paper-500);
}

.gm-world-search__input:focus-visible {
  border-color: var(--gold-500);
  box-shadow: var(--focus);
  outline: none;
}

.gm-world-search__hint {
  grid-column: 1 / -1;
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-world-home__skeletons {
  display: grid;
  gap: var(--sp-2);
}

.gm-world-hits {
  display: grid;
  gap: var(--sp-4);
}

.gm-world-hits__group {
  display: grid;
  gap: var(--sp-2);
  padding-bottom: var(--sp-3);
  border-bottom: 1px dashed var(--ink-700);
}

.gm-world-hits__group:last-child {
  padding-bottom: 0;
  border-bottom: 0;
}

.gm-world-hits__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-2);
}

.gm-world-hits__registry {
  font-family: var(--f-serif);
  font-size: var(--text-md);
  font-weight: 600;
}

.gm-world-hits__count {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-world-hits__keys {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1) var(--sp-4);
  padding: 0;
  list-style: none;
}

.gm-world-toc {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.gm-world-toc__link {
  display: inline-flex;
  align-items: baseline;
  gap: var(--sp-2);
  padding: 2px var(--sp-3);
  font-size: var(--text-sm);
  color: var(--paper-200);
  text-decoration: none;
  background: var(--ink-860);
  border: 1px solid var(--ink-700);
  border-radius: var(--radius-pill);
  transition: border-color var(--motion-fast) var(--ease-standard);
}

.gm-world-toc__link .gm-num {
  font-size: var(--text-xs);
  color: var(--gold-500);
}

.gm-world-toc__link:hover,
.gm-world-toc__link:focus-visible {
  color: var(--paper-50);
  border-color: var(--gold-600);
  outline: none;
}

.gm-world-toc__link:focus-visible {
  box-shadow: var(--focus);
}

.gm-world-group {
  display: grid;
  gap: var(--sp-3);
  scroll-margin-top: var(--sp-6);
}

.gm-world-group__heading {
  display: flex;
  align-items: baseline;
  gap: var(--sp-3);
}

.gm-world-group__ordinal {
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--gold-500);
}

.gm-world-group__label {
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--paper-50);
}

.gm-world-group__rule {
  flex: 1;
  align-self: center;
  border-bottom: 1px solid var(--ink-700);
}

.gm-world-group__count {
  font-size: var(--text-xs);
  color: var(--paper-500);
  white-space: nowrap;
}

.gm-world-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr));
  gap: var(--sp-3);
  padding: 0;
  list-style: none;
}

.gm-world-home__card-skeleton {
  height: 88px;
}

.gm-world-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    "label count"
    "name count"
    "path path";
  align-items: baseline;
  gap: 2px var(--sp-3);
  height: 100%;
  padding: var(--sp-3) var(--sp-4);
  color: var(--paper-100);
  text-decoration: none;
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius);
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}

.gm-world-card:hover {
  background: var(--ink-820);
  border-color: var(--gold-600);
}

.gm-world-card:focus-visible {
  box-shadow: var(--focus);
  outline: none;
}

.gm-world-card__label {
  grid-area: label;
  font-family: var(--f-serif);
  font-size: var(--text-md);
  font-weight: 600;
}

.gm-world-card__count {
  grid-area: count;
  align-self: center;
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
}

.gm-world-card__number {
  font-family: var(--f-mono);
  font-size: var(--text-xl);
  font-variant-numeric: tabular-nums;
  color: var(--paper-50);
}

.gm-world-card__number.is-zero {
  color: var(--paper-500);
}

.gm-world-card__unit {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-world-card__name {
  grid-area: name;
  font-size: var(--text-xs);
  color: var(--gold-500);
}

.gm-world-card__path {
  grid-area: path;
  margin-top: var(--sp-1);
  overflow: hidden;
  font-size: var(--text-xs);
  color: var(--paper-500);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-world-sources {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-5);
}

.gm-world-sources__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
  font-family: var(--f-serif);
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--paper-100);
}

.gm-world-sources__list {
  display: grid;
  gap: 2px;
  padding: 0;
  list-style: none;
}

.gm-world-sources__link {
  font-size: var(--text-sm);
}

@media (max-width: 859px) {
  .gm-world-search {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .gm-world-search__label {
    grid-column: 1 / -1;
  }

  .gm-world-sources {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
