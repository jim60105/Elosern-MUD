<script setup>
// 總覽 (gm-portal-s2b-dashboard): the operations dashboard. One
// /gm/api/dashboard snapshot every five seconds while the tab is visible,
// through the single fetch boundary; each slot renders (or fails) on its
// own. A failed poll keeps the last good snapshot and marks it stale.
// Selecting a recent call opens the payload drawer, which fetches the
// retained transcript on demand.
import { computed, inject, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import GmCallDrawer from "../components/GmCallDrawer.vue";
import GmRefreshBar from "../components/GmRefreshBar.vue";
import { createPoller, POLL_INTERVAL_MS } from "../lib/poller.js";
import ArtPanel from "./overview/ArtPanel.vue";
import IssuesPanel from "./overview/IssuesPanel.vue";
import LlmLayersPanel from "./overview/LlmLayersPanel.vue";
import ProcessPanel from "./overview/ProcessPanel.vue";
import RecentCallsPanel from "./overview/RecentCallsPanel.vue";
import ServicesPanel from "./overview/ServicesPanel.vue";
import SessionPanel from "./overview/SessionPanel.vue";
import WorldPanel from "./overview/WorldPanel.vue";

const api = inject("gmApi");
const session = inject("gmSession");

const dashboard = reactive({ data: null, lastUpdatedAt: null, error: null });
const selectedCall = ref(null);
const hidden = ref(globalThis.document?.visibilityState === "hidden");
const now = ref(Date.now() / 1000);
let clock = null;

const poller = createPoller({
  load: () => api.get("/dashboard"),
  onData(data) {
    dashboard.data = data;
    dashboard.lastUpdatedAt = Date.now() / 1000;
    dashboard.error = null;
  },
  onError(error) {
    dashboard.error = error;
  },
});

const refreshing = ref(false);
async function refresh() {
  refreshing.value = true;
  try {
    await poller.refresh();
  } finally {
    refreshing.value = false;
  }
}

// The relative-age clock ticks only while the tab is visible.
function startClock() {
  if (clock === null) clock = setInterval(() => (now.value = Date.now() / 1000), 1000);
}

function stopClock() {
  clearInterval(clock);
  clock = null;
}

function onVisibility() {
  hidden.value = document.visibilityState === "hidden";
  if (hidden.value) {
    stopClock();
  } else {
    now.value = Date.now() / 1000;
    startClock();
  }
}

onMounted(() => {
  session.load();
  document.addEventListener("visibilitychange", onVisibility);
  if (!hidden.value) startClock();
  poller.start();
});

onBeforeUnmount(() => {
  poller.stop();
  stopClock();
  document.removeEventListener("visibilitychange", onVisibility);
});

const barState = computed(() => {
  if (dashboard.error) return "stale";
  if (hidden.value) return "paused";
  if (!dashboard.data) return "loading";
  if (refreshing.value) return "refreshing";
  return "live";
});

const data = computed(() => dashboard.data);
</script>

<template>
  <div class="gm-dashboard">
    <GmRefreshBar
      class="gm-dashboard__bar"
      :state="barState"
      :last-updated-at="dashboard.lastUpdatedAt"
      :interval-seconds="POLL_INTERVAL_MS / 1000"
      :error-message="dashboard.error?.message ?? ''"
      :now="now"
      :paused="hidden"
      :busy="refreshing"
      data-testid="gm-refresh-bar"
      @refresh="refresh"
    />

    <ServicesPanel class="gm-dashboard__services" :services="data?.services ?? null" :now="now" />

    <LlmLayersPanel
      class="gm-dashboard__layers"
      :layers="data?.llm?.layers ?? null"
      :window="data?.llm?.window ?? null"
      :now="now"
    />

    <div class="gm-dashboard__main">
      <RecentCallsPanel
        id="gm-recent-calls"
        :calls="data?.llm?.recent ?? null"
        :selected-id="selectedCall"
        @select="selectedCall = $event"
      />
      <IssuesPanel
        :issues="data?.errors?.recent ?? null"
        :window="data?.errors?.window ?? null"
      />
    </div>

    <div class="gm-dashboard__aside">
      <ArtPanel :art="data?.art ?? null" :now="now" />
      <WorldPanel :world="data?.world ?? null" />
      <ProcessPanel :process="data?.process ?? null" />
      <SessionPanel />
    </div>

    <GmCallDrawer
      :call-id="selectedCall"
      :api="api"
      fallback-focus="#gm-recent-calls h2"
      @close="selectedCall = null"
    />
  </div>
</template>

<style scoped>
.gm-dashboard {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: var(--sp-6);
  align-items: start;
  container: gm-dashboard / inline-size;
}

.gm-dashboard > * {
  grid-column: 1 / -1;
  min-width: 0;
}

.gm-dashboard__bar {
  position: sticky;
  top: var(--sp-3);
  z-index: 2;
}

.gm-dashboard__main {
  display: grid;
  grid-column: span 8;
  gap: var(--sp-6);
  min-width: 0;
}

.gm-dashboard__aside {
  display: grid;
  grid-column: span 4;
  gap: var(--sp-6);
  min-width: 0;
}

@container gm-dashboard (max-width: 1099px) {
  .gm-dashboard__main,
  .gm-dashboard__aside {
    grid-column: 1 / -1;
  }

  .gm-dashboard__aside {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@container gm-dashboard (max-width: 759px) {
  .gm-dashboard__aside {
    grid-template-columns: minmax(0, 1fr);
  }

  .gm-dashboard__bar {
    position: static;
  }
}
</style>
