<script setup>
// Approved visual prototype (party member management §6.4): the 技能 tab.
// The SkillBook content in the shared frame, per viewed member: proficiency
// meters, 新 tags, lineage position, and 施放 / 排入修煉 for that member.
// In combat both actions are disabled with their reason.
import { computed, ref, watch } from "vue";
import PmGlyph from "../PmGlyph.vue";
import { SKILLS } from "../prototype-data.js";

const props = defineProps({
  member: { type: Object, required: true },
  combat: { type: Boolean, default: false },
  initialSkill: { type: String, default: null },
});
const emit = defineEmits(["lineage"]);

const kind = ref("active");
const query = ref("");
const book = computed(() => SKILLS[props.member.id]);
const groups = computed(() =>
  book.value[kind.value]
    .map((g) => ({ ...g, skills: g.skills.filter((s) => !query.value || s.name.includes(query.value)) }))
    .filter((g) => g.skills.length),
);
const all = computed(() => groups.value.flatMap((g) => g.skills));
const selected = ref(null);
watch(
  () => [props.member.id, kind.value, query.value],
  () => {
    if (!all.value.some((s) => s.key === selected.value)) {
      selected.value = all.value.find((s) => s.key === props.initialSkill)?.key ?? all.value[0]?.key ?? null;
    }
  },
  { immediate: true },
);
const skill = computed(() => all.value.find((s) => s.key === selected.value) ?? null);

const castReason = computed(() => {
  if (props.combat) return "戰鬥中請使用指令卡";
  if (props.member.knocked_out) return `${props.member.name}倒地中`;
  if (skill.value && !skill.value.field) return "此技能無法在戰鬥外施放";
  return null;
});
</script>

<template>
  <div class="pm-col pm-list">
    <div class="sk-seg" role="tablist" aria-label="技能種類">
      <button type="button" role="tab" :aria-selected="kind === 'active'" :class="{ 'is-active': kind === 'active' }" @click="kind = 'active'">主動 {{ book.active.reduce((n, g) => n + g.skills.length, 0) }}</button>
      <button type="button" role="tab" :aria-selected="kind === 'passive'" :class="{ 'is-active': kind === 'passive' }" @click="kind = 'passive'">被動 {{ book.passive.reduce((n, g) => n + g.skills.length, 0) }}</button>
    </div>
    <label class="sk-search"><PmGlyph name="look" /><input v-model="query" type="search" placeholder="搜尋技能" aria-label="搜尋技能" /></label>
    <template v-for="g in groups" :key="g.category">
      <div class="pm-sech">{{ g.category }}</div>
      <button
        v-for="s in g.skills"
        :key="s.key"
        type="button"
        role="option"
        class="pm-row"
        :class="{ 'is-selected': s.key === selected }"
        :aria-selected="s.key === selected"
        @click="selected = s.key"
      >
        <span class="pm-icon"><PmGlyph :name="s.icon" /></span>
        <span class="pm-row__name">{{ s.name }}<span v-if="s.fresh" class="pm-tag pm-tag--new">新</span>
          <span class="pm-meter" :class="{ 'pm-meter--capped': s.capped }"><i :style="{ width: `${Math.round(s.progress * 100)}%` }" /></span>
        </span>
        <span class="pm-row__end">{{ s.capped ? "見頂" : `Lv ${s.level}` }}</span>
      </button>
    </template>
  </div>

  <div class="pm-col pm-detail">
    <template v-if="skill">
      <div class="pm-detail__scroll">
        <span class="pm-ribbon"><PmGlyph :name="skill.icon" />{{ kind === "active" ? "主動" : "被動" }}</span>
        <h3 class="pm-hero__title">{{ skill.name }}</h3>
        <div class="pm-facts">
          <div class="pm-fact">目標<b>{{ skill.target }}</b></div>
          <div class="pm-fact">消耗<b>{{ skill.cost }}</b></div>
          <div class="pm-fact">戰鬥外<b>{{ skill.field ? "可施放" : "不可" }}</b></div>
        </div>
        <template v-if="skill.rungs.length || skill.locked_rungs.length">
          <div class="pm-label">威力階段</div>
          <div class="sk-rungs"><span v-for="r in skill.rungs" :key="r">{{ r }}</span><span v-for="r in skill.locked_rungs" :key="r" class="is-locked"><PmGlyph name="lock" />{{ r }}</span></div>
        </template>
        <div class="pm-label">熟練度</div>
        <div class="sk-prog">
          <span>{{ skill.capped ? "見頂" : `Lv ${skill.level}` }}</span>
          <span class="pm-gauge__track"><i :style="{ width: `${Math.round(skill.progress * 100)}%`, background: skill.capped ? 'var(--gold-300)' : 'var(--gold-500)' }" /></span>
          <span>{{ Math.round(skill.progress * 100) }} / 100</span>
        </div>
        <div class="pm-label">系譜位置</div>
        <div class="sk-path">
          <span class="sk-node" :class="{ 'is-none': skill.path[0] === '—' }">{{ skill.path[0] }}</span>→
          <span class="sk-node is-current">{{ skill.path[1] }}</span>→
          <span class="sk-node" :class="skill.path[2] === '—' ? 'is-none' : 'is-locked'">{{ skill.path[2] }}</span>
          <button type="button" class="sk-link" @click="emit('lineage')">在系譜中檢視</button>
        </div>
      </div>
      <div class="pm-bar">
        <span v-if="castReason" class="pm-bar__reason">{{ castReason }}</span>
        <button type="button" class="pm-btn pm-btn--gold" :aria-disabled="combat || kind === 'passive'">排入修煉</button>
        <button v-if="kind === 'active'" type="button" class="pm-btn pm-btn--primary" :aria-disabled="Boolean(castReason)">施放</button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.sk-seg { display: flex; margin-bottom: var(--sp-3); border: 1px solid var(--pm-line); border-radius: var(--radius-sm); overflow: hidden; }
.sk-seg button { flex: 1; padding: var(--sp-1) 0; color: var(--paper-500); font-size: var(--text-xs); background: transparent; border: 0; cursor: pointer; }
.sk-seg button.is-active { color: var(--gold-300); background: rgba(207, 68, 68, 0.2); }
.sk-search { display: flex; align-items: center; gap: var(--sp-2); padding: var(--sp-1) var(--sp-3); color: var(--paper-500); border: 1px solid var(--ink-600); border-radius: var(--radius-sm); }
.sk-search input { flex: 1; min-width: 0; color: var(--paper-100); font: var(--text-xs) var(--f-sans); background: transparent; border: 0; outline: none; }
.sk-rungs { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
.sk-rungs span { display: inline-flex; align-items: center; gap: var(--sp-1); padding: 2px var(--sp-3); color: var(--paper-100); font-size: var(--text-xs); border: 1px solid var(--pm-line); border-radius: var(--radius-sm); }
.sk-rungs span.is-locked { color: var(--paper-700); border-style: dashed; }
.sk-prog { display: grid; grid-template-columns: auto 1fr auto; gap: var(--sp-3); align-items: center; color: var(--paper-200); font: var(--text-xs) var(--f-num); }
.sk-path { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-2); color: var(--paper-500); font-size: var(--text-xs); }
.sk-node { padding: 2px var(--sp-3); color: var(--paper-100); border: 1px solid var(--pm-line); border-radius: var(--radius-sm); }
.sk-node.is-current { color: var(--gold-300); border-color: var(--seal-500); }
.sk-node.is-locked { color: var(--paper-500); border-style: dashed; }
.sk-node.is-none { color: var(--paper-700); border-color: transparent; }
.sk-link { margin-left: var(--sp-2); padding: 0; color: var(--gold-400); font-size: var(--text-xs); text-decoration: underline; text-underline-offset: 3px; background: none; border: 0; cursor: pointer; }
</style>
