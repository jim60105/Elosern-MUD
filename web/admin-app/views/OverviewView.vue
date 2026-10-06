<script setup>
// 總覽 (gm-portal-s1-foundation): the temporary S1 home. It renders the real
// /gm/api/session and /gm/api/health responses through the single fetch
// boundary; S2 replaces it with the operations dashboard.
import { computed, inject, onMounted, reactive } from "vue";
import GmPanel from "../components/GmPanel.vue";
import GmTable from "../components/GmTable.vue";
import GmError from "../components/GmError.vue";
import GmStatusBadge from "../components/GmStatusBadge.vue";
import { formatServerTime } from "../lib/format.js";

const api = inject("gmApi");
const session = inject("gmSession");

const health = reactive({ status: "idle", data: null, error: null });

async function loadHealth() {
  health.status = "loading";
  health.error = null;
  try {
    health.data = await api.get("/health");
    health.status = "ready";
  } catch (error) {
    health.error = error;
    health.status = "error";
  }
}

function retrySession() {
  session.load({ force: true });
}

onMounted(() => {
  session.load();
  loadHealth();
});

const sessionState = session.state;

const HEALTH_CHECKS = [
  { key: "django", label: "Django 回應", expected: "ok", okLabel: "正常" },
  { key: "database", label: "資料庫讀取", expected: "readable", okLabel: "可讀取" },
];

const healthColumns = [
  { key: "label", label: "項目" },
  { key: "key", label: "識別碼", mono: true },
  { key: "value", label: "回報值", mono: true },
  { key: "status", label: "狀態" },
];

const healthRows = computed(() =>
  HEALTH_CHECKS.map((check) => {
    const value = health.data?.[check.key];
    const healthy = value === check.expected;
    return {
      key: check.key,
      label: check.label,
      value: value ?? "—",
      badge: healthy ? { status: "ok", label: check.okLabel } : { status: "crit", label: "異常" },
    };
  }),
);
</script>

<template>
  <div class="gm-overview">
    <GmPanel
      class="gm-overview__session"
      title="操作者工作階段"
      description="目前登入的帳號、權限與伺服器資訊"
      :busy="sessionState.status === 'loading'"
    >
      <GmError
        v-if="sessionState.status === 'error'"
        title="無法載入工作階段"
        :message="sessionState.error?.message"
        :code="sessionState.error?.code"
      >
        <template #actions>
          <button type="button" class="ui-btn ui-btn--sm" @click="retrySession">重試</button>
        </template>
      </GmError>
      <template v-else-if="sessionState.data">
        <dl class="gm-ledger" data-testid="gm-session">
          <div class="gm-ledger__row">
            <dt>帳號</dt>
            <dd class="gm-mono" data-field="account_name">{{ sessionState.data.account_name }}</dd>
          </div>
          <div class="gm-ledger__row">
            <dt>權限等級</dt>
            <dd><span class="gm-level" data-field="permission_level">{{ sessionState.data.permission_level }}</span></dd>
          </div>
          <div class="gm-ledger__row">
            <dt>伺服器時間</dt>
            <dd>
              <time :datetime="sessionState.data.server_time">{{ formatServerTime(sessionState.data.server_time) }}</time>
              <span class="gm-ledger__raw gm-mono" data-field="server_time">{{ sessionState.data.server_time }}</span>
            </dd>
          </div>
          <div class="gm-ledger__row">
            <dt>遊戲版本</dt>
            <dd class="gm-mono" data-field="game_version">{{ sessionState.data.game_version }}</dd>
          </div>
        </dl>
      </template>
      <div v-else class="gm-ledger" aria-hidden="true">
        <div v-for="width in ['42%', '28%', '64%', '22%']" :key="width" class="gm-ledger__row">
          <span class="gm-skeleton" style="width: 4.5em"></span>
          <span class="gm-skeleton" :style="{ width }"></span>
        </div>
      </div>
      <p v-if="sessionState.status === 'loading'" class="gm-visually-hidden" role="status">載入中…</p>
    </GmPanel>

    <GmPanel
      class="gm-overview__health"
      title="系統健康"
      description="Django 與資料庫的骨架檢查（不探測外部服務）"
      :flush="health.status !== 'error'"
      :busy="health.status === 'loading'"
    >
      <template #actions>
        <button
          type="button"
          class="ui-btn ui-btn--ghost ui-btn--sm"
          :aria-disabled="health.status === 'loading' ? 'true' : null"
          @click="health.status !== 'loading' && loadHealth()"
        >
          {{ health.status === "loading" ? "檢查中…" : "重新檢查" }}
        </button>
      </template>
      <GmError
        v-if="health.status === 'error'"
        title="無法取得健康狀態"
        :message="health.error?.message"
        :code="health.error?.code"
      >
        <template #actions>
          <button type="button" class="ui-btn ui-btn--sm" @click="loadHealth">重試</button>
        </template>
      </GmError>
      <GmTable
        v-else-if="health.status === 'ready'"
        :columns="healthColumns"
        :rows="healthRows"
        row-key="key"
        caption="各項檢查的即時結果"
        caption-hidden
        flush
        data-testid="gm-health"
      >
        <template #cell-status="{ row }">
          <GmStatusBadge :status="row.badge.status" :label="row.badge.label" />
        </template>
      </GmTable>
      <div v-else class="gm-health-skeleton" aria-hidden="true">
        <div v-for="row in 2" :key="row" class="gm-health-skeleton__row">
          <span class="gm-skeleton" style="width: 30%"></span>
          <span class="gm-skeleton" style="width: 18%"></span>
          <span class="gm-skeleton" style="width: 14%"></span>
        </div>
      </div>
      <p v-if="health.status === 'loading'" class="gm-visually-hidden" role="status">檢查中…</p>
    </GmPanel>
  </div>
</template>

<style scoped>
.gm-overview {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: var(--sp-6);
  align-items: start;
}

.gm-overview__session,
.gm-overview__health {
  grid-column: span 6;
}

@media (max-width: 1099px) {
  .gm-overview__session,
  .gm-overview__health {
    grid-column: span 12;
  }
}

.gm-ledger {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  column-gap: var(--sp-6);
}

/* Each row spans both columns on the shared grid (subgrid), so the dashed
   ledger rule runs unbroken under the term and its value. */
.gm-ledger__row {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  align-items: baseline;
  padding-block: var(--sp-3);
  border-bottom: 1px dashed var(--ink-700);
}

.gm-ledger__row:first-child {
  padding-top: 0;
}

.gm-ledger__row:last-child {
  border-bottom: 0;
  padding-bottom: 0;
}

.gm-ledger dt {
  font-size: var(--text-sm);
  color: var(--paper-500);
}

.gm-ledger dd {
  min-width: 0;
  font-size: var(--text-md);
  color: var(--paper-100);
  overflow-wrap: anywhere;
}

.gm-ledger dd.gm-mono {
  font-size: var(--text-sm);
}

.gm-ledger time {
  display: block;
}

.gm-ledger__raw {
  display: block;
  overflow-wrap: normal;
  white-space: nowrap;
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-level {
  padding: 1px var(--sp-2);
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--gold-400);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
}

.gm-health-skeleton__row {
  display: flex;
  gap: var(--sp-6);
  align-items: center;
  height: 48px;
  padding: 0 var(--sp-5);
  border-bottom: 1px solid var(--ink-700);
}

.gm-health-skeleton__row:last-child {
  border-bottom: 0;
}
</style>
