<script setup>
// Approved visual prototype (party member management §6.3): the 狀態 tab.
// One layout for every member. Selecting a trait shows its breakdown as a
// waterfall (base → each layer with source bar, glyph, and text → effective);
// selecting a condition shows its source, remaining time, and modifiers.
import { computed, ref, watch } from "vue";
import PmGlyph from "../PmGlyph.vue";
import { CHARACTER } from "../prototype-data.js";

const props = defineProps({
  member: { type: Object, required: true },
  initialTrait: { type: String, default: null },
});

const SOURCE = {
  equipment: { label: "裝備", glyph: "armor" },
  skill: { label: "技能", glyph: "skills" },
  condition: { label: "狀態", glyph: "buff" },
};
const KIND = { flat: "固定值", pct: "百分比", mult: "倍率" };

const ch = computed(() => CHARACTER[props.member.id]);
const selection = ref(null);
watch(
  () => props.member.id,
  () => {
    const wanted = props.initialTrait && ch.value.traits.find((t) => t.key === props.initialTrait);
    const first = wanted ?? ch.value.traits.find((t) => t.layers.length) ?? ch.value.traits[0];
    selection.value = { type: "trait", key: first.key };
  },
  { immediate: true },
);
const trait = computed(() => (selection.value?.type === "trait" ? ch.value.traits.find((t) => t.key === selection.value.key) : null));
const condition = computed(() => (selection.value?.type === "condition" ? ch.value.conditions.find((c) => c.code === selection.value.key) : null));

function pct([cur, max]) {
  return `${max ? Math.round((cur / max) * 100) : 0}%`;
}
function signed(layer) {
  const sign = layer.amount > 0 ? "+" : "−";
  const value = Math.abs(layer.amount);
  return layer.kind === "pct" ? `${sign}${value}%` : layer.kind === "mult" ? `×${layer.amount}` : `${sign}${value}`;
}
function trend(t) {
  return t.effective > t.base ? "pm-up" : t.effective < t.base ? "pm-down" : "";
}
</script>

<template>
  <div class="pm-col pm-list">
    <div class="st-hero">
      <span class="pm-avatar pm-avatar--lg">{{ member.initial }}</span>
      <div class="st-hero__id"><h3>{{ member.name }}</h3><small>{{ member.title }}</small></div>
      <div v-if="ch.guild.rank" class="st-guild"><span class="pm-gem" :class="`pm-gem--${ch.guild.rank}`"><span>{{ ch.guild.rank }}</span></span>功績 {{ ch.guild.merit }}</div>
    </div>
    <div class="pm-gauge"><span style="color: var(--vit-hp)">HP</span><span class="pm-gauge__track"><i :style="{ width: pct(member.hp), background: 'var(--vit-hp)' }" /></span><span class="pm-gauge__value">{{ member.hp[0] }} / {{ member.hp[1] }}</span></div>
    <div class="pm-gauge"><span style="color: var(--vit-mp)">MP</span><span class="pm-gauge__track"><i :style="{ width: pct(member.mp), background: 'var(--vit-mp)' }" /></span><span class="pm-gauge__value">{{ member.mp[0] }} / {{ member.mp[1] }}</span></div>
    <div class="pm-gauge"><span style="color: var(--vit-sp)">SP</span><span class="pm-gauge__track"><i :style="{ width: pct(member.sp), background: 'var(--vit-sp)' }" /></span><span class="pm-gauge__value">{{ member.sp[0] }} / {{ member.sp[1] }}</span></div>

    <div class="pm-sech">屬性<span class="pm-sech__count">基礎 → 有效</span></div>
    <div role="listbox" aria-label="屬性與狀態">
      <button
        v-for="t in ch.traits"
        :key="t.key"
        type="button"
        role="option"
        class="pm-row st-trait"
        :class="{ 'is-selected': trait?.key === t.key }"
        :aria-selected="trait?.key === t.key"
        @click="selection = { type: 'trait', key: t.key }"
      >
        <span class="pm-row__name">{{ t.label }}</span>
        <span class="st-base">{{ t.base }}</span>
        <span class="st-eff" :class="trend(t)">{{ t.effective }}<small v-if="t.effective !== t.base">{{ t.effective > t.base ? "▲" : "▼" }}</small></span>
      </button>

      <div class="pm-sech">狀態<span class="pm-sech__count">{{ ch.conditions.length }}</span></div>
      <p v-if="!ch.conditions.length" class="st-empty">無</p>
      <button
        v-for="c in ch.conditions"
        :key="c.code"
        type="button"
        role="option"
        class="pm-row"
        :class="{ 'is-selected': condition?.code === c.code }"
        :aria-selected="condition?.code === c.code"
        @click="selection = { type: 'condition', key: c.code }"
      >
        <span class="st-cond" :class="`st-cond--${c.severity}`"><PmGlyph :name="c.severity === 'buff' ? 'buff' : 'debuff'" /></span>
        <span class="pm-row__name">{{ c.label }}<span v-if="c.remaining" class="pm-row__sub">剩 {{ c.remaining }}</span></span>
        <span class="pm-row__end">{{ c.modifiers }}</span>
      </button>
    </div>
  </div>

  <div class="pm-col pm-detail">
    <div class="pm-detail__scroll">
      <template v-if="trait">
        <span class="pm-ribbon">屬性</span>
        <h3 class="pm-hero__title">{{ trait.label }} {{ trait.effective }}</h3>
        <div class="st-fall">
          <div class="st-step"><span /><span>基礎值</span><span class="st-amt">{{ trait.base }}</span></div>
          <div v-for="(l, i) in trait.layers" :key="i" class="st-step" :class="`st-step--${l.source}`">
            <PmGlyph :name="SOURCE[l.source].glyph" />
            <span>{{ l.name }}<small>{{ SOURCE[l.source].label }} ‧ {{ KIND[l.kind] }}</small></span>
            <span class="st-amt" :class="l.amount > 0 ? 'pm-up' : 'pm-down'">{{ signed(l) }}</span>
          </div>
          <div class="st-step st-step--total"><span /><span>有效值</span><span class="st-amt">{{ trait.effective }}</span></div>
        </div>
      </template>
      <template v-else-if="condition">
        <span class="pm-ribbon"><PmGlyph :name="condition.severity === 'buff' ? 'buff' : 'debuff'" />{{ condition.severity === "buff" ? "增益" : "減益" }}</span>
        <h3 class="pm-hero__title">{{ condition.label }}</h3>
        <div class="pm-facts">
          <div class="pm-fact">來源<b>{{ condition.source }}</b></div>
          <div class="pm-fact">剩餘<b>{{ condition.remaining ?? "—" }}</b></div>
          <div class="pm-fact">修正<b>{{ condition.modifiers }}</b></div>
        </div>
      </template>
    </div>
    <div v-if="ch.disguise" class="st-disguise">
      <b>偽裝中</b>{{ ch.disguise.description }}
      <span>對外顯示：<template v-for="([label, value], i) in ch.disguise.displayed" :key="label">{{ i ? "、" : "" }}{{ label }} {{ value }}</template></span>
    </div>
  </div>
</template>

<style scoped>
.st-hero { display: flex; align-items: center; gap: var(--sp-3); padding-bottom: var(--sp-3); margin-bottom: var(--sp-2); border-bottom: 1px solid var(--pm-line); }
.st-hero__id h3 { margin: 0; color: var(--paper-50); font: var(--text-xl) var(--f-display); }
.st-hero__id small { color: var(--gold-400); font-size: var(--text-xs); }
.st-guild { margin-left: auto; display: grid; justify-items: center; gap: var(--sp-2); color: var(--paper-500); font-size: var(--text-xs); }
.st-trait { grid-template-columns: minmax(0, 1fr) auto auto; }
.st-base { color: var(--paper-500); font: var(--text-xs) var(--f-num); }
.st-eff { min-width: calc(48px * var(--ui-scale)); text-align: right; color: var(--paper-50); font: 600 var(--text-lg) var(--f-num); }
.st-eff small { margin-left: 2px; font-size: var(--text-xs); }
.st-eff.pm-up { color: var(--buff); }
.st-eff.pm-down { color: var(--debuff); }
.st-empty { margin: 0; padding: var(--sp-2) var(--sp-3); color: var(--paper-700); }
.st-cond { display: grid; place-items: center; width: calc(26px * var(--ui-scale)); height: calc(26px * var(--ui-scale)); font-size: calc(15px * var(--ui-scale)); border-radius: 50%; border: 1px solid; }
.st-cond--buff { color: var(--buff); border-color: var(--buff); }
.st-cond--debuff { color: var(--debuff); border-color: var(--debuff); border-radius: 3px; }
.st-fall { display: grid; gap: var(--sp-1); margin-top: var(--sp-4); }
.st-step {
  display: grid;
  grid-template-columns: calc(20px * var(--ui-scale)) 1fr auto;
  gap: var(--sp-3);
  align-items: center;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-200);
  background: rgba(0, 0, 0, 0.2);
  border-left: 3px solid var(--ink-600);
  border-radius: var(--radius-sm);
}
.st-step small { margin-left: var(--sp-2); color: var(--paper-500); font-size: var(--text-xs); }
.st-step--equipment { border-left-color: var(--pm-src-equipment); color: var(--paper-100); }
.st-step--equipment .pm-glyph { color: var(--pm-src-equipment); }
.st-step--skill { border-left-color: var(--pm-src-skill); }
.st-step--skill .pm-glyph { color: var(--pm-src-skill); }
.st-step--condition { border-left-color: var(--pm-src-condition); }
.st-step--condition .pm-glyph { color: var(--pm-src-condition); }
.st-step--total { border-left-color: var(--seal-500); background: rgba(207, 68, 68, 0.1); font-weight: 600; }
.st-amt { font: var(--text-md) var(--f-num); font-variant-numeric: tabular-nums; }
.st-step--total .st-amt { color: var(--paper-50); font-size: var(--text-xl); }
.st-disguise {
  margin-top: var(--sp-3);
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-400);
  font-size: var(--text-xs);
  line-height: 1.7;
  border: 1px dashed var(--gold-600);
  border-radius: var(--radius-sm);
}
.st-disguise b { margin-right: var(--sp-2); color: var(--gold-300); font-weight: 500; }
.st-disguise span { display: block; }
</style>
