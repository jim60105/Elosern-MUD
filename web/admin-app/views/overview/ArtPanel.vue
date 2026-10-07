<script setup>
// 美術佇列: record counts per status, the drain script, and the newest
// failures. A queue with work but no running drain is called out in text.
import { computed } from "vue";
import GmMeter from "../../components/GmMeter.vue";
import GmPanel from "../../components/GmPanel.vue";
import GmStatusBadge from "../../components/GmStatusBadge.vue";
import SlotState from "./SlotState.vue";
import { ART_SEGMENTS, drainBadge, formatCount } from "../../lib/dashboard.js";
import { formatAge, isoFromEpoch } from "../../lib/format.js";

const props = defineProps({
  art: { type: Object, default: null },
  now: { type: Number, required: true },
});

const segments = computed(() =>
  ART_SEGMENTS.map((segment) => ({ ...segment, value: props.art?.counts?.[segment.key] ?? 0 })),
);
const meterLabel = computed(() => segments.value.map((s) => `${s.label} ${s.value}`).join("，"));
const drain = computed(() => drainBadge(props.art?.drain));
const stalled = computed(() => {
  const counts = props.art?.counts ?? {};
  return !props.art?.drain?.running && (counts.pending ?? 0) + (counts.in_progress ?? 0) > 0;
});
</script>

<template>
  <GmPanel title="美術佇列" description="生成紀錄的狀態分布與排程">
    <SlotState :value="art" :rows="4">
      <div class="gm-art" data-testid="gm-art">
        <div class="gm-art__drain">
          <GmStatusBadge :status="drain.status" :label="drain.label" />
          <p v-if="stalled" class="gm-art__stalled"><span aria-hidden="true">▲</span> 佇列有待處理項目，但排程未執行</p>
        </div>
        <GmMeter width="100%" :segments="segments" :label="meterLabel" />
        <ul class="gm-stats gm-art__stats">
          <li v-for="segment in segments" :key="segment.key" class="gm-stat" :data-status="segment.key">
            <span class="gm-stat__value">{{ formatCount(segment.value) }}</span>
            <span class="gm-stat__label">
              <span class="gm-art__swatch" :class="`gm-art__swatch--${segment.key}`" aria-hidden="true"></span>{{ segment.label }}
            </span>
          </li>
        </ul>
        <div class="gm-art__failures">
          <h3 class="gm-art__h3">最近失敗</h3>
          <ol v-if="art.failures?.length" class="gm-art__list">
            <li v-for="failure in art.failures" :key="`${failure.subject_key}:${failure.ts}`" class="gm-art__item">
              <span class="gm-art__subject gm-mono" :title="failure.subject_key">{{ failure.subject_key }}</span>
              <span class="gm-chip">{{ failure.kind ?? "—" }}</span>
              <time v-if="failure.ts" class="gm-muted gm-art__time" :datetime="isoFromEpoch(failure.ts)">
                {{ formatAge(failure.ts, now) }}
              </time>
              <code v-if="failure.error" class="gm-art__error" :title="failure.error">{{ failure.error }}</code>
            </li>
          </ol>
          <p v-else class="gm-muted gm-art__none">沒有失敗紀錄</p>
        </div>
      </div>
    </SlotState>
  </GmPanel>
</template>

<style scoped>
.gm-art {
  display: grid;
  gap: var(--sp-4);
}

.gm-art__drain {
  display: grid;
  justify-items: start;
  gap: var(--sp-2);
}

.gm-art__stalled {
  font-size: var(--text-sm);
  color: var(--paper-200);
}

.gm-art__stalled span {
  color: var(--warn);
}

.gm-art__stats {
  grid-template-columns: repeat(5, minmax(0, 1fr));
  padding: 0;
  list-style: none;
}

.gm-art__stats .gm-stat {
  padding-inline: var(--sp-2);
}

.gm-art__stats .gm-stat__value {
  font-size: var(--text-lg);
}

.gm-art__swatch {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 4px;
  vertical-align: middle;
  border-radius: 1px;
}

.gm-art__swatch--failed {
  background: repeating-linear-gradient(135deg, var(--crit) 0 2px, var(--ink-950) 2px 3px);
}
.gm-art__swatch--in_progress {
  background: repeating-linear-gradient(135deg, var(--gold-500) 0 2px, var(--ink-950) 2px 3px);
}
.gm-art__swatch--pending {
  background: var(--paper-500);
}
.gm-art__swatch--missing {
  box-shadow: inset 0 0 0 1px var(--paper-500);
}
.gm-art__swatch--done {
  background: var(--ok);
}

.gm-art__h3 {
  margin-bottom: var(--sp-2);
  font-size: var(--text-xs);
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--paper-400);
}

.gm-art__list {
  display: grid;
  padding: 0;
  list-style: none;
}

.gm-art__item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 2px var(--sp-2);
  align-items: center;
  padding-block: var(--sp-2);
  border-bottom: 1px dashed var(--ink-700);
}

.gm-art__item:last-child {
  border-bottom: 0;
}

.gm-art__subject {
  overflow: hidden;
  font-size: var(--text-sm);
  color: var(--paper-100);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-art__time {
  font-size: var(--text-xs);
  white-space: nowrap;
}

.gm-art__error {
  grid-column: 1 / -1;
  overflow: hidden;
  font-size: var(--text-xs);
  color: var(--paper-400);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-art__none {
  font-size: var(--text-sm);
}
</style>
