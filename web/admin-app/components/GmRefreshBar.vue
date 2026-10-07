<script setup>
// The freshness strip of a polled page (gm-portal-s2b-dashboard): live,
// refreshing, paused (tab hidden), or stale (the last poll failed and the
// shown data is older). It is the single polite live region of the page and
// announces only state transitions, never the ticking age.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import GmStatusBadge from "./GmStatusBadge.vue";
import { formatAge, formatClock, isoFromEpoch } from "../lib/format.js";

const props = defineProps({
  state: {
    type: String,
    default: "loading",
    validator: (value) => ["loading", "live", "refreshing", "paused", "stale"].includes(value),
  },
  lastUpdatedAt: { type: Number, default: null },
  intervalSeconds: { type: Number, default: 5 },
  errorMessage: { type: String, default: "" },
  now: { type: Number, default: null },
  // The tab is hidden: a stale bar then says it retries on return.
  paused: { type: Boolean, default: false },
  // A manual refresh is in flight, whatever the freshness state.
  busy: { type: Boolean, default: false },
});

const emit = defineEmits(["refresh"]);

const tick = ref(Date.now() / 1000);
let timer = null;
onMounted(() => {
  if (props.now === null) timer = setInterval(() => (tick.value = Date.now() / 1000), 1000);
});
onBeforeUnmount(() => timer && clearInterval(timer));
const current = computed(() => props.now ?? tick.value);

const BADGES = {
  loading: { status: "neutral", label: "載入中" },
  live: { status: "ok", label: "即時" },
  refreshing: { status: "ok", label: "即時" },
  paused: { status: "neutral", label: "已暫停" },
  stale: { status: "warn", label: "資料過期" },
};

const badge = computed(() => BADGES[props.state]);
const busy = computed(() => props.busy || props.state === "loading" || props.state === "refreshing");
const hint = computed(() => {
  if (props.state === "paused") return "分頁在背景，已暫停自動更新";
  if (props.state === "stale") {
    const reason = props.errorMessage ? `更新失敗：${props.errorMessage}` : "更新失敗";
    const retry = props.paused ? "分頁回到前景時重試" : `${props.intervalSeconds} 秒後重試`;
    if (props.lastUpdatedAt === null) return `${reason}。尚未取得任何資料，${retry}。`;
    return `${reason}。目前顯示 ${formatClock(props.lastUpdatedAt)} 的資料，${retry}。`;
  }
  if (props.state === "loading") return "";
  return `每 ${props.intervalSeconds} 秒自動更新`;
});

// Announce transitions only (stale / recovered / paused), not every poll.
const announcement = ref("");
watch(
  () => props.state,
  (next, previous) => {
    if (next === "stale" && previous !== "stale") announcement.value = "資料已過期";
    else if (next === "live" && previous === "stale") announcement.value = "已恢復即時更新";
    else if (next === "paused") announcement.value = "已暫停自動更新";
    else if (next === "live" && previous === "paused") announcement.value = "已恢復自動更新";
  },
);
</script>

<template>
  <div class="gm-refresh-bar" :class="`gm-refresh-bar--${state}`" :data-state="state">
    <GmStatusBadge :status="badge.status" :label="badge.label" />
    <p class="gm-refresh-bar__time">
      <template v-if="lastUpdatedAt !== null">
        <span class="gm-refresh-bar__label">最後更新</span>
        <time class="gm-mono" :datetime="isoFromEpoch(lastUpdatedAt)">{{ formatClock(lastUpdatedAt) }}</time>
        <span class="gm-refresh-bar__age">（{{ formatAge(lastUpdatedAt, current) }}）</span>
      </template>
      <span v-else class="gm-refresh-bar__label">尚未取得資料</span>
    </p>
    <p v-if="hint" class="gm-refresh-bar__hint">{{ hint }}</p>
    <button
      type="button"
      class="ui-btn ui-btn--ghost ui-btn--sm gm-refresh-bar__button"
      :aria-disabled="busy ? 'true' : null"
      @click="!busy && emit('refresh')"
    >
      <span class="gm-refresh-bar__icon" :class="{ 'is-spinning': busy }" aria-hidden="true">↻</span>
      {{ busy ? "更新中…" : "立即更新" }}
    </button>
    <p class="gm-visually-hidden" role="status" aria-live="polite">{{ announcement }}</p>
  </div>
</template>

<style scoped>
.gm-refresh-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2) var(--sp-4);
  padding: var(--sp-2) var(--sp-2) var(--sp-2) var(--sp-4);
  background: color-mix(in srgb, var(--ink-950) 88%, transparent);
  border: 1px solid var(--ink-700);
  border-bottom-color: var(--band-edge-dim);
  border-radius: var(--radius);
  backdrop-filter: blur(6px);
}

.gm-refresh-bar--stale {
  border-left: 3px dashed var(--warn);
}

.gm-refresh-bar__time {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  font-size: var(--text-sm);
  color: var(--paper-200);
}

.gm-refresh-bar__label,
.gm-refresh-bar__age {
  color: var(--paper-500);
}

.gm-refresh-bar__label {
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
}

.gm-refresh-bar__hint {
  flex: 1 1 18em;
  min-width: 0;
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-refresh-bar--stale .gm-refresh-bar__hint {
  color: var(--paper-300);
}

.gm-refresh-bar__button {
  margin-left: auto;
  gap: var(--sp-2);
}

.gm-refresh-bar__icon {
  display: inline-block;
  font-family: var(--f-sans);
}

.gm-refresh-bar__icon.is-spinning {
  animation: gm-refresh-spin var(--motion-spin) linear infinite;
}

@keyframes gm-refresh-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .gm-refresh-bar__icon.is-spinning {
    animation: none;
  }
}
</style>
