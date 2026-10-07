<script setup>
// 最近警告與錯誤: the newest buffered warn/error events with their caller,
// context and one-line exception summary, filterable by level. Values are
// rendered verbatim (text interpolation only).
import { computed, ref } from "vue";
import GmCodeBlock from "../../components/GmCodeBlock.vue";
import GmEmpty from "../../components/GmEmpty.vue";
import GmPanel from "../../components/GmPanel.vue";
import GmStatusBadge from "../../components/GmStatusBadge.vue";
import SlotState from "./SlotState.vue";
import { formatCount, issueBadge } from "../../lib/dashboard.js";
import { formatClock, isoFromEpoch } from "../../lib/format.js";

const props = defineProps({
  issues: { type: [Array, Object], default: null },
  window: { type: Object, default: null },
});

const COLLAPSED_COUNT = 10;
const filter = ref("all");
const expanded = ref(false);

const list = computed(() => (Array.isArray(props.issues) ? props.issues : []));
const counts = computed(() => ({
  all: list.value.length,
  error: list.value.filter((item) => item.level === "error").length,
  warn: list.value.filter((item) => item.level === "warn").length,
}));
const filters = computed(() => [
  { key: "all", label: "全部" },
  { key: "error", label: "錯誤" },
  { key: "warn", label: "警告" },
]);
const filtered = computed(() =>
  filter.value === "all" ? list.value : list.value.filter((item) => item.level === filter.value),
);
const visible = computed(() => (expanded.value ? filtered.value : filtered.value.slice(0, COLLAPSED_COUNT)));

function contextPairs(context) {
  return Object.entries(context ?? {}).map(([key, value]) => ({
    key,
    text: `${key}=${typeof value === "string" ? value : JSON.stringify(value)}`,
  }));
}
</script>

<template>
  <GmPanel
    title="最近警告與錯誤"
    :description="window ? `緩衝區保留 ${formatCount(window.retained)} / ${formatCount(window.capacity)} 筆` : ''"
  >
    <template v-if="Array.isArray(issues) && issues.length" #actions>
      <div class="ui-tabs" role="group" aria-label="依級別篩選">
        <button
          v-for="item in filters"
          :key="item.key"
          type="button"
          class="ui-tabs__tab"
          :class="{ 'is-active': filter === item.key }"
          :aria-pressed="filter === item.key ? 'true' : 'false'"
          @click="filter = item.key"
        >
          {{ item.label }} <span class="gm-num">{{ counts[item.key] }}</span>
        </button>
      </div>
    </template>
    <SlotState :value="issues" :rows="4">
      <ol v-if="visible.length" class="gm-issues" data-testid="gm-issues">
        <li v-for="(issue, index) in visible" :key="`${issue.ts}:${issue.event}:${index}`" class="gm-issue" :data-level="issue.level">
          <div class="gm-issue__head">
            <time class="gm-mono gm-issue__time" :datetime="isoFromEpoch(issue.ts)">{{ formatClock(issue.ts) }}</time>
            <GmStatusBadge :status="issueBadge(issue.level).status" :label="issueBadge(issue.level).label" />
            <span class="gm-mono gm-issue__event">{{ issue.event }}</span>
            <span class="gm-mono gm-issue__caller" :title="issue.caller">{{ issue.caller }}</span>
          </div>
          <div v-if="Object.keys(issue.context ?? {}).length" class="gm-issue__context">
            <span v-for="pair in contextPairs(issue.context)" :key="pair.key" class="gm-chip" :title="pair.text">{{ pair.text }}</span>
          </div>
          <GmCodeBlock v-if="issue.exc" class="gm-issue__exc" :text="issue.exc" :max-lines="2" copy-label="複製" />
        </li>
      </ol>
      <GmEmpty
        v-else
        :title="filter === 'all' ? '目前沒有警告或錯誤' : '此級別沒有紀錄'"
        message="本次啟動後的 warn／error 事件會出現在這裡。"
      />
      <div v-if="filtered.length > COLLAPSED_COUNT" class="gm-issues__more">
        <button
          type="button"
          class="ui-btn ui-btn--ghost ui-btn--sm"
          :aria-expanded="expanded ? 'true' : 'false'"
          @click="expanded = !expanded"
        >
          {{ expanded ? "收合" : `顯示全部（${filtered.length} 筆）` }}
        </button>
      </div>
    </SlotState>
  </GmPanel>
</template>

<style scoped>
.gm-issues {
  display: grid;
  padding: 0;
  list-style: none;
}

.gm-issue {
  display: grid;
  gap: var(--sp-2);
  padding-block: var(--sp-3);
  border-bottom: 1px dashed var(--ink-700);
}

.gm-issue:first-child {
  padding-top: 0;
}

.gm-issue:last-child {
  border-bottom: 0;
}

.gm-issue__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2) var(--sp-3);
  min-width: 0;
}

.gm-issue__time {
  font-size: var(--text-sm);
  color: var(--paper-400);
}

.gm-issue__event {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--paper-100);
}

.gm-issue__caller {
  min-width: 0;
  overflow: hidden;
  font-size: var(--text-xs);
  color: var(--paper-500);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.gm-issue__context {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
}

.gm-issue__context .gm-chip {
  max-width: 48ch;
}

.gm-issues__more {
  display: flex;
  justify-content: center;
  padding-top: var(--sp-3);
}
</style>
