<script setup>
// Approved visual prototype of the party window
// (docs/superpowers/specs/2026-10-18-party-member-management-ui-design.md §6).
// Reference only: self-contained mock data, not wired to any payload.
// One window, five first-level tabs, one member rail whose selection
// persists across tabs. Identical whether or not the player is possessing.
import { computed, ref } from "vue";
import "./prototype.css";
import PmGlyph from "./PmGlyph.vue";
import MemberRail from "./MemberRail.vue";
import MemberTab from "./tabs/MemberTab.vue";
import BagTab from "./tabs/BagTab.vue";
import StatusTab from "./tabs/StatusTab.vue";
import SkillTab from "./tabs/SkillTab.vue";
import LineageTab from "./tabs/LineageTab.vue";
import { GENERAL_QUOTA, MEMBERS, PURSE } from "./prototype-data.js";

const props = defineProps({
  initialTab: { type: String, default: "member" },
  initialMember: { type: [Number, String], default: 1 },
  initialItem: { type: String, default: null },
  initialTrait: { type: String, default: null },
  initialSkill: { type: String, default: null },
  initialGraph: { type: String, default: null },
  combat: { type: Boolean, default: false },
});

const TABS = [
  { key: "member", label: "成員", glyph: "member" },
  { key: "bag", label: "背包", glyph: "inventory" },
  { key: "status", label: "狀態", glyph: "status" },
  { key: "skill", label: "技能", glyph: "skills" },
  { key: "lineage", label: "系譜", glyph: "lineage" },
];

const tab = ref(props.initialTab);
const memberId = ref(props.initialMember);
const member = computed(() => MEMBERS.find((m) => m.id === memberId.value) ?? null);
const unread = ref(new Set(MEMBERS.filter((m) => m.unread).map((m) => m.id)));
if (tab.value === "skill") unread.value.delete(memberId.value);

function selectTab(key) {
  tab.value = key;
  // The 空位 entry exists only on the 成員 tab; elsewhere fall back to the
  // commander.
  if (key !== "member" && typeof memberId.value !== "number") memberId.value = MEMBERS[0].id;
  if (key === "skill" && typeof memberId.value === "number") unread.value.delete(memberId.value);
}
function selectMember(id) {
  memberId.value = id;
  if (tab.value === "skill" && typeof id === "number") unread.value.delete(id);
}
function openSkill() {
  selectTab("skill");
}

const headerExtra = computed(() =>
  tab.value === "member"
    ? { text: `同伴 ${GENERAL_QUOTA.used} / ${GENERAL_QUOTA.limit}`, muted: true }
    : { text: `${PURSE.toLocaleString("en-US")} 銅`, glyph: "reward_copper" },
);
</script>

<template>
  <section class="pm" role="dialog" aria-label="隊伍">
    <header class="pm-head">
      <span class="pm-head__seal"><PmGlyph name="party" /></span>
      <h2 class="pm-head__title">隊伍</h2>
      <div class="pm-top" role="tablist" aria-label="隊伍分頁">
        <button
          v-for="t in TABS"
          :key="t.key"
          type="button"
          role="tab"
          class="pm-top__tab"
          :class="{ 'is-active': tab === t.key }"
          :aria-selected="tab === t.key"
          @click="selectTab(t.key)"
        >
          <PmGlyph :name="t.glyph" />
          <span class="pm-top__label">{{ t.label }}</span>
        </button>
      </div>
      <span class="pm-head__extra" :class="{ 'pm-head__extra--muted': headerExtra.muted }">
        <PmGlyph v-if="headerExtra.glyph" :name="headerExtra.glyph" />{{ headerExtra.text }}
      </span>
      <button type="button" class="pm-head__close" aria-label="關閉"><PmGlyph name="close" /></button>
    </header>

    <div class="pm-body" :class="{ 'pm-body--portrait': tab === 'member' }">
      <MemberRail
        :members="MEMBERS"
        :selected="memberId"
        :unread="unread"
        :show-empty="tab === 'member'"
        @select="selectMember"
      />
      <MemberTab v-if="tab === 'member'" :member-id="memberId" />
      <BagTab v-else-if="tab === 'bag'" :member="member" :combat="combat" :initial-item="initialItem" />
      <StatusTab v-else-if="tab === 'status'" :member="member" :initial-trait="initialTrait" />
      <SkillTab v-else-if="tab === 'skill'" :member="member" :combat="combat" :initial-skill="initialSkill" @lineage="selectTab('lineage')" />
      <LineageTab v-else :member="member" :initial-graph="initialGraph" @open-skill="openSkill" />
    </div>
  </section>
</template>
