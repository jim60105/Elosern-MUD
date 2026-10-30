<script setup>
// The party in travel mode (prototype): round face medallions instead of
// standing portraits. Each carries the member's 精力 as a thin bar with the
// stage thresholds (70 / 40 / 20 %) notched in, the stage name when it is not
// 精神充沛, and a crescent while asleep. The controlled member is ringed.
import { RESERVE_FULL, stageOf } from "./travel-model.js";

defineProps({
  members: { type: Array, required: true },
  controlled: { type: String, default: null },
});

function percent(reserve) {
  return Math.round((reserve / RESERVE_FULL) * 100);
}
</script>

<template>
  <ul class="party-medallions" aria-label="隊伍">
    <li
      v-for="m in members"
      :key="m.id"
      class="party-medallion"
      :class="[`is-${stageOf(m.reserve).key}`, { 'is-controlled': m.id === controlled, 'is-asleep': m.asleep }]"
      :aria-label="`${m.name}：精力 ${percent(m.reserve)}%（${m.asleep ? '沉睡' : stageOf(m.reserve).label}）`"
    >
      <span class="party-medallion__face" :style="{ backgroundImage: `url(${m.portrait})` }">
        <span v-if="m.asleep" class="party-medallion__moon" aria-hidden="true"></span>
      </span>
      <span class="party-medallion__name">{{ m.name }}</span>
      <span class="party-medallion__bar" aria-hidden="true">
        <span class="party-medallion__fill" :style="{ width: `${percent(m.reserve)}%` }"></span>
        <i style="left: 20%"></i><i style="left: 40%"></i><i style="left: 70%"></i>
      </span>
      <span v-if="!m.asleep && stageOf(m.reserve).key !== 'normal'" class="party-medallion__stage">
        {{ stageOf(m.reserve).label }}
      </span>
    </li>
  </ul>
</template>

<style>
.party-medallions {
  display: flex;
  gap: calc(14px * var(--ui-scale));
  margin: 0;
  padding: calc(10px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(8px * var(--ui-scale));
  list-style: none;
  border-radius: calc(10px * var(--ui-scale));
  background: radial-gradient(120% 140% at 30% 100%, rgba(11, 13, 16, 0.85), rgba(11, 13, 16, 0) 75%);
}
.party-medallion {
  display: grid;
  justify-items: center;
  gap: calc(3px * var(--ui-scale));
  width: calc(76px * var(--ui-scale));
}
.party-medallion__face {
  position: relative;
  width: calc(60px * var(--ui-scale));
  height: calc(60px * var(--ui-scale));
  border-radius: 50%;
  background-size: 220%;
  background-position: 50% 9%;
  background-color: var(--ink-800);
  border: 1.5px solid var(--gold-500);
  box-shadow: 0 0 0 3px var(--ink-950), 0 6px 16px rgba(0, 0, 0, 0.55);
  transition: filter var(--motion-base) var(--ease-standard);
}
.party-medallion.is-controlled .party-medallion__face {
  border-color: var(--gold-300);
  box-shadow: 0 0 0 3px var(--ink-950), 0 0 0 4.5px rgba(228, 200, 142, 0.6), 0 6px 16px rgba(0, 0, 0, 0.55);
}
.party-medallion.is-light .party-medallion__face {
  filter: saturate(0.85);
}
.party-medallion.is-moderate .party-medallion__face {
  filter: saturate(0.65) brightness(0.9);
}
.party-medallion.is-severe .party-medallion__face,
.party-medallion.is-asleep .party-medallion__face {
  filter: saturate(0.35) brightness(0.75);
}
.party-medallion__moon {
  position: absolute;
  right: calc(-4px * var(--ui-scale));
  top: calc(-4px * var(--ui-scale));
  width: calc(22px * var(--ui-scale));
  height: calc(22px * var(--ui-scale));
  border-radius: 50%;
  background: radial-gradient(circle at 65% 40%, #10131c 46%, transparent 47%), #c8d4ee;
  box-shadow: 0 0 0 2px var(--ink-950), 0 0 12px rgba(170, 190, 230, 0.5);
}
.party-medallion__name {
  font: var(--text-xs)/1.2 var(--f-serif);
  color: var(--paper-50);
  text-shadow: 0 1px 3px #000;
}
.party-medallion__bar {
  position: relative;
  width: 100%;
  height: calc(5px * var(--ui-scale));
  border-radius: 3px;
  background: rgba(36, 38, 42, 0.95);
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(58, 56, 51, 0.9);
}
.party-medallion__fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(90deg, #a98432, var(--vit-sp));
  transition: width var(--motion-slow) var(--ease-standard);
}
.party-medallion.is-light .party-medallion__fill {
  background: var(--warn);
}
.party-medallion.is-moderate .party-medallion__fill,
.party-medallion.is-severe .party-medallion__fill {
  background: #c46a4f;
}
.party-medallion__bar i {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(11, 13, 16, 0.85);
}
.party-medallion__stage {
  font: var(--text-xs)/1.1 var(--f-sans);
  color: var(--warn);
  white-space: nowrap;
}
.party-medallion.is-moderate .party-medallion__stage,
.party-medallion.is-severe .party-medallion__stage {
  color: #e08a6a;
}
</style>
