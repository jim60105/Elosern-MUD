<script setup>
// 世界: the in-game date and daypart from the existing clock (read only —
// the overview never creates the clock), plus live session/combat/instance
// counts.
import GmEmpty from "../../components/GmEmpty.vue";
import GmPanel from "../../components/GmPanel.vue";
import SlotState from "./SlotState.vue";
import { formatCount } from "../../lib/dashboard.js";
import { inject, ref } from "vue";
import GmConsolePrompt from "../../components/GmConsolePrompt.vue";

const api = inject("gmApi", null);
const seconds = ref("");
const request = ref(null);
const emit = defineEmits(["refresh"]);

defineProps({
  world: { type: Object, default: null },
});

const pad = (value) => String(value ?? 0).padStart(2, "0");
</script>

<template>
  <GmPanel title="世界" description="遊戲內時間與即時狀態">
    <form v-if="api" @submit.prevent="request = {path: '/console/advance_clock', body: {seconds: Number(seconds)}, label: 'advance_clock · world'}">
      <label>秒數<input v-model="seconds" type="number" min="0" step="1" required /></label>
      <button type="submit" class="ui-btn ui-btn--danger" :disabled="!world?.clock">推進時鐘</button>
    </form>
    <GmConsolePrompt v-if="api" :request="request" :api="api" @cancel="request = null" @done="request = null; emit('refresh')" />
    <SlotState :value="world" :rows="3">
      <div class="gm-world" data-testid="gm-world">
        <div v-if="world.clock" class="gm-world__clock">
          <p class="gm-world__date">
            第 {{ world.clock.year }} 年 {{ world.clock.season }} 第 {{ world.clock.day }} 日
            <span class="gm-world__daypart">{{ world.clock.daypart ?? "—" }}</span>
          </p>
          <p class="gm-world__tick gm-mono">
            {{ pad(world.clock.hour) }}:{{ pad(world.clock.minute) }} · tick {{ formatCount(world.clock.tick) }}
          </p>
        </div>
        <GmEmpty v-else title="世界時鐘尚未建立" message="總覽只讀取，不會建立時鐘。" />
        <ul class="gm-stats gm-world__stats">
          <li class="gm-stat"><span class="gm-stat__value">{{ formatCount(world.sessions) }}</span><span class="gm-stat__label">連線中</span></li>
          <li class="gm-stat"><span class="gm-stat__value">{{ formatCount(world.accounts) }}</span><span class="gm-stat__label">帳號</span></li>
          <li class="gm-stat"><span class="gm-stat__value">{{ formatCount(world.active_combats) }}</span><span class="gm-stat__label">進行中戰鬥</span></li>
          <li class="gm-stat"><span class="gm-stat__value">{{ formatCount(world.live_instances) }}</span><span class="gm-stat__label">副本實例</span></li>
        </ul>
      </div>
    </SlotState>
  </GmPanel>
</template>

<style scoped>
.gm-world {
  display: grid;
  gap: var(--sp-4);
}

.gm-world__clock {
  display: grid;
  gap: var(--sp-1);
  padding-bottom: var(--sp-3);
  border-bottom: 1px solid var(--ink-700);
}

.gm-world__date {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-2) var(--sp-3);
  font-family: var(--f-serif);
  font-size: var(--text-xl);
  line-height: 1.3;
  color: var(--paper-50);
}

.gm-world__daypart {
  padding: 0 var(--sp-2);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--gold-400);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-pill);
}

.gm-world__tick {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

.gm-world__stats {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 0;
  list-style: none;
}
</style>
