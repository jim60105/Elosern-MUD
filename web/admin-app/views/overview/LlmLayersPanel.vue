<script setup>
// LLM 各層狀態: passive per-layer health from the buffered llm_call events
// plus static profile configuration. The counts describe the retained
// window only (stated in the caption), never lifetime totals.
import { computed } from "vue";
import GmMeter from "../../components/GmMeter.vue";
import GmPanel from "../../components/GmPanel.vue";
import GmStatusBadge from "../../components/GmStatusBadge.vue";
import GmTable from "../../components/GmTable.vue";
import SlotState from "./SlotState.vue";
import { degradeRate, formatCount, sortLayers } from "../../lib/dashboard.js";
import { formatAge, formatMs, formatPercent, isoFromEpoch } from "../../lib/format.js";

const props = defineProps({
  layers: { type: [Array, Object], default: null },
  window: { type: Object, default: null },
  now: { type: Number, required: true },
});

const columns = [
  { key: "layer", label: "層" },
  { key: "status", label: "狀態" },
  { key: "calls", label: "呼叫", align: "end" },
  { key: "mix", label: "結果分布" },
  { key: "rate", label: "降級率" },
  { key: "mean", label: "平均", align: "end" },
  { key: "p95", label: "p95", align: "end" },
  { key: "last", label: "最近成功", align: "end" },
];

const rows = computed(() =>
  Array.isArray(props.layers)
    ? sortLayers(props.layers).map(({ layer, state }) => {
        const rate = degradeRate(layer);
        const reasons = Object.entries(layer.reasons ?? {}).sort((a, b) => b[1] - a[1]);
        return {
          id: layer.layer,
          layer,
          state,
          rate,
          rateText: layer.calls ? formatPercent((layer.degraded ?? 0) + (layer.rejected ?? 0), layer.calls) : "—",
          reasons: reasons.slice(0, 3),
          moreReasons: Math.max(0, reasons.length - 3),
        };
      })
    : [],
);

const caption = computed(() =>
  props.window ? `緩衝區保留 ${formatCount(props.window.retained)} / ${formatCount(props.window.capacity)} 筆呼叫` : "各層統計",
);
</script>

<template>
  <GmPanel
    title="LLM 各層狀態"
    description="統計範圍為緩衝區保留的呼叫，非啟動以來總數；不主動探測端點"
    :flush="Array.isArray(layers)"
  >
    <SlotState :value="layers" :rows="5">
      <GmTable
        :columns="columns"
        :rows="rows"
        :caption="caption"
        flush
        empty-title="沒有設定任何生成層"
        data-testid="gm-llm-layers"
      >
        <template #cell-layer="{ row }">
          <span class="gm-layer">
            <span class="gm-layer__name gm-mono">{{ row.layer.layer }}</span>
            <span class="gm-layer__model gm-mono" :title="`${row.layer.model} · ${row.layer.endpoint_host ?? '—'}`">
              {{ row.layer.model }} · {{ row.layer.endpoint_host ?? "—" }}
            </span>
          </span>
        </template>
        <template #cell-status="{ row }">
          <GmStatusBadge :status="row.state.status" :label="row.state.label" />
        </template>
        <template #cell-calls="{ row }">
          <span class="gm-num">{{ row.layer.calls ? formatCount(row.layer.calls) : "—" }}</span>
        </template>
        <template #cell-mix="{ row }">
          <div v-if="row.layer.calls" class="gm-mix">
            <GmMeter
              width="140px"
              :label="`成功 ${row.layer.ok}，降級 ${row.layer.degraded}，拒絕 ${row.layer.rejected}`"
              :segments="[
                { key: 'ok', value: row.layer.ok, tone: 'ok', pattern: 'solid' },
                { key: 'degraded', value: row.layer.degraded, tone: 'warn', pattern: 'hatch' },
                { key: 'rejected', value: row.layer.rejected, tone: 'crit', pattern: 'cross' },
              ]"
            />
            <span class="gm-mix__counts" aria-hidden="true">
              成功 {{ row.layer.ok }} · 降級 {{ row.layer.degraded }} · 拒絕 {{ row.layer.rejected }}
            </span>
            <span v-if="row.reasons.length" class="gm-mix__reasons">
              <span v-for="[reason, count] in row.reasons" :key="reason" class="gm-chip" :title="reason">{{ reason }} ×{{ count }}</span>
              <span v-if="row.moreReasons" class="gm-muted gm-mix__more">另 {{ row.moreReasons }} 種</span>
            </span>
          </div>
          <span v-else class="gm-muted" aria-label="無資料">—</span>
        </template>
        <template #cell-rate="{ row }">
          <span class="gm-rate">
            <span class="gm-num">{{ row.rateText }}</span>
            <GmMeter
              v-if="row.rate !== null"
              width="60px"
              :value="row.rate"
              :max="1"
              :tone="row.state.status === 'ok' ? 'ok' : row.state.status"
              :pattern="row.state.status === 'crit' ? 'cross' : row.state.status === 'warn' ? 'hatch' : 'solid'"
              :label="`降級率 ${row.rateText}`"
            />
          </span>
        </template>
        <template #cell-mean="{ row }"><span class="gm-num">{{ formatMs(row.layer.mean_ms) }}</span></template>
        <template #cell-p95="{ row }"><span class="gm-num">{{ formatMs(row.layer.p95_ms) }}</span></template>
        <template #cell-last="{ row }">
          <time
            v-if="row.layer.last_success_at"
            class="gm-num"
            :datetime="isoFromEpoch(row.layer.last_success_at)"
          >{{ formatAge(row.layer.last_success_at, now) }}</time>
          <span v-else class="gm-muted" aria-label="無資料">—</span>
        </template>
      </GmTable>
    </SlotState>
  </GmPanel>
</template>

<style scoped>
.gm-layer {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.gm-layer__name {
  font-size: var(--text-sm);
  color: var(--paper-100);
}

.gm-layer__model {
  max-width: 40ch;
  overflow: hidden;
  font-size: var(--text-xs);
  color: var(--paper-500);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-mix {
  display: grid;
  gap: var(--sp-1);
  min-width: 160px;
}

.gm-mix__counts {
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
  color: var(--paper-400);
  white-space: nowrap;
}

.gm-mix__reasons {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
}

.gm-mix__more {
  font-size: var(--text-xs);
}

.gm-rate {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
}
</style>
