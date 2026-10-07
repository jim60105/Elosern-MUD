<script setup>
// The NPC 對話 tab (gm-portal-s3-runtime-state §5).
//
// Dialogue epochs and frames, grouped by player through the pure read query.
// Opening a player's group asks for that player's epochs and frames, whose
// rows link back to the retained S2 call drawer when a frame recorded a
// call id — no dialogue context is assembled and no correspondence is
// settled to render this tab.
import { computed, onMounted, reactive, ref } from "vue";
import GmEntityListTable from "./GmEntityListTable.vue";
import GmError from "./GmError.vue";
import GmPager from "./GmPager.vue";
import GmSectionView from "./GmSectionView.vue";
import { LIST_DEFAULT_LIMIT, listPath, ownerQuery } from "../lib/runtime.js";

const props = defineProps({
  npcDbref: { type: String, required: true },
  api: { type: Object, required: true },
});

const emit = defineEmits(["open-call"]);

const list = reactive({
  status: "idle",
  items: [],
  nextCursor: null,
  page: 1,
  limit: LIST_DEFAULT_LIMIT,
  error: null,
  loadedAt: null,
});
const expanded = reactive({});
const refreshing = ref(false);

const owner = computed(() => ({ owner: `#${props.npcDbref}` }));

function detailOf(player) {
  return (expanded[player] ??= { status: "idle", data: null, error: null });
}

async function load({ cursor = null, append = false } = {}) {
  list.status = "loading";
  try {
    const data = await props.api.get(
      listPath("dialogue", { cursor, limit: list.limit, filters: owner.value }),
    );
    list.items = append ? [...list.items, ...data.items] : data.items;
    list.nextCursor = data.next_cursor;
    list.page = append ? list.page + 1 : 1;
    list.status = "ready";
    list.error = null;
    list.loadedAt = Date.now() / 1000;
  } catch (error) {
    list.status = "error";
    list.error = error;
  }
}

async function reload() {
  refreshing.value = true;
  try {
    await load();
  } finally {
    refreshing.value = false;
  }
}

function onLimit(limit) {
  list.limit = limit;
  load();
}

defineExpose({ reload });

async function toggle(player) {
  const state = detailOf(player);
  if (state.status === "ready" || state.status === "loading") {
    state.status = "idle";
    return;
  }
  state.status = "loading";
  try {
    const query = new URLSearchParams(owner.value).toString();
    state.data = await props.api.get(`/state/dialogue/${encodeURIComponent(player)}?${query}`);
    state.status = "ready";
    state.error = null;
  } catch (error) {
    state.status = "error";
    state.error = error;
  }
}

onMounted(load);
</script>

<template>
  <div class="gm-dialogue">
    <div class="gm-dialogue__head">
      <h3 class="gm-dialogue__title">對話紀元</h3>
      <span v-if="list.loadedAt" class="gm-dialogue__hint">依玩家分組</span>
      <button
        type="button"
        class="ui-btn ui-btn--ghost ui-btn--sm gm-dialogue__refresh"
        :aria-disabled="refreshing ? 'true' : null"
        @click="!refreshing && reload()"
      >
        重新載入
      </button>
    </div>

    <p v-if="list.status === 'loading' && list.items.length === 0" class="gm-skeleton" style="width: 50%"></p>
    <GmError
      v-else-if="list.error"
      title="無法載入對話"
      :message="list.error.message"
      :code="list.error.code"
    >
      <template #actions>
        <button type="button" class="ui-btn ui-btn--sm" @click="load">重試</button>
      </template>
    </GmError>
    <template v-else>
      <GmEntityListTable
        :rows="list.items"
        kind="dialogue"
        caption="對話紀元（依玩家分組）"
        extra-column="展開"
        empty-title="沒有對話紀錄"
        empty-message="此 NPC 尚未與任何玩家建立對話紀元。"
        @open-call="emit('open-call', $event)"
      >
        <template #extra="{ row }">
          <button
            type="button"
            class="ui-btn ui-btn--ghost ui-btn--sm"
            :aria-expanded="detailOf(row.id).status !== 'idle' ? 'true' : 'false'"
            @click="toggle(row.id)"
          >
            {{ detailOf(row.id).status === "idle" ? "展開紀元" : "收合" }}
          </button>
        </template>
      </GmEntityListTable>

      <div v-for="row in list.items" :key="row.id">
        <template v-if="detailOf(row.id).status !== 'idle'">
          <p v-if="detailOf(row.id).status === 'loading'" class="gm-skeleton" style="width: 45%"></p>
          <GmError
            v-else-if="detailOf(row.id).error"
            compact
            live="off"
            title="無法載入對話明細"
            :message="detailOf(row.id).error.message"
            :code="detailOf(row.id).error.code"
          />
          <div v-else class="gm-dialogue__sections">
            <GmSectionView
              v-for="section in detailOf(row.id).data.sections"
              :key="section.key"
              :section="section"
              @open-call="emit('open-call', $event)"
            />
          </div>
        </template>
      </div>
      <GmPager
        :next-cursor="list.nextCursor"
        :limit="list.limit"
        :shown="list.items.length"
        :page="list.page"
        :busy="list.status === 'loading'"
        @more="load({ cursor: list.nextCursor, append: true })"
        @limit="onLimit"
        @first="load()"
      />
    </template>
  </div>
</template>

<style scoped>
.gm-dialogue {
  display: grid;
  gap: var(--sp-3);
  min-width: 0;
}

.gm-dialogue__head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-3);
}

.gm-dialogue__title {
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--paper-100);
}

.gm-dialogue__hint {
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  color: var(--paper-500);
}

.gm-dialogue__refresh {
  margin-left: auto;
}

.gm-dialogue__sections {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
  gap: var(--sp-4);
  margin: var(--sp-2) 0 var(--sp-4);
  padding: var(--sp-4);
  background: color-mix(in srgb, var(--ink-820) 60%, transparent);
  border: 1px dashed var(--ink-700);
  border-radius: var(--radius-sm);
}
</style>
