<script setup>
// 最近 LLM 呼叫: the newest buffered calls; each row opens the payload
// drawer through one real button (the only tab stop per row; a row click is
// forwarded to it). While the pointer or focus is inside the table, newly
// polled rows are held back behind a "有 n 筆新呼叫" control so a row never
// shifts under the operator's click.
import { computed, ref, watch } from "vue";
import GmPanel from "../../components/GmPanel.vue";
import GmStatusBadge from "../../components/GmStatusBadge.vue";
import GmTable from "../../components/GmTable.vue";
import SlotState from "./SlotState.vue";
import { resultBadge, slotError } from "../../lib/dashboard.js";
import { formatClock, formatMs, isoFromEpoch } from "../../lib/format.js";

const props = defineProps({
  calls: { type: [Array, Object], default: null },
  selectedId: { type: String, default: null },
});

const emit = defineEmits(["select"]);

const COLLAPSED_COUNT = 15;
const columns = [
  { key: "time", label: "時間" },
  { key: "layer", label: "層／設定檔" },
  { key: "result", label: "結果" },
  { key: "reason", label: "原因" },
  { key: "ms", label: "耗時", align: "end" },
  { key: "detail", label: "明細", align: "end" },
];

// Hold while either the pointer or keyboard focus is inside the table.
const pointerInside = ref(false);
const focusInside = ref(false);
const held = computed(() => pointerInside.value || focusInside.value);
const shown = ref(props.calls);
const arrived = ref(new Set());
const expanded = ref(false);

function keyOf(call) {
  return `${call.call_id}:${call.ts}`;
}

function apply(next) {
  const before = Array.isArray(shown.value) ? new Set(shown.value.map(keyOf)) : null;
  shown.value = next;
  arrived.value =
    before && Array.isArray(next) ? new Set(next.map(keyOf).filter((key) => !before.has(key))) : new Set();
}

watch(
  () => props.calls,
  (next) => {
    if (!held.value || !Array.isArray(next) || !Array.isArray(shown.value)) apply(next);
  },
);

const pendingCount = computed(() => {
  if (!held.value || !Array.isArray(props.calls) || !Array.isArray(shown.value)) return 0;
  const seen = new Set(shown.value.map(keyOf));
  return props.calls.filter((call) => !seen.has(keyOf(call))).length;
});

function catchUp() {
  if (!held.value && props.calls !== shown.value) apply(props.calls);
}

function pointerEnter() {
  pointerInside.value = true;
}

function pointerLeave() {
  pointerInside.value = false;
  catchUp();
}

function focusIn() {
  focusInside.value = true;
}

function focusOut(event) {
  if (event?.relatedTarget && event.currentTarget.contains(event.relatedTarget)) return;
  focusInside.value = false;
  catchUp();
}

function showNew() {
  apply(props.calls);
}

const rows = computed(() => {
  if (!Array.isArray(shown.value)) return [];
  const list = expanded.value ? shown.value : shown.value.slice(0, COLLAPSED_COUNT);
  return list.map((call) => ({
    id: keyOf(call),
    call,
    badge: resultBadge(call.result),
    layerText: call.profile && call.profile !== call.layer ? `${call.layer} / ${call.profile}` : call.layer,
    arrived: arrived.value.has(keyOf(call)),
  }));
});

const total = computed(() => (Array.isArray(shown.value) ? shown.value.length : 0));

function onRowClick(event) {
  const row = event.target.closest("tr");
  if (!row || event.target.closest("button")) return;
  row.querySelector("button[data-call-id]")?.click();
}

const panelValue = computed(() => (slotError(props.calls) ? props.calls : shown.value));
</script>

<template>
  <GmPanel
    title="最近 LLM 呼叫"
    description="點選任一筆以檢視請求與回應內容"
    :flush="Array.isArray(shown)"
  >
    <template #actions>
      <button
        v-if="pendingCount"
        type="button"
        class="ui-btn ui-btn--sm"
        data-testid="gm-calls-new"
        @click="showNew"
      >
        有 {{ pendingCount }} 筆新呼叫
      </button>
    </template>
    <SlotState :value="panelValue" :rows="6">
      <div
        class="gm-calls"
        data-testid="gm-calls-region"
        @pointerenter="pointerEnter"
        @pointerleave="pointerLeave"
        @focusin="focusIn"
        @focusout="focusOut"
        @click="onRowClick"
      >
        <GmTable
          :columns="columns"
          :rows="rows"
          caption="最近的 LLM 呼叫，最新在前"
          caption-hidden
          flush
          empty-title="本次啟動後尚無 LLM 呼叫"
          empty-message="遊戲觸發生成後，呼叫會出現在這裡。"
          data-testid="gm-recent-calls"
        >
          <template #cell-time="{ row }">
            <time class="gm-mono gm-calls__time" :class="{ 'gm-arrived': row.arrived }" :datetime="isoFromEpoch(row.call.ts)">
              {{ formatClock(row.call.ts) }}
            </time>
          </template>
          <template #cell-layer="{ row }">
            <span class="gm-calls__layer" :title="row.layerText">
              <span class="gm-mono gm-calls__layer-name">{{ row.call.layer }}</span>
              <span v-if="row.call.profile && row.call.profile !== row.call.layer" class="gm-mono gm-calls__profile">{{ row.call.profile }}</span>
            </span>
          </template>
          <template #cell-result="{ row }">
            <GmStatusBadge :status="row.badge.status" :label="row.badge.label" />
          </template>
          <template #cell-reason="{ row }">
            <span v-if="row.call.reason" class="gm-chip" :title="row.call.reason">{{ row.call.reason }}</span>
            <span v-else class="gm-muted" aria-label="無資料">—</span>
          </template>
          <template #cell-ms="{ row }"><span class="gm-num">{{ formatMs(row.call.ms) }}</span></template>
          <template #cell-detail="{ row }">
            <button
              type="button"
              class="ui-btn ui-btn--ghost ui-btn--sm gm-calls__open"
              :class="{ 'is-selected': row.call.call_id === selectedId }"
              :data-call-id="row.call.call_id"
              :disabled="!row.call.call_id"
              :aria-label="`檢視 ${formatClock(row.call.ts)} ${row.call.layer ?? ''} 呼叫明細`"
              @click="emit('select', row.call.call_id)"
            >
              檢視
            </button>
          </template>
        </GmTable>
        <div v-if="total > COLLAPSED_COUNT" class="gm-calls__more">
          <button
            type="button"
            class="ui-btn ui-btn--ghost ui-btn--sm"
            :aria-expanded="expanded ? 'true' : 'false'"
            @click="expanded = !expanded"
          >
            {{ expanded ? "收合" : `顯示全部（${total} 筆）` }}
          </button>
        </div>
      </div>
    </SlotState>
  </GmPanel>
</template>

<style scoped>
.gm-calls :deep(tbody tr) {
  cursor: pointer;
}

.gm-calls__time {
  font-size: var(--text-sm);
  color: var(--paper-300);
  border-radius: var(--radius-sm);
}

.gm-calls__layer {
  display: grid;
  gap: 1px;
  min-width: 0;
}

.gm-calls__layer-name {
  font-size: var(--text-sm);
  color: var(--paper-100);
}

.gm-calls__profile {
  max-width: 24ch;
  overflow: hidden;
  font-size: var(--text-xs);
  color: var(--paper-500);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-calls__open.is-selected {
  color: var(--gold-400);
  border-color: var(--gold-600);
}

.gm-calls__more {
  display: flex;
  justify-content: center;
  padding: var(--sp-3);
  border-top: 1px solid var(--ink-700);
}
</style>
