<script setup>
// 操作者工作階段 (compact): identity, permission and game version from
// /gm/api/session; freshness now lives in the refresh bar.
import { inject } from "vue";
import GmError from "../../components/GmError.vue";
import GmPanel from "../../components/GmPanel.vue";

const session = inject("gmSession");
const state = session.state;
</script>

<template>
  <GmPanel title="操作者工作階段" :busy="state.status === 'loading'">
    <GmError
      v-if="state.status === 'error'"
      compact
      title="無法載入工作階段"
      :message="state.error?.message"
      :code="state.error?.code"
    >
      <template #actions>
        <button type="button" class="ui-btn ui-btn--sm" @click="session.load({ force: true })">重試</button>
      </template>
    </GmError>
    <dl v-else-if="state.data" class="gm-ledger" data-testid="gm-session">
      <div class="gm-ledger__row">
        <dt>帳號</dt>
        <dd class="gm-mono" data-field="account_name">{{ state.data.account_name }}</dd>
      </div>
      <div class="gm-ledger__row">
        <dt>權限等級</dt>
        <dd><span class="gm-level" data-field="permission_level">{{ state.data.permission_level }}</span></dd>
      </div>
      <div class="gm-ledger__row">
        <dt>遊戲版本</dt>
        <dd class="gm-mono" data-field="game_version">{{ state.data.game_version }}</dd>
      </div>
    </dl>
    <div v-else class="gm-session-skeleton" aria-hidden="true">
      <span v-for="width in ['44%', '28%', '20%']" :key="width" class="gm-skeleton" :style="{ width }"></span>
    </div>
  </GmPanel>
</template>

<style scoped>
.gm-level {
  padding: 1px var(--sp-2);
  font-family: var(--f-mono);
  font-size: var(--text-xs);
  color: var(--gold-400);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
}

.gm-session-skeleton {
  display: grid;
  gap: var(--sp-3);
}
</style>
