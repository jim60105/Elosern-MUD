<script setup>
// 行程與緩衝: the folded S1 health (Django responding, a real database
// read), server start and uptime, and the recent-event buffer fill.
import { computed } from "vue";
import GmMeter from "../../components/GmMeter.vue";
import GmPanel from "../../components/GmPanel.vue";
import GmStatusBadge from "../../components/GmStatusBadge.vue";
import SlotState from "./SlotState.vue";
import { formatCount } from "../../lib/dashboard.js";
import { formatClock, formatDuration, formatServerTime, isoFromEpoch } from "../../lib/format.js";

const props = defineProps({
  process: { type: Object, default: null },
});

const buffers = computed(() => {
  const data = props.process?.buffers;
  if (!data) return [];
  return [
    { key: "llm", label: "LLM 緩衝", ...data.llm },
    { key: "issues", label: "警告緩衝", ...data.issues },
  ].map((buffer) => ({ ...buffer, full: buffer.capacity > 0 && buffer.fill >= buffer.capacity }));
});

function fullTime(epoch) {
  const iso = isoFromEpoch(epoch);
  return iso ? formatServerTime(iso) : "";
}
</script>

<template>
  <GmPanel title="行程與緩衝" description="伺服器行程、資料庫與近期事件緩衝">
    <SlotState :value="process" :rows="5">
      <dl class="gm-ledger" data-testid="gm-process">
        <div class="gm-ledger__row">
          <dt>Django</dt>
          <dd><GmStatusBadge :status="process.django === 'ok' ? 'ok' : 'crit'" :label="process.django === 'ok' ? '正常' : '異常'" /></dd>
        </div>
        <div class="gm-ledger__row">
          <dt>資料庫</dt>
          <dd><GmStatusBadge :status="process.database === 'readable' ? 'ok' : 'crit'" :label="process.database === 'readable' ? '可讀取' : '異常'" /></dd>
        </div>
        <div class="gm-ledger__row">
          <dt>啟動於</dt>
          <dd>
            <time v-if="process.started_at" class="gm-mono" :datetime="isoFromEpoch(process.started_at)" :title="fullTime(process.started_at)">
              {{ formatClock(process.started_at) }}
            </time>
            <span v-else class="gm-muted" aria-label="無資料">—</span>
          </dd>
        </div>
        <div class="gm-ledger__row">
          <dt>運行時間</dt>
          <dd class="gm-mono">{{ formatDuration(process.uptime_s) }}</dd>
        </div>
        <div v-for="buffer in buffers" :key="buffer.key" class="gm-ledger__row">
          <dt>{{ buffer.label }}</dt>
          <dd class="gm-buffer">
            <span class="gm-buffer__line">
              <GmMeter
                width="96px"
                :value="buffer.fill"
                :max="buffer.capacity"
                :tone="buffer.full ? 'warn' : 'gold'"
                :pattern="buffer.full ? 'hatch' : 'solid'"
                :label="`${buffer.label} ${buffer.fill} / ${buffer.capacity}`"
              />
              <span class="gm-num">{{ formatCount(buffer.fill) }} / {{ formatCount(buffer.capacity) }}</span>
            </span>
            <span v-if="buffer.full" class="gm-buffer__full">▲ 已滿，最舊紀錄會被淘汰</span>
          </dd>
        </div>
      </dl>
      <p class="gm-process__epoch">
        緩衝自 <time :datetime="isoFromEpoch(process.buffers_started_at)">{{ formatClock(process.buffers_started_at) }}</time> 起累積；重新載入伺服器後清空
      </p>
    </SlotState>
  </GmPanel>
</template>

<style scoped>
.gm-buffer {
  display: grid;
  gap: 2px;
}

.gm-buffer__line {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
}

.gm-buffer__line .gm-num {
  font-size: var(--text-sm);
  color: var(--paper-200);
}

.gm-buffer__full {
  font-size: var(--text-xs);
  color: var(--paper-300);
}

.gm-process__epoch {
  margin-top: var(--sp-3);
  font-size: var(--text-xs);
  color: var(--paper-500);
}
</style>
