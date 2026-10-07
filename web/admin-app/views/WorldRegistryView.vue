<script setup>
// One registry's entries (gm-portal-s4-world-data §4.1): keys with their
// summary fields in stable key order, a text filter over keys and string
// fields, and forward-only cursor paging. Registries never change while the
// server runs, so there is no refresh stamp; a new query restarts paging.
import { computed, inject, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import GmEntityLink from "../components/GmEntityLink.vue";
import GmError from "../components/GmError.vue";
import GmFilterBar from "../components/GmFilterBar.vue";
import GmPager from "../components/GmPager.vue";
import GmProvenanceNote from "../components/GmProvenanceNote.vue";
import GmTable from "../components/GmTable.vue";
import { LIST_DEFAULT_LIMIT } from "../lib/runtime.js";
import { WORLD_ROUTE, registryListPath } from "../lib/world.js";

const props = defineProps({
  registry: { type: String, required: true },
  query: { type: Object, default: () => ({}) },
});

const api = inject("gmApi");
const router = useRouter();

const FILTER_FIELDS = Object.freeze([
  Object.freeze({ key: "q", label: "搜尋條目", type: "text", placeholder: "比對 key 與文字欄位", mono: true }),
]);

const filters = ref({});
const state = reactive({
  status: "idle",
  items: [],
  meta: null,
  total: 0,
  nextCursor: null,
  page: 1,
  limit: LIST_DEFAULT_LIMIT,
  error: null,
});

async function load({ cursor = null, append = false } = {}) {
  state.status = "loading";
  try {
    const data = await api.get(
      registryListPath(props.registry, { cursor, limit: state.limit, q: filters.value.q ?? "" }),
    );
    state.items = append ? [...state.items, ...data.items] : data.items;
    state.meta = data.registry;
    state.total = data.total;
    state.nextCursor = data.next_cursor;
    state.page = append ? state.page + 1 : 1;
    state.status = "ready";
    state.error = null;
  } catch (error) {
    state.status = "error";
    state.error = error;
  }
}

function onFilters(next) {
  router.replace({ name: WORLD_ROUTE.registry, params: { registry: props.registry }, query: next.q ? { q: next.q } : {} });
}

function onLimit(limit) {
  state.limit = limit;
  load();
}

const summaryFields = computed(() => state.meta?.summary_fields ?? []);
const columns = computed(() => [
  { key: "key", label: "Key", mono: true },
  ...summaryFields.value.map((field) => ({ key: `f:${field}`, label: field, mono: true })),
]);
const rows = computed(() =>
  state.items.map((item) => ({
    key: item.key,
    label: item.label,
    ...Object.fromEntries(item.summary.map((entry) => [`f:${entry.field}`, entry.value])),
  })),
);

function display(value) {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

watch(
  () => [props.registry, props.query.q],
  () => {
    filters.value = props.query.q ? { q: String(props.query.q) } : {};
    state.items = [];
    state.nextCursor = null;
    load();
  },
  { immediate: true },
);
</script>

<template>
  <div class="gm-world-list">
    <nav class="gm-crumbs" aria-label="位置">
      <RouterLink :to="{ name: WORLD_ROUTE.home }">世界資料</RouterLink>
      <span aria-hidden="true">／</span>
      <span v-if="state.meta">{{ state.meta.group }}</span>
      <span v-if="state.meta" aria-hidden="true">／</span>
      <span aria-current="page">{{ state.meta?.label ?? registry }}</span>
    </nav>

    <GmError
      v-if="state.status === 'error' && state.error?.code === 'registry_not_found'"
      title="找不到這個登錄表"
      :message="state.error.message"
      :code="state.error.code"
    >
      <template #actions>
        <RouterLink class="ui-btn ui-btn--sm" :to="{ name: WORLD_ROUTE.home }">回到世界資料</RouterLink>
      </template>
    </GmError>

    <template v-else>
      <header class="gm-world-list__head">
        <div class="gm-world-list__titles">
          <p class="gm-world-list__eyebrow">{{ state.meta?.group ?? "世界資料" }}</p>
          <h2 class="gm-world-list__title">
            {{ state.meta?.label ?? registry }}
            <span class="gm-chip">{{ registry }}</span>
          </h2>
        </div>
        <p v-if="state.meta" class="gm-world-list__total">
          共 <span class="gm-num">{{ state.meta.entry_count }}</span> 筆條目
          <template v-if="filters.q">，符合 <span class="gm-num">{{ state.total }}</span> 筆</template>
        </p>
      </header>

      <GmProvenanceNote v-if="state.meta" :path="state.meta.source_path" variant="loaded" />

      <GmFilterBar
        :fields="FILTER_FIELDS"
        :model-value="filters"
        :busy="state.status === 'loading'"
        caption="條目篩選"
        @change="onFilters"
      />

      <p v-if="state.status === 'loading' && state.items.length === 0" class="gm-skeleton" style="width: 60%"></p>

      <GmError
        v-else-if="state.status === 'error'"
        title="無法載入條目"
        :message="state.error.message"
        :code="state.error.code"
      >
        <template #actions>
          <button type="button" class="ui-btn ui-btn--sm" @click="load()">重試</button>
        </template>
      </GmError>

      <template v-else>
        <GmTable
          :columns="columns"
          :rows="rows"
          row-key="key"
          :caption="`${state.meta?.label ?? registry}條目`"
          caption-hidden
          :empty-title="filters.q ? `沒有符合「${filters.q}」的條目` : '沒有條目'"
          empty-message="調整搜尋文字，或回到世界資料總覽。"
        >
          <template #cell-key="{ row }">
            <span class="gm-world-list__key">
              <GmEntityLink :link="{ kind: 'registry', registry, id: row.key }" :label="row.key" />
              <span v-if="row.label" class="gm-world-list__label">{{ row.label }}</span>
            </span>
          </template>
          <template v-for="field in summaryFields" :key="field" #[`cell-f:${field}`]="{ value }">
            <span class="gm-world-list__cell" :title="display(value)">{{ display(value) }}</span>
          </template>
        </GmTable>
        <GmPager
          :next-cursor="state.nextCursor"
          :limit="state.limit"
          :shown="state.items.length"
          :page="state.page"
          :busy="state.status === 'loading'"
          @more="load({ cursor: state.nextCursor, append: true })"
          @limit="onLimit"
          @first="load()"
        />
      </template>
    </template>
  </div>
</template>

<style scoped>
.gm-world-list {
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

.gm-world-list__head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--sp-3);
}

.gm-world-list__titles {
  min-width: 0;
}

.gm-world-list__eyebrow {
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  color: var(--gold-400);
}

.gm-world-list__title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-3);
  font-family: var(--f-serif);
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--paper-50);
}

.gm-world-list__total {
  font-size: var(--text-sm);
  color: var(--paper-400);
}

.gm-world-list__key {
  display: grid;
  gap: 1px;
  font-weight: 600;
}

.gm-world-list__label {
  font-family: var(--f-serif);
  font-size: var(--text-xs);
  font-weight: 400;
  color: var(--paper-400);
}

.gm-world-list__cell {
  display: -webkit-box;
  max-width: 42ch;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow-wrap: anywhere;
}
</style>
