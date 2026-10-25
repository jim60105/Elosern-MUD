<script setup>
// NPC service-menu prototype (reference only, mock data; not imported by the
// app). The exploration stage with the real HudFrame, PresenceRail,
// StageActor, ChoiceCard, and HudDrawer: activating a person on the rail
// opens that person's single interaction card in the stage's `choices`
// anchor (the production person-focus location). The card groups the common
// interactions (1 交談, 2 查看人物 for every NPC), the conditional
// interactions, then the services the NPC's synthetic descriptors supply
// (see npc-service-model.js). NPC identity is the plain name everywhere: the
// rail plate, the standee, and the card's accessible name.
//
// Nothing here dispatches a command or touches the network. A service row
// opens a demonstration pane named after the player function inside the
// shared drawer chrome; its close (✕, Escape, the scrim, or its return
// button) restores focus to that service row while the card and the row
// still exist. Closing the card restores focus to the person's rail entry.
// The departure and service-read-failure controls in the top strip are
// prototype-only simulations, labelled as such, outside the stage.
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import ChoiceCard from "../../../web/webclient-app/components/ChoiceCard.vue";
import ExitCompass from "../../../web/webclient-app/components/ExitCompass.vue";
import ExplorationReadout from "../../../web/webclient-app/components/ExplorationReadout.vue";
import HudDrawer from "../../../web/webclient-app/components/HudDrawer.vue";
import HudFrame from "../../../web/webclient-app/components/HudFrame.vue";
import LocalMap from "../../../web/webclient-app/components/LocalMap.vue";
import PlaceCard from "../../../web/webclient-app/components/PlaceCard.vue";
import PresenceRail from "../../../web/webclient-app/components/PresenceRail.vue";
import SceneBackdrop from "../../../web/webclient-app/components/SceneBackdrop.vue";
import StageActor from "../../../web/webclient-app/components/StageActor.vue";
import {
  FLASH_MS,
  departedReadout,
  idleReadout,
  readoutContent,
} from "../../../web/webclient-app/components/exploration-readout.js";
import { compassArgs } from "../../../web/webclient-app/stories/fixtures/scene_overview.js";
import { LOCAL_MAP, NPCS, ROOM, STORY_ART, railEntries } from "./npc-service-fixtures.js";
import { serviceMenuRows } from "./npc-service-model.js";

const props = defineProps({
  // The NPC whose card is open on mount, or null for the rail at rest.
  initialNpc: { type: Number, default: null },
  // NPC identities whose service read fails from the start.
  unreadable: { type: Array, default: () => [] },
  // A service row key (`service:<key>`) of `initialNpc` to open on mount.
  initialService: { type: String, default: null },
  // Milliseconds after mount at which `initialNpc` leaves the room, or null.
  autoDepartMs: { type: Number, default: null },
});

const FLOW_COPY = {
  trade: { icon: "shop", flow: "交易流程", product: "正式版會開啟商店視窗（購買／出售）。" },
  guild: { icon: "quests", flow: "公會櫃檯流程", product: "正式版會開啟對應的公會櫃檯畫面。" },
};

const { localMapModel, ...compassProps } = compassArgs(ROOM, LOCAL_MAP);

const presentIds = ref(NPCS.map((npc) => npc.identity));
const unreadableIds = ref(new Set(props.unreadable));
const card = ref(null); // {identity, openerKey}
const openService = ref(null); // {npcIdentity, key, label, flow}
const railHover = ref(null);
const flash = ref(null);
const log = ref("原型模擬：在舞臺右下的在場人物上按 Enter 或點擊，開啟互動選單。");

const railRef = ref(null);
const cardRef = ref(null);
const compassRef = ref(null);

let flashTimer = null;
let departTimer = null;

const present = computed(() => NPCS.filter((npc) => presentIds.value.includes(npc.identity)));
const entries = computed(() => railEntries(present.value.map(effective)));

// A fixture NPC with the simulated service-read failure applied.
function effective(npc) {
  return unreadableIds.value.has(npc.identity) ? { ...npc, services: { state: "unreadable" } } : npc;
}

const cardNpc = computed(() => {
  if (!card.value) {
    return null;
  }
  const npc = present.value.find((candidate) => candidate.identity === card.value.identity);
  return npc ? effective(npc) : null;
});
const menu = computed(() => (cardNpc.value ? serviceMenuRows(cardNpc.value) : null));
const cardPortrait = computed(() => {
  const portraitRef = cardNpc.value?.portraitRef;
  return portraitRef == null ? null : (STORY_ART.portrait_catalog?.[portraitRef]?.artwork ?? null);
});
const cardUnreadable = computed(() => !!cardNpc.value && unreadableIds.value.has(cardNpc.value.identity));

const readout = computed(() =>
  readoutContent({
    flash: flash.value,
    rail: card.value ? null : railHover.value,
    idle: idleReadout(compassProps.targets.cycle.length, present.value.length),
  }),
);

function showFlash(content) {
  flash.value = content;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => {
    flash.value = null;
  }, FLASH_MS);
}

function focusRail(openerKey) {
  const rail = railRef.value;
  if (rail && (openerKey ? rail.focusEntry(openerKey) : false)) {
    return;
  }
  if (rail && entries.value.length > 0) {
    rail.focus();
    return;
  }
  compassRef.value?.focus();
}

function onRailActivate(key) {
  const entry = entries.value.find((candidate) => candidate.key === key);
  if (!entry) {
    return;
  }
  card.value = { identity: entry.identity, openerKey: key };
  log.value = `原型模擬：開啟「${entry.label}」的互動選單。`;
}

async function closeCard() {
  const openerKey = card.value?.openerKey ?? null;
  card.value = null;
  await nextTick();
  focusRail(openerKey);
  log.value = "原型模擬：選單已關閉，焦點回到在場人物。";
}

function onPick(key) {
  const npc = cardNpc.value;
  const row = menu.value?.meta[key];
  if (!npc || !row) {
    return;
  }
  if (row.type === "service") {
    openService.value = { npcIdentity: npc.identity, key, label: row.label, flow: row.flow };
    log.value = `原型模擬：開啟「${row.label}」示範面板（未送出任何指令）。`;
    return;
  }
  const what = {
    talk: "正式版會進入對話畫面",
    look: "正式版會送出查看並關閉選單",
    conditional: "條件互動維持現有流程，不屬於服務",
  }[row.type];
  log.value = `原型模擬：選了「${row.label}」——${what}；此原型不送出指令。`;
}

// The demonstration pane closed: focus returns to the service row it was
// opened from while the card and that row still exist, else to the card,
// else to the rail.
async function onServiceClose() {
  const opened = openService.value;
  openService.value = null;
  await nextTick();
  if (!cardNpc.value || !cardRef.value) {
    focusRail(null);
    return;
  }
  const index = menu.value.rows.findIndex((row) => row.key === opened?.key);
  if (index >= 0) {
    cardRef.value.setActive(index);
  }
  cardRef.value.focus();
  log.value =
    index >= 0
      ? `原型模擬：示範面板已關閉，焦點回到「${opened.label}」。`
      : "原型模擬：示範面板已關閉；該服務已不在選單上，焦點回到選單。";
}

// The person in focus leaves the room: the card (and any demonstration pane
// opened from it) closes, the departed flash shows, and focus goes to the
// rail (the person's own entry no longer exists).
async function simulateDeparture() {
  const npc = cardNpc.value;
  if (!npc) {
    return;
  }
  presentIds.value = presentIds.value.filter((identity) => identity !== npc.identity);
  openService.value = null;
  card.value = null;
  showFlash(departedReadout(npc.name));
  log.value = `原型模擬：「${npc.name}」離開了房間，選單已安全關閉。`;
  await nextTick();
  focusRail(null);
}

function toggleUnreadable() {
  const npc = cardNpc.value;
  if (!npc) {
    return;
  }
  const next = new Set(unreadableIds.value);
  if (next.has(npc.identity)) {
    next.delete(npc.identity);
    log.value = `原型模擬：「${npc.name}」的服務資訊恢復可讀取。`;
  } else {
    next.add(npc.identity);
    log.value = `原型模擬：「${npc.name}」的服務資訊讀取失敗（不是沒有服務）。`;
  }
  unreadableIds.value = next;
}

async function reset() {
  presentIds.value = NPCS.map((npc) => npc.identity);
  unreadableIds.value = new Set();
  openService.value = null;
  card.value = null;
  flash.value = null;
  log.value = "原型模擬：已重設所有人物與服務狀態。";
  await nextTick();
  focusRail(null);
}

onMounted(async () => {
  const npc = NPCS.find((candidate) => candidate.identity === props.initialNpc);
  if (npc) {
    card.value = { identity: npc.identity, openerKey: `target-${npc.identity}` };
    if (props.initialService) {
      await nextTick();
      const index = menu.value.rows.findIndex((row) => row.key === props.initialService);
      if (index >= 0 && cardRef.value) {
        cardRef.value.setActive(index);
        cardRef.value.focus();
        onPick(props.initialService);
      }
    }
    if (props.autoDepartMs !== null) {
      log.value = `原型模擬：「${npc.name}」將在 ${(props.autoDepartMs / 1000).toFixed(1)} 秒後離開。`;
      departTimer = setTimeout(() => {
        if (cardNpc.value?.identity === npc.identity) {
          void simulateDeparture();
        }
      }, props.autoDepartMs);
    }
  }
});

onBeforeUnmount(() => {
  clearTimeout(flashTimer);
  clearTimeout(departTimer);
});
</script>

<template>
  <div class="npc-proto" data-testid="npc-service-prototype">
    <!-- Prototype-only controls, in the top navigation's strip and outside
         the stage: never in-character prose. -->
    <section class="npc-proto__controls" aria-label="原型模擬控制（非遊戲內容）">
      <span class="npc-proto__tag">原型模擬</span>
      <button
        type="button"
        class="npc-proto__btn"
        data-testid="npc-proto-depart"
        :disabled="!cardNpc"
        @click="simulateDeparture"
      >模擬：{{ cardNpc ? cardNpc.name : "目前人物" }}離開</button>
      <button
        type="button"
        class="npc-proto__btn"
        data-testid="npc-proto-unreadable"
        :disabled="!cardNpc"
        :aria-pressed="cardUnreadable ? 'true' : 'false'"
        @click="toggleUnreadable"
      >模擬：服務資訊讀取失敗</button>
      <button type="button" class="npc-proto__btn" data-testid="npc-proto-reset" @click="reset">重設</button>
      <p class="npc-proto__log" aria-live="polite" :title="log" data-testid="npc-proto-log">{{ log }}</p>
    </section>

    <div class="npc-proto__stage">
      <HudFrame mode="exploration" :card-open="!!cardNpc" :person-focus="!!cardNpc">
        <template #backdrop>
          <SceneBackdrop :art="STORY_ART" mode="exploration" />
        </template>
        <template #actor-right>
          <StageActor
            v-if="cardNpc"
            side="right"
            :artwork="cardPortrait"
            :panel="STORY_ART"
            :has-reference="cardNpc.portraitRef != null"
            :name="cardNpc.name"
          />
        </template>
        <template #presence>
          <PresenceRail
            v-show="!cardNpc"
            ref="railRef"
            :entries="entries"
            :art-panel="STORY_ART"
            @activate="onRailActivate"
            @hover="railHover = $event"
          />
        </template>
        <template #choices>
          <ChoiceCard
            v-if="cardNpc"
            :key="cardNpc.identity"
            ref="cardRef"
            :rows="menu.rows"
            :digit-rows="menu.digitRows"
            :trailing-index="menu.trailingIndex"
            :aria-label="`${cardNpc.name}：選擇行動`"
            test-id="presence-card"
            block="npc-service-card"
            trap-focus
            autofocus
            @pick="onPick"
            @back="closeCard"
          />
        </template>
        <template #map>
          <PlaceCard location-label="冒險者公會大廳" time-label="第 3 天 ‧ 午後" :actions-enabled="true" />
          <LocalMap :local-map="localMapModel" />
        </template>
        <template #band-command>
          <div class="npc-proto__command">
            <div class="npc-proto__compass">
              <ExitCompass ref="compassRef" v-bind="compassProps" :active="!cardNpc" />
            </div>
            <ExplorationReadout class="exploration-root__readout" v-bind="readout" />
          </div>
        </template>
      </HudFrame>
    </div>

    <HudDrawer
      v-if="openService"
      :open="true"
      drawer-key="npc-service-demo"
      :icon="FLOW_COPY[openService.flow].icon"
      :title="openService.label"
      subtitle="原型示範面板"
      @close="onServiceClose"
    >
      <div class="npc-proto__pane" data-testid="npc-service-demo-pane">
        <p class="npc-proto__pane-lead">
          這是原型示範面板，不是正式的{{ FLOW_COPY[openService.flow].flow }}介面；沒有送出任何指令，也沒有改變遊戲狀態。
        </p>
        <dl class="npc-proto__facts">
          <dt>服務</dt>
          <dd>{{ openService.label }}</dd>
          <dt>對象</dt>
          <dd>{{ NPCS.find((npc) => npc.identity === openService.npcIdentity)?.name }}</dd>
          <dt>流程</dt>
          <dd>{{ FLOW_COPY[openService.flow].flow }}——{{ FLOW_COPY[openService.flow].product }}</dd>
        </dl>
        <p class="npc-proto__pane-hint">按 Esc、✕ 或下方按鈕返回，焦點會回到選單上的「{{ openService.label }}」。</p>
        <button type="button" class="npc-proto__btn npc-proto__btn--primary" data-testid="npc-service-demo-return" @click="onServiceClose">
          返回人物選單
        </button>
      </div>
    </HudDrawer>
  </div>
</template>

<style>
/* The prototype's own chrome: tokens and the ui-scale factor only. */
.npc-proto {
  position: relative;
  width: 100%;
  height: calc(100vh - var(--header-h));
}

.npc-proto__stage {
  position: absolute;
  inset: 0;
}

.npc-proto__controls {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: calc(var(--z-surface-modal) + 1);
  box-sizing: border-box;
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  padding: 0 calc(16px * var(--ui-scale));
  background: repeating-linear-gradient(135deg, rgba(185, 154, 96, 0.08) 0 calc(8px * var(--ui-scale)), transparent 0 calc(16px * var(--ui-scale))), var(--ink-950);
  border-bottom: 1px dashed rgba(185, 154, 96, 0.55);
  font: var(--text-sm)/1.3 var(--f-sans);
  color: var(--paper-300);
}

.npc-proto__tag {
  flex: none;
  padding: calc(2px * var(--ui-scale)) calc(8px * var(--ui-scale));
  border: 1px dashed var(--gold-500);
  border-radius: var(--radius-sm);
  color: var(--gold-400);
  letter-spacing: 0.12em;
}

.npc-proto__btn {
  flex: none;
  padding: calc(4px * var(--ui-scale)) calc(10px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.55);
  border-radius: var(--radius-sm);
  background: rgba(185, 154, 96, 0.08);
  color: var(--paper-100);
  font: inherit;
  cursor: pointer;
  transition: background-color var(--motion-fast) var(--ease-standard);
}

.npc-proto__btn:hover:not(:disabled) {
  background: rgba(185, 154, 96, 0.2);
}

.npc-proto__btn:disabled {
  border-style: dashed;
  color: var(--paper-500);
  cursor: default;
}

.npc-proto__btn[aria-pressed="true"] {
  border-color: var(--seal-500);
  background: rgba(169, 50, 42, 0.18);
}

.npc-proto__btn[aria-pressed="true"]::before {
  content: "✓ ";
}

.npc-proto__btn--primary {
  align-self: flex-start;
}

.npc-proto__log {
  flex: 1;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  color: var(--paper-400);
}

.npc-proto__command {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: calc(10px * var(--ui-scale));
  height: 100%;
}

.npc-proto__compass {
  height: 100%;
  aspect-ratio: 1 / 1;
}

.npc-proto__pane {
  display: flex;
  flex-direction: column;
  gap: calc(14px * var(--ui-scale));
  max-width: calc(640px * var(--ui-scale));
  font: var(--text-base)/1.6 var(--f-sans);
  color: var(--paper-200);
}

.npc-proto__pane-lead {
  margin: 0;
  padding: calc(10px * var(--ui-scale)) calc(14px * var(--ui-scale));
  border: 1px dashed rgba(185, 154, 96, 0.55);
  border-radius: var(--radius-sm);
  color: var(--paper-100);
}

.npc-proto__facts {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: calc(6px * var(--ui-scale)) calc(16px * var(--ui-scale));
  margin: 0;
}

.npc-proto__facts dt {
  color: var(--gold-400);
}

.npc-proto__facts dd {
  margin: 0;
}

.npc-proto__pane-hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--paper-400);
}

/* The service card's groups, on the production card (its `block` classes):
   the conditional group opens under a hairline, the services group under a
   hairline captioned 服務. The caption's alternative text is empty, so it
   never joins a row's accessible name. */
.npc-service-card__row--conditional .choice-card__label,
.npc-service-card__row--service .choice-card__label {
  color: var(--paper-100);
}

.choice-card.npc-service-card .choice-card__row.npc-service-card__row--conditional .choice-card__badge,
.choice-card.npc-service-card .choice-card__row.npc-service-card__row--service .choice-card__badge {
  font: var(--text-md)/1 var(--f-mono);
}

.npc-service-card__row--verb + .npc-service-card__row--conditional,
.npc-service-card__row--verb + .npc-service-card__row--service,
.npc-service-card__row--conditional + .npc-service-card__row--service,
.npc-service-card__row--verb + .npc-service-card__row--service-status,
.npc-service-card__row--conditional + .npc-service-card__row--service-status {
  margin-top: calc(9px * var(--ui-scale));
}

.npc-service-card__row--service,
.npc-service-card__row--service-status {
  scroll-margin-top: calc(20px * var(--ui-scale));
}

.npc-service-card__row--verb + .npc-service-card__row--service,
.npc-service-card__row--conditional + .npc-service-card__row--service,
.npc-service-card__row--verb + .npc-service-card__row--service-status,
.npc-service-card__row--conditional + .npc-service-card__row--service-status {
  margin-top: calc(22px * var(--ui-scale));
}

.npc-service-card__row--verb + .npc-service-card__row--conditional::after {
  content: "";
  position: absolute;
  left: calc(12px * var(--ui-scale));
  right: calc(12px * var(--ui-scale));
  top: calc(-6px * var(--ui-scale));
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(185, 154, 96, 0.34), transparent);
  pointer-events: none;
}

.npc-service-card__row--verb + .npc-service-card__row--service::after,
.npc-service-card__row--conditional + .npc-service-card__row--service::after,
.npc-service-card__row--verb + .npc-service-card__row--service-status::after,
.npc-service-card__row--conditional + .npc-service-card__row--service-status::after {
  content: "服務" / "";
  position: absolute;
  left: calc(12px * var(--ui-scale));
  right: calc(12px * var(--ui-scale));
  top: calc(-19px * var(--ui-scale));
  padding-left: calc(14px * var(--ui-scale));
  font: var(--text-xs)/1.4 var(--f-sans);
  letter-spacing: 0.3em;
  color: var(--gold-500);
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.45), transparent) no-repeat right center / calc(100% - 4.5em) 1px;
  pointer-events: none;
}

/* The unreadable line: a status, not an action (no caret fill promise). */
.npc-service-card__row--service-status {
  cursor: default;
}

.npc-service-card__row--service-status .choice-card__label {
  color: var(--paper-300);
}
</style>
