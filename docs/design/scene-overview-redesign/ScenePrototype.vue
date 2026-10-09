<script setup>
// Approved-direction prototype of the exploration screen redesign
// (docs/superpowers/specs/2026-10-10-scene-overview-redesign-design.md).
// Reference only: self-contained mock data, not wired to any payload.
//
// The scene overview's chip rows are split by meaning:
// - movement → ExitCompass in the command panel (§3);
// - people and things → the PresenceRail on the stage floor, with a person's
//   verbs on the centred ChoiceCard while their standee enters (§4);
// - room actions → 查看房間 / 等待 on the place card, 建議 in the panel (§5);
// - one shared readout line explains whatever is aimed or hovered (§5.3).
import { computed, nextTick, onMounted, ref } from "vue";
import ExitCompassPrototype from "./ExitCompassPrototype.vue";
import ChoiceCardPrototype from "./ChoiceCardPrototype.vue";
import { resolveTargets, octantGlyph } from "./compass-model.js";
import { PLAYER, SUGGESTIONS, WAIT_OPTIONS, sceneById } from "./prototype-data.js";

const props = defineProps({
  startScene: { type: String, required: true },
  initialFocus: { type: String, default: null },
});

const RAIL_MAX = 6;

const sceneId = ref(props.startScene);
const scene = computed(() => sceneById(sceneId.value));
const targets = computed(() => resolveTargets(scene.value, sceneById));
const busy = ref(false);
const log = ref([]);
const hover = ref(null); // {lead, text, tone}
const flash = ref(null);
let flashTimer = null;

// Overlay state: null | {kind: "person", person} | {kind: "wait"} |
// {kind: "suggest"} | {kind: "overflow"}.
const overlay = ref(null);
const railEl = ref(null);
const railActive = ref(0);
let returnFocus = null;

// --- presence rail -------------------------------------------------------

const railItems = computed(() => {
  const s = scene.value;
  return [
    ...s.people.map((p) => ({ ...p, kind: "person" })),
    ...s.bystanders.map((p) => ({ ...p, kind: "bystander" })),
    ...s.objects.map((o) => ({ ...o, kind: "object" })),
  ];
});
const railShown = computed(() => {
  const items = railItems.value;
  if (items.length <= RAIL_MAX) {
    return items;
  }
  const shown = items.slice(0, RAIL_MAX - 1);
  shown.push({ id: "__more", kind: "more", name: `其餘 ${items.length - shown.length}`, count: items.length - shown.length });
  return shown;
});

function railSummary(item) {
  if (item.kind === "person") {
    return item.affordances.filter((a) => a.key !== "look").map((a) => a.label).join("／") || "查看";
  }
  if (item.kind === "more") {
    return "列出其餘在場者與物件";
  }
  return "查看";
}

function onRailHover(item) {
  hover.value = item ? { lead: item.kind === "object" ? "物件" : item.name, text: item.kind === "object" ? item.name + " · 查看" : railSummary(item) } : null;
}

function activateRail(item, el) {
  if (!item) {
    return;
  }
  returnFocus = el || railEl.value;
  if (item.kind === "person") {
    overlay.value = { kind: "person", person: item };
  } else if (item.kind === "more") {
    overlay.value = { kind: "overflow" };
  } else {
    say(`你查看了${item.name}。`);
  }
}

function onRailKey(event) {
  const n = railShown.value.length;
  if (n === 0) {
    return;
  }
  if (event.key === "ArrowRight") {
    railActive.value = (railActive.value + 1) % n;
  } else if (event.key === "ArrowLeft") {
    railActive.value = (railActive.value - 1 + n) % n;
  } else if (event.key === "Enter" || event.key === " ") {
    activateRail(railShown.value[railActive.value], railEl.value);
  } else {
    return;
  }
  event.preventDefault();
  onRailHover(railShown.value[railActive.value]);
}

// Digits 1–9 pick the rail's Nth entry anywhere in the exploration screen
// while no card is open (the card owns the digits while it is).
function onRootKey(event) {
  if (overlay.value || !/^[1-9]$/.test(event.key)) {
    return;
  }
  const item = railShown.value[Number(event.key) - 1];
  if (item) {
    event.preventDefault();
    railActive.value = Number(event.key) - 1;
    activateRail(item, railEl.value);
  }
}

// --- overlay cards -------------------------------------------------------

const card = computed(() => {
  const o = overlay.value;
  if (!o) {
    return null;
  }
  if (o.kind === "person") {
    return { caption: null, rows: o.person.affordances.map((a) => ({ key: a.key, label: a.label })) };
  }
  if (o.kind === "wait") {
    return { caption: "等待", rows: WAIT_OPTIONS };
  }
  if (o.kind === "suggest") {
    return { caption: "建議", rows: SUGGESTIONS };
  }
  return {
    caption: "在場",
    rows: railItems.value.slice(RAIL_MAX - 1).map((i) => ({ key: i.id, label: i.kind === "object" ? `◇ ${i.name}` : i.name })),
  };
});

function closeOverlay() {
  overlay.value = null;
  nextTick(() => returnFocus?.focus({ preventScroll: true }));
}

function onPick(key) {
  const o = overlay.value;
  if (o.kind === "person") {
    const p = o.person;
    const lines = {
      talk: `（進入與${p.name}的交談畫面，立繪留在場上）`,
      trade: `（開啟${p.name}的交易 drawer）`,
      guild: "（開啟公會服務 drawer）",
      engage: `（與${p.name}進入戰鬥）`,
      look: `你仔細打量著${p.name}。`,
    };
    say(lines[key]);
  } else if (o.kind === "overflow") {
    const item = railItems.value.find((i) => i.id === key);
    overlay.value = null;
    activateRail(item, returnFocus);
    return;
  } else {
    const row = card.value.rows.find((r) => r.key === key);
    say(`（送出：${row.label}）`);
  }
  closeOverlay();
}

// --- movement ------------------------------------------------------------

function say(line) {
  log.value = [...log.value.slice(-2), line];
}

function onMove(target) {
  busy.value = true;
  setTimeout(() => {
    sceneId.value = target.dest;
    busy.value = false;
    say(`你來到了${sceneById(target.dest).name}。`);
  }, 220);
}

function onAim(aim) {
  const t = aim.target;
  aimedKey.value = t && t.kind === "angled" ? t.key : null;
  if (!t) {
    hover.value = aim.angle === null ? null : { lead: octantGlyph(aim.angle), text: "這個方向沒有出口", tone: "quiet" };
    return;
  }
  if (!t.enabled) {
    hover.value = { lead: "無法通行", text: t.reason || t.destName, tone: "warn" };
  } else if (t.kind === "angled") {
    hover.value = { lead: `前往 ${octantGlyph(t.angle)}`, text: t.destName };
  } else {
    const glyph = t.vertical === "up" ? "⇧" : t.vertical === "down" ? "⇩" : "✦";
    hover.value = { lead: `通道 ${glyph}`, text: t.destName };
  }
}

function onBlocked(info) {
  const text =
    info.kind === "disabled"
      ? info.target.reason
      : info.kind === "no-exit"
        ? "這個方向沒有路了，停下腳步。"
        : "停下腳步。";
  flash.value = { lead: "停止", text, tone: "warn" };
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => {
    flash.value = null;
  }, 1600);
}

const readout = computed(() => {
  if (flash.value) {
    return flash.value;
  }
  if (hover.value) {
    return hover.value;
  }
  const exits = scene.value.exits.length;
  const people = scene.value.people.length + scene.value.bystanders.length;
  return { lead: "", text: `出口 ${exits} · 在場 ${people}`, tone: "quiet" };
});

// --- minimap (auxiliary: lights the aimed node) ---------------------------

const aimedKey = ref(null);
const minimapNodes = computed(() =>
  targets.value.angled.map((t) => {
    const rad = (t.angle * Math.PI) / 180;
    return { ...t, x: 50 + 30 * Math.sin(rad), y: 50 - 30 * Math.cos(rad) };
  }),
);

const actorFocus = computed(() => (overlay.value && overlay.value.kind === "person" ? overlay.value.person : null));

const placeButtons = {
  look: { lead: "查看房間", text: "重新觀察四周" },
  wait: { lead: "等待", text: "讓時間流逝、休息或睡眠" },
  suggest: { lead: "建議", text: `${SUGGESTIONS.length} 個可行的下一步` },
};

const rootEl = ref(null);
const compassHost = ref(null);
onMounted(() => {
  if (props.initialFocus) {
    const p = scene.value.people.find((x) => x.id === props.initialFocus);
    if (p) {
      overlay.value = { kind: "person", person: p };
      return;
    }
  }
  compassHost.value?.querySelector(".compass")?.focus({ preventScroll: true });
});
</script>

<template>
  <div ref="rootEl" class="proto" @keydown="onRootKey">
    <!-- top bar (unchanged; abbreviated) -->
    <header class="proto__top">
      <span class="proto__brand">ELOSERN <small>伊洛瑟恩</small></span>
      <nav>角色狀態　任務　背包　地圖　設定</nav>
      <span class="proto__who">{{ PLAYER.name }} ▾</span>
    </header>

    <!-- The band precedes the stage in DOM so the Tab order starts at the
         compass (spec §5.4); both are absolutely positioned. -->
    <section class="band" :class="{ 'band--muted': overlay }">
      <div class="band__msg">
        <p v-if="actorFocus" class="band__speaker">{{ actorFocus.name }}</p>
        <p class="band__room">{{ scene.name }}</p>
        <p>{{ scene.description }}</p>
        <p v-for="(line, i) in log" :key="i + line" class="band__log">{{ line }}</p>
      </div>
      <div class="cmd" :inert="overlay || null">
        <div ref="compassHost" class="cmd__compass">
          <ExitCompassPrototype
            :targets="targets"
            :busy="busy"
            @move="onMove"
            @aim="onAim"
            @blocked="onBlocked"
          />
        </div>
        <div class="cmd__side">
          <button
            type="button"
            class="cmd__suggest"
            @mouseenter="hover = placeButtons.suggest"
            @mouseleave="hover = null"
            @focus="hover = placeButtons.suggest"
            @blur="hover = null"
            @click="returnFocus = $event.currentTarget; overlay = { kind: 'suggest' }"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z" /></svg>
            建議 <b>{{ SUGGESTIONS.length }}</b>
          </button>
          <div class="readout" :class="readout.tone && `readout--${readout.tone}`" aria-live="polite">
            <span v-if="readout.lead" class="readout__lead">{{ readout.lead }}</span>
            <span class="readout__text">{{ readout.text }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="stage">
      <Transition name="art">
        <img :key="scene.art + sceneId" class="stage__art" :src="scene.art" alt="" />
      </Transition>
      <img class="stage__player" :src="PLAYER.portrait" alt="" />

      <Transition name="actor">
        <div v-if="actorFocus" class="stage__npc">
          <img v-if="actorFocus.portrait" :src="actorFocus.portrait" alt="" />
          <div v-else class="stage__silhouette">
            <span>{{ actorFocus.initial }}</span>
            <small>{{ actorFocus.name }}</small>
            <small class="dim">無肖像</small>
          </div>
        </div>
      </Transition>

      <!-- place card with its two room actions -->
      <div class="place" :class="{ 'stage__hud--away': actorFocus }" :inert="overlay || null">
        <div class="place__row">
          <h1 class="place__name">{{ scene.name }}</h1>
          <button
            type="button"
            class="place__btn"
            aria-label="查看房間"
            @mouseenter="hover = placeButtons.look"
            @mouseleave="hover = null"
            @focus="hover = placeButtons.look"
            @blur="hover = null"
            @click="say(`你環顧${scene.name}。${scene.description}`)"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6" /><path d="M15 15l5.5 5.5" /></svg>
          </button>
        </div>
        <div class="place__rule" />
        <div class="place__row">
          <span class="place__time">春季 12 日 · 10:41</span>
          <button
            type="button"
            class="place__btn place__btn--wait"
            @mouseenter="hover = placeButtons.wait"
            @mouseleave="hover = null"
            @focus="hover = placeButtons.wait"
            @blur="hover = null"
            @click="returnFocus = $event.currentTarget; overlay = { kind: 'wait' }"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9" /></svg>
            等待
          </button>
        </div>
      </div>

      <!-- minimap (auxiliary) -->
      <div class="mini" :class="{ 'stage__hud--away': actorFocus }" aria-hidden="true">
        <svg viewBox="0 0 100 100">
          <line v-for="n in minimapNodes" :key="'l' + n.key" x1="50" y1="50" :x2="n.x" :y2="n.y" class="mini__edge" />
          <circle v-for="n in minimapNodes" :key="n.key" :cx="n.x" :cy="n.y" r="4" class="mini__node" :class="{ 'mini__node--off': !n.enabled, 'mini__node--aim': aimedKey === n.key }" />
          <circle cx="50" cy="50" r="4" class="mini__here" />
        </svg>
      </div>

      <!-- presence rail -->
      <Transition name="rail">
        <div
          v-if="!overlay && railShown.length"
          ref="railEl"
          class="rail"
          tabindex="0"
          role="listbox"
          aria-label="在場"
          :aria-activedescendant="`rail-${railActive}`"
          @keydown="onRailKey"
          @focus="onRailHover(railShown[railActive])"
          @blur="onRailHover(null)"
        >
          <template v-for="(item, i) in railShown" :key="item.id">
            <span v-if="item.kind === 'object' && (i === 0 || railShown[i - 1].kind !== 'object')" class="rail__sep" />
            <div
              :id="`rail-${i}`"
              class="rail__item"
              :class="[`rail__item--${item.kind}`, { 'rail__item--active': railActive === i }]"
              role="option"
              @mouseenter="railActive = i; onRailHover(item)"
              @mouseleave="onRailHover(null)"
              @click="railActive = i; activateRail(item, railEl)"
            >
              <span class="rail__digit">{{ i + 1 }}</span>
              <span v-if="item.kind === 'object'" class="rail__gem" />
              <span v-else-if="item.kind === 'more'" class="rail__medal rail__medal--more">＋{{ item.count }}</span>
              <span v-else class="rail__medal" :class="{ 'rail__medal--dashed': item.kind === 'bystander' }">
                <img v-if="item.portrait" :src="item.portrait" alt="" />
                <span v-else>{{ item.initial }}</span>
              </span>
              <span class="rail__name">{{ item.kind === "more" ? "其餘" : item.name }}</span>
            </div>
          </template>
        </div>
      </Transition>

      <!-- centred card -->
      <div v-if="card" class="overlay">
        <ChoiceCardPrototype
          :key="overlay.kind + (overlay.person ? overlay.person.id : '')"
          :caption="card.caption"
          :rows="card.rows"
          @pick="onPick"
          @back="closeOverlay"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.proto {
  position: fixed;
  inset: 0;
  overflow: hidden;
  background: var(--ink-950);
  color: var(--paper-100);
  font-family: var(--f-serif);
  --hh: calc(48px * var(--ui-scale));
  --bh: clamp(190px * var(--ui-scale), 27.85vh, 400px * var(--ui-scale));
  --rc: calc(278px * var(--ui-scale));
}
.proto__top nav {
  color: var(--paper-200);
  letter-spacing: 0.1em;
}
.proto__top {
  position: absolute;
  inset: 0 0 auto 0;
  height: var(--hh);
  display: flex;
  align-items: center;
  gap: calc(40px * var(--ui-scale));
  padding: 0 calc(24px * var(--ui-scale));
  background: #0f1014;
  border-bottom: 1px solid #2a2724;
  font-size: var(--text-sm);
  color: var(--paper-300);
  z-index: 5;
}
.proto__brand {
  font-family: var(--f-display);
  letter-spacing: 0.2em;
  color: var(--paper-50);
}
.proto__brand small {
  font-size: var(--text-xs);
  letter-spacing: 0.1em;
  color: var(--paper-400);
}
.proto__who {
  margin-left: auto;
}

/* ---------- stage ---------- */
.stage {
  position: absolute;
  left: 0;
  right: 0;
  top: var(--hh);
  bottom: var(--bh);
  overflow: hidden;
}
.stage__art {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.art-enter-active,
.art-leave-active {
  transition: opacity 320ms var(--ease-standard);
}
.art-enter-from,
.art-leave-to {
  opacity: 0;
}
.stage__player {
  position: absolute;
  left: 12vw;
  bottom: 0;
  height: 92%;
  filter: drop-shadow(0 10px 30px rgba(0, 0, 0, 0.6));
}
.stage__npc {
  position: absolute;
  right: 6vw;
  bottom: 0;
  height: 92%;
  display: flex;
  align-items: flex-end;
}
.stage__npc img {
  height: 100%;
  filter: drop-shadow(0 10px 30px rgba(0, 0, 0, 0.6));
}
.stage__silhouette {
  width: calc(240px * var(--ui-scale));
  height: 100%;
  border-radius: 45% 45% 6% 6% / 22% 22% 6% 6%;
  background: linear-gradient(180deg, rgba(20, 22, 26, 0.85), rgba(20, 22, 26, 0.6));
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: calc(6px * var(--ui-scale));
}
.stage__silhouette span {
  font: var(--text-initial) / 1 var(--f-display);
  color: var(--gold-400);
}
.stage__silhouette small {
  font-size: var(--text-sm);
  color: var(--paper-200);
}
.stage__silhouette .dim {
  color: var(--paper-400);
}
.actor-enter-active,
.actor-leave-active {
  transition: transform 320ms var(--ease-standard), opacity 320ms var(--ease-standard);
}
.actor-enter-from,
.actor-leave-to {
  transform: translateX(30%);
  opacity: 0;
}

/* A person in focus takes the stage like the dialogue screen: the place
   card and the minimap step away. */
.place,
.mini {
  transition: opacity var(--motion-reveal) var(--ease-standard);
}
.stage__hud--away {
  opacity: 0;
  pointer-events: none;
}

/* place card */
.place {
  position: absolute;
  top: calc(14px * var(--ui-scale));
  right: calc(16px * var(--ui-scale));
  width: var(--rc);
  box-sizing: border-box;
  padding: calc(10px * var(--ui-scale)) calc(14px * var(--ui-scale));
  background: rgba(15, 17, 21, 0.88);
  border: 1px solid #3a3530;
  border-radius: var(--radius-sm);
}
.place__row {
  display: flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
}
.place__name {
  flex: 1;
  min-width: 0;
  margin: 0;
  font: var(--text-xl) / 1.3 var(--f-serif);
  font-weight: 500;
  color: var(--paper-50);
  letter-spacing: 0.08em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.place__rule {
  height: 1px;
  margin: calc(6px * var(--ui-scale)) 0;
  background: linear-gradient(90deg, var(--gold-500), transparent 60%);
}
.place__time {
  flex: 1;
  font: var(--text-sm) / 1.4 var(--f-sans);
  color: var(--paper-300);
}
.place__btn {
  display: inline-flex;
  align-items: center;
  gap: calc(4px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  min-width: calc(30px * var(--ui-scale));
  padding: 0 calc(6px * var(--ui-scale));
  justify-content: center;
  background: transparent;
  border: 1px solid #736b5c;
  border-radius: var(--radius-sm);
  color: var(--paper-200);
  font: var(--text-xs) / 1 var(--f-sans);
  cursor: pointer;
}
.place__btn svg,
.cmd__suggest svg {
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  fill: none;
  stroke: currentColor;
  stroke-width: 1.6;
  stroke-linecap: round;
}
.place__btn:hover,
.place__btn:focus-visible,
.cmd__suggest:hover,
.cmd__suggest:focus-visible {
  border-color: var(--gold-500);
  color: var(--paper-50);
  background: var(--gold-glow);
  outline: none;
}

/* minimap */
.mini {
  position: absolute;
  top: calc(120px * var(--ui-scale));
  right: calc(16px * var(--ui-scale));
  width: var(--rc);
  aspect-ratio: 1.15;
  box-sizing: border-box;
  background: rgba(15, 17, 21, 0.82);
  border: 1px solid #3a3530;
  border-radius: var(--radius-sm);
}
.mini svg {
  width: 100%;
  height: 100%;
}
.mini__edge {
  stroke: #4a453d;
  stroke-width: 0.8;
}
.mini__node {
  fill: none;
  stroke: var(--gold-500);
  stroke-width: 1.2;
}
.mini__node--off {
  stroke-dasharray: 1.5 1.5;
  stroke: #8c826e;
}
.mini__node--aim {
  stroke: var(--gold-300);
  stroke-width: 2.4;
  fill: rgba(228, 200, 142, 0.25);
}
.mini__here {
  fill: var(--seal-500);
}

/* presence rail */
.rail {
  position: absolute;
  right: calc(var(--rc) + 48px * var(--ui-scale));
  bottom: calc(14px * var(--ui-scale));
  display: flex;
  align-items: flex-end;
  gap: calc(14px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(4px * var(--ui-scale));
  border-radius: var(--radius);
  outline: none;
}
.rail:focus-visible {
  box-shadow: 0 0 0 1px var(--gold-500);
  background: rgba(10, 11, 14, 0.35);
}
.rail-enter-active,
.rail-leave-active {
  transition: opacity var(--motion-reveal) var(--ease-standard);
}
.rail-enter-from,
.rail-leave-to {
  opacity: 0;
}
.rail__sep {
  align-self: center;
  width: 1px;
  height: calc(52px * var(--ui-scale));
  background: linear-gradient(transparent, #8a7550, transparent);
}
.rail__item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: calc(4px * var(--ui-scale));
  cursor: pointer;
}
.rail__medal {
  width: calc(64px * var(--ui-scale));
  height: calc(64px * var(--ui-scale));
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--gold-500);
  background: radial-gradient(circle at 40% 35%, #3b3326, #16130f);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.6);
  font: var(--text-2xl) / 1 var(--f-display);
  color: var(--gold-300);
  transition: transform 120ms var(--ease-standard), box-shadow 120ms;
}
.rail__medal img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: 50% 8%;
  transform: scale(1.9);
  transform-origin: 50% 12%;
}
.rail__medal--dashed {
  border-style: dashed;
  border-color: #8c826e;
  color: var(--paper-300);
}
.rail__medal--more {
  font: var(--text-md) / 1 var(--f-sans);
  border-color: #736b5c;
  color: var(--paper-200);
}
.rail__gem {
  width: calc(36px * var(--ui-scale));
  height: calc(36px * var(--ui-scale));
  margin: calc(14px * var(--ui-scale)) 0;
  transform: rotate(45deg);
  border: 2px solid #9aa3ad;
  background: radial-gradient(circle at 40% 35%, #2c3138, #121519);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.6);
}
.rail__name {
  max-width: calc(120px * var(--ui-scale));
  padding: 0 calc(6px * var(--ui-scale));
  border-radius: var(--radius-sm);
  background: rgba(10, 11, 14, 0.78);
  font: var(--text-xs) / 1.5 var(--f-sans);
  color: var(--paper-100);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rail__digit {
  position: absolute;
  top: calc(-4px * var(--ui-scale));
  left: calc(-4px * var(--ui-scale));
  z-index: 1;
  min-width: calc(20px * var(--ui-scale));
  height: calc(20px * var(--ui-scale));
  border-radius: 50%;
  background: var(--ink-900);
  border: 1px solid #736b5c;
  font: calc(13px * var(--ui-scale)) / calc(18px * var(--ui-scale)) var(--f-sans);
  text-align: center;
  color: var(--paper-300);
  opacity: 0;
  transition: opacity 120ms;
}
.rail:focus-visible .rail__digit,
.rail__item:hover .rail__digit {
  opacity: 1;
}
.rail__item--active .rail__medal,
.rail__item:hover .rail__medal {
  transform: translateY(calc(-4px * var(--ui-scale)));
  border-color: var(--gold-300);
  box-shadow: 0 0 0 3px var(--gold-glow), 0 8px 20px rgba(0, 0, 0, 0.6);
}
.rail__item--active .rail__gem,
.rail__item:hover .rail__gem {
  border-color: #dfe7ef;
  box-shadow: 0 0 0 3px rgba(200, 215, 230, 0.2);
}
.rail__item--active .rail__name {
  color: var(--paper-50);
  box-shadow: inset 0 -2px 0 var(--gold-500);
}

/* centred card */
.overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, transparent 20%, rgba(5, 6, 8, 0.35) 50%, transparent 80%);
}

/* ---------- band ---------- */
.band {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: var(--bh);
  display: grid;
  grid-template-columns: 2fr 1fr;
  background: linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel));
  border-top: 1px solid #4a4134;
  z-index: 2;
}
.band__msg {
  padding: calc(18px * var(--ui-scale)) calc(28px * var(--ui-scale)) 0 10vw;
  font: var(--text-base) / 1.6 var(--f-serif);
  color: var(--paper-200);
  overflow: hidden;
}
.band__msg p {
  margin: 0;
}
.band__speaker {
  font-size: var(--text-sm);
  color: var(--gold-400);
  letter-spacing: 0.1em;
}
.band__room {
  color: #9cc3d6;
}
.band__log {
  color: var(--paper-300);
}
.cmd {
  box-sizing: border-box;
  height: var(--bh);
  display: flex;
  gap: calc(12px * var(--ui-scale));
  padding: calc(10px * var(--ui-scale)) calc(16px * var(--ui-scale)) calc(12px * var(--ui-scale));
  border-left: 1px solid #2c2822;
  min-width: 0;
  transition: opacity var(--motion-reveal);
}
.band--muted .cmd {
  opacity: 0.35;
}
.cmd__compass {
  --compass-d: calc(var(--bh) - 22px * var(--ui-scale));
  width: var(--compass-d);
  height: var(--compass-d);
  flex: none;
}
.cmd__side {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: stretch;
  gap: calc(8px * var(--ui-scale));
}
.cmd__suggest {
  align-self: flex-end;
  display: inline-flex;
  align-items: center;
  gap: calc(6px * var(--ui-scale));
  height: calc(34px * var(--ui-scale));
  padding: 0 calc(10px * var(--ui-scale));
  background: transparent;
  border: 1px solid #736b5c;
  border-radius: var(--radius-pill);
  color: var(--paper-200);
  font: var(--text-xs) / 1 var(--f-sans);
  cursor: pointer;
}
.cmd__suggest b {
  font-weight: 500;
  color: var(--gold-300);
}
.readout {
  display: flex;
  flex-direction: column;
  gap: calc(2px * var(--ui-scale));
  min-height: calc(58px * var(--ui-scale));
  justify-content: center;
  padding: calc(6px * var(--ui-scale)) calc(10px * var(--ui-scale));
  border-left: 2px solid var(--gold-500);
  background: var(--ink-900);
  min-width: 0;
}
.readout__lead {
  font: var(--text-xs) / 1.3 var(--f-sans);
  color: var(--gold-400);
  letter-spacing: 0.06em;
}
.readout__text {
  font: var(--text-md) / 1.35 var(--f-serif);
  color: var(--paper-50);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
.readout--quiet {
  border-left-color: #55524b;
}
.readout--quiet .readout__text {
  color: var(--paper-300);
  font-size: var(--text-sm);
}
.readout--warn {
  border-left-color: var(--seal-500);
}
.readout--warn .readout__lead {
  color: var(--seal-400);
}
</style>
