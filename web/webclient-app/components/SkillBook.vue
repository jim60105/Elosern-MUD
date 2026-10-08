<script setup>
// SkillBook (skillbook-authoritative-casting D8): the character's skills as a
// master–detail spellbook. The left column is a keyboard tree over the
// committed `character` payload's own category → group → skill order (never
// re-sorted): category headers collapse/expand, skill rows select. The right
// column is a sticky detail card for the selected row — target shape, cost,
// the advertised 威力 rungs, the truthful field capability, and the two
// actions: 施放 (hand the cast to the dock through the authoritative server
// preview) and 修煉 (the bounded declared-practice sub-screen).
//
// Nothing here decides availability. The capability line restates the
// static `usable_out_of_combat` flag only; whether a cast is possible right
// now, and at whom, is the server preview's answer once 施放 is pressed. A
// row the payload gives without detail fields (an unregistered key) renders
// without detail and offers no 施放, so nothing is invented. Tab, search,
// expansion and selection are view-local UI state.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import RestForm from "./RestForm.vue";
import { targetSpecLabel } from "../lib/skill_labels.js";

const props = defineProps({
  // { actives, passives } in the character payload's category → groups →
  // {key, label, …} shape, with optional skill-descriptor detail fields.
  skills: { type: Object, required: true },
  // Showcase/mount conveniences.
  initialTab: { type: String, default: "active" },
  initialQuery: { type: String, default: "" },
  practiceDisabled: { type: Boolean, default: false },
  practiceFeedback: { type: String, default: "" },
  // The committed presentation mode ("exploration" | "combat" | "dialogue"
  // | …): it decides what the book's 施放 does, never whether a cast is legal.
  mode: { type: String, default: "exploration" },
  // True while the shared dispatch lock forbids a new request.
  useLocked: { type: Boolean, default: false },
  // The skill whose preview request is in flight (施放 → 準備中…).
  usePendingKey: { type: String, default: null },
  // The last refused 施放 `{ skillKey, message }` (server message verbatim).
  useNotice: { type: Object, default: null },
  // `{ skillKey, seq }`: reopened after leaving the dock flow — select that
  // row and focus its 施放.
  returnTarget: { type: Object, default: null },
});
const emit = defineEmits(["practice", "practice-view", "use"]);

// ---------------------------------------------------------------- practice
const practice = ref(null);
watch(practice, (value) => emit("practice-view", value !== null));
onBeforeUnmount(() => emit("practice-view", false));
const practiceSkills = computed(() => (props.skills.actives ?? []).flatMap(
  (category) => (category.groups ?? []).flatMap((group) => group.skills ?? []),
));
const practiceSkill = computed(() => practiceSkills.value.find((row) => row.key === practice.value));
function openPractice(key) {
  practice.value = key;
}
function closePractice() {
  const key = practice.value;
  practice.value = null;
  if (key) {
    nextTick(() => focusAction(key, "practice"));
  }
}

// ---------------------------------------------------------------- browsing
const ELEMENT_LOZENGE = {
  fire: "var(--seal-500)",
  water: "var(--vit-mp)",
  wind: "var(--warn)",
};

const tab = ref(props.initialTab === "passive" ? "passive" : "active");
const query = ref(props.initialQuery);
const searchEl = ref(null);
const treeEl = ref(null);

function matches(row, group, category) {
  const q = query.value.trim().toLowerCase();
  if (!q) return true;
  return [row.label, group?.label, category?.label].some(
    (label) => typeof label === "string" && label.toLowerCase().includes(q),
  );
}

function filterCategories(rows) {
  const filtered = [];
  for (const category of rows ?? []) {
    const groups = [];
    for (const group of category.groups ?? []) {
      const skills = (group.skills ?? []).filter((row) => matches(row, group, category));
      if (skills.length > 0) groups.push({ ...group, skills });
    }
    if (groups.length > 0) filtered.push({ ...category, groups });
  }
  return filtered;
}

const sourceRows = computed(() => (tab.value === "active" ? props.skills?.actives : props.skills?.passives) ?? []);
const visibleCategories = computed(() => filterCategories(sourceRows.value));
// The committed `character` panel in its common unavailable form (it is
// unavailable in combat by design): the book states the server reason and
// invents no rows.
const unavailableReason = computed(() =>
  props.skills && props.skills.available === false
    ? (props.skills.reason && props.skills.reason.message) || "技能資料目前無法顯示"
    : null,
);
const hasAny = computed(() => sourceRows.value.some((c) => (c.groups ?? []).some((g) => (g.skills ?? []).length > 0)));

function categorySkillCount(category) {
  return (category.groups ?? []).reduce((sum, group) => sum + (group.skills ?? []).length, 0);
}

function lozenge(category, group) {
  if (category === "sexual_act") return "var(--seal-500)";
  if (category === "elemental_magic" && ELEMENT_LOZENGE[group]) return ELEMENT_LOZENGE[group];
  return null;
}

// Expansion: the first category opens by default; a search shows every
// matching category; the player's own toggles win until the tab changes.
const expanded = ref(new Set());
function resetExpansion() {
  const first = visibleCategories.value[0];
  expanded.value = new Set(first ? [first.category] : []);
}
resetExpansion();
watch(tab, () => {
  resetExpansion();
  selectFirst();
});
function isOpen(category) {
  return query.value.trim() !== "" || expanded.value.has(category);
}
function toggleCategory(category, open) {
  const next = new Set(expanded.value);
  const want = open === undefined ? !next.has(category) : open;
  if (want) next.add(category);
  else next.delete(category);
  expanded.value = next;
}

// The flat, rendered tree order: headers, then (when open) their skills.
const nodes = computed(() => {
  const list = [];
  for (const category of visibleCategories.value) {
    list.push({ id: `cat:${category.category}`, type: "category", category });
    if (!isOpen(category.category)) continue;
    for (const group of category.groups ?? []) {
      for (const row of group.skills ?? []) {
        list.push({ id: `skill:${row.key}`, type: "skill", row, group, category });
      }
    }
  }
  return list;
});

// Every visible skill with its context, for selection lookups.
const visibleSkills = computed(() => {
  const list = [];
  for (const category of visibleCategories.value) {
    for (const group of category.groups ?? []) {
      for (const row of group.skills ?? []) list.push({ row, group, category });
    }
  }
  return list;
});

const selectedKey = ref(null);
const focusedId = ref(null);
function selectFirst() {
  const first = visibleSkills.value[0];
  selectedKey.value = first ? first.row.key : null;
  focusedId.value = first ? `skill:${first.row.key}` : nodes.value[0]?.id ?? null;
}
selectFirst();
watch(query, () => {
  if (!visibleSkills.value.some((entry) => entry.row.key === selectedKey.value)) {
    selectFirst();
  }
});
const selected = computed(() => visibleSkills.value.find((entry) => entry.row.key === selectedKey.value) ?? null);

// ------------------------------------------------------------ presentation
function costText(row) {
  if (!("cost" in row)) return null;
  const scales = Array.isArray(row.freeform_scales) ? row.freeform_scales : [];
  if (scales.length > 0) {
    const costs = scales.map((entry) => entry.mp_cost);
    const low = Math.min(...costs);
    const high = Math.max(...costs);
    return { prefix: "MP", value: low === high ? `${low}` : `${low}–${high}`, tone: "mp" };
  }
  const cost = row.cost ?? {};
  if (cost.sp > 0 && cost.mp > 0) return { prefix: "MP", value: `${cost.mp} ‧ SP ${cost.sp}`, tone: "sp" };
  if (cost.sp > 0) return { prefix: "SP", value: `${cost.sp}`, tone: "sp" };
  if (cost.mp > 0) return { prefix: "MP", value: `${cost.mp}`, tone: "mp" };
  return { prefix: "", value: "無消耗", tone: "free" };
}

function detailCost(row) {
  const cost = row.cost ?? {};
  const parts = [];
  if (cost.mp > 0) parts.push(`MP ${cost.mp}`);
  if (cost.sp > 0) parts.push(`SP ${cost.sp}`);
  return parts.length ? parts.join(" ‧ ") : "無消耗";
}

function targetText(row) {
  return row.target_spec ? targetSpecLabel(row.target_spec) : null;
}

const isActiveTab = computed(() => tab.value === "active");

// What 施放 does in the current mode (never a legality verdict).
const useAction = computed(() => {
  const entry = selected.value;
  if (!entry || !isActiveTab.value || typeof entry.row.usable_out_of_combat !== "boolean") {
    return null;
  }
  const row = entry.row;
  if (props.mode === "combat") {
    return { label: "改用戰鬥指令", enabled: !props.useLocked, note: "將關閉技能書，改由戰鬥指令的「技能」選擇目標。" };
  }
  if (props.mode === "dialogue") {
    return { label: "施放", enabled: false, note: "對話中無法施放。" };
  }
  if (props.mode !== "exploration") {
    return { label: "施放", enabled: false, note: "目前無法施放。" };
  }
  if (!row.usable_out_of_combat) {
    return { label: "施放", enabled: false, note: "此技能僅能在戰鬥中使用。" };
  }
  if (props.usePendingKey === row.key) {
    return { label: "準備中…", enabled: false, busy: true, note: "正在確認可選目標…" };
  }
  return { label: "施放", enabled: !props.useLocked && props.usePendingKey === null, note: null };
});

const notice = computed(() => {
  const entry = selected.value;
  return entry && props.useNotice && props.useNotice.skillKey === entry.row.key ? props.useNotice.message : null;
});

// Combat: the book's single hand-off to the combat 技能 entry, available even
// while the character panel is withheld.
function onCombatHandOff() {
  if (!props.useLocked) emit("use", selected.value ? selected.value.row.key : null);
}

function onUse() {
  const entry = selected.value;
  if (entry && useAction.value?.enabled) {
    emit("use", entry.row.key);
  }
}

// ---------------------------------------------------------------- keyboard
function nodeElement(id) {
  const all = treeEl.value ? treeEl.value.querySelectorAll("[data-node-id]") : [];
  return Array.from(all).find((el) => el.getAttribute("data-node-id") === id) ?? null;
}
function focusNode(id) {
  focusedId.value = id;
  const node = nodes.value.find((entry) => entry.id === id);
  if (node?.type === "skill") selectedKey.value = node.row.key;
  nextTick(() => nodeElement(id)?.focus({ preventScroll: false }));
}
function focusAction(key, which = "use") {
  const selector = which === "practice" ? '[data-testid="skill-book__practice"]' : '[data-testid="skill-book__use"]';
  const button = treeEl.value?.closest('[data-testid="skill-book"]')?.querySelector(selector);
  if (button && !button.disabled) {
    button.focus();
    return true;
  }
  return false;
}
function focusFirstAction() {
  nextTick(() => {
    if (!focusAction(selectedKey.value, "use")) focusAction(selectedKey.value, "practice");
  });
}

function onTreeKeydown(event) {
  const list = nodes.value;
  const index = list.findIndex((entry) => entry.id === focusedId.value);
  const node = list[index];
  if (!node) return;
  const move = (to) => {
    const target = list[Math.max(0, Math.min(list.length - 1, to))];
    if (target) focusNode(target.id);
  };
  switch (event.key) {
    case "ArrowDown": move(index + 1); break;
    case "ArrowUp": move(index - 1); break;
    case "Home": move(0); break;
    case "End": move(list.length - 1); break;
    case "PageDown": move(index + 8); break;
    case "PageUp": move(index - 8); break;
    case "ArrowRight":
      if (node.type === "category") {
        if (!isOpen(node.category.category)) toggleCategory(node.category.category, true);
        else move(index + 1);
      } else {
        focusFirstAction();
      }
      break;
    case "ArrowLeft":
      if (node.type === "category") toggleCategory(node.category.category, false);
      else focusNode(`cat:${node.category.category}`);
      break;
    case "Enter":
    case " ":
      if (node.type === "category") toggleCategory(node.category.category);
      else focusFirstAction();
      break;
    default:
      return;
  }
  event.preventDefault();
  // Inside the focus-trapped drawer the tree owns its arrows.
  event.stopPropagation();
}

function onRowClick(entry) {
  focusNode(`skill:${entry.row.key}`);
}

function onActionKeydown(event) {
  if (event.key === "ArrowLeft" && selectedKey.value) {
    event.preventDefault();
    focusNode(`skill:${selectedKey.value}`);
  }
}

function onSearchKeydown(event) {
  if (event.key === "Escape" && query.value !== "") {
    event.preventDefault();
    event.stopPropagation();
    query.value = "";
  } else if (event.key === "ArrowDown") {
    event.preventDefault();
    const first = nodes.value.find((entry) => entry.type === "skill") ?? nodes.value[0];
    if (first) focusNode(first.id);
  }
}

// `/` focuses the search from anywhere in the drawer (its close control
// holds focus when the drawer opens, outside this component's own element),
// so the shortcut listens on the enclosing drawer while the book is mounted.
const bookEl = ref(null);
let drawerEl = null;
function onBookKeydown(event) {
  if (event.key !== "/" || practice.value !== null) return;
  const target = event.target;
  if (target === searchEl.value || (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA"))) return;
  event.preventDefault();
  searchEl.value?.focus();
}
onMounted(() => {
  drawerEl = bookEl.value?.closest('[data-testid="hud-drawer"]') ?? bookEl.value?.parentElement ?? null;
  drawerEl?.addEventListener("keydown", onBookKeydown);
});
onBeforeUnmount(() => drawerEl?.removeEventListener("keydown", onBookKeydown));

function clearSearch() {
  query.value = "";
  nextTick(() => searchEl.value?.focus());
}

// Returning from the dock flow: select the row and focus its 施放 after the
// drawer's own focus trap has entered (it focuses the close control first).
function applyReturn(target) {
  if (!target || !target.skillKey) return;
  tab.value = "active";
  const entry = visibleSkills.value.find((candidate) => candidate.row.key === target.skillKey);
  if (!entry) return;
  toggleCategory(entry.category.category, true);
  selectedKey.value = entry.row.key;
  focusedId.value = `skill:${entry.row.key}`;
  setTimeout(() => {
    if (!focusAction(entry.row.key, "use")) nodeElement(`skill:${entry.row.key}`)?.focus();
  }, 0);
}
onMounted(() => applyReturn(props.returnTarget));
watch(() => props.returnTarget?.seq, () => applyReturn(props.returnTarget));
</script>

<template>
  <section
    v-if="practice !== null"
    class="practice-screen"
    data-testid="practice-screen"
    @keydown.stop
    @keydown.esc.prevent="closePractice"
  >
    <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm practice-screen__back" @click="closePractice">‹ 返回技能書</button>
    <h2>專注修煉</h2>
    <p>選擇一項已學會的主動技能，投入時間磨練熟練度。</p>
    <label>修煉技能
      <select v-model="practice" :disabled="practiceDisabled" aria-label="修煉技能">
        <option v-for="row in practiceSkills" :key="row.key" :value="row.key">{{ row.label }}</option>
      </select>
    </label>
    <p>技能達上限、戰鬥中或附近有敵人時，伺服器會拒絕修煉，不推進時間。</p>
    <p>修煉依完整小時結算；不足一小時不增加熟練度。普通休息與睡眠不增加熟練度。</p>
    <RestForm :disabled="practiceDisabled || !practiceSkill" label="開始修煉" @close="closePractice" @submit="(seconds) => emit('practice', { skill: practice, seconds })" />
    <p v-if="practiceFeedback" role="status">{{ practiceFeedback }}</p>
  </section>

  <section v-else ref="bookEl" class="skill-book" :class="{ 'skill-book--bare': unavailableReason }" data-testid="skill-book">
    <div class="skill-book__toolbar">
      <div class="ui-tabs skill-book__tabs" role="tablist" aria-label="技能種類" data-testid="skill-book__tabs">
        <button
          type="button"
          role="tab"
          class="ui-tabs__tab"
          :class="{ 'is-active': tab === 'active' }"
          :aria-selected="String(tab === 'active')"
          data-testid="skill-book__tab--active"
          @click="tab = 'active'"
        >主動</button>
        <button
          type="button"
          role="tab"
          class="ui-tabs__tab"
          :class="{ 'is-active': tab === 'passive' }"
          :aria-selected="String(tab === 'passive')"
          data-testid="skill-book__tab--passive"
          @click="tab = 'passive'"
        >被動</button>
      </div>
      <div class="skill-book__search-wrap">
        <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <circle cx="11" cy="11" r="6"></circle>
          <path d="M20 20l-4-4" stroke-linecap="round"></path>
        </svg>
        <input
          ref="searchEl"
          v-model="query"
          class="skill-book__search"
          type="search"
          aria-label="搜尋技能"
          placeholder="搜尋技能（例：火、治癒）"
          data-testid="skill-book__search"
          @keydown="onSearchKeydown"
        />
      </div>
    </div>

    <div class="skill-book__list">
      <div v-if="mode === 'combat'" class="skill-book__combat-note" data-testid="skill-book__combat-note">
        <p>戰鬥中的技能由戰鬥指令的「技能」選擇目標與施放。</p>
        <button
          type="button"
          class="ui-btn ui-btn--primary ui-btn--sm"
          data-testid="skill-book__combat-handoff"
          :disabled="useLocked"
          @click="onCombatHandOff"
        >改用戰鬥指令</button>
      </div>
      <div v-if="unavailableReason" class="skill-book__empty" role="status" data-testid="skill-book__unavailable">
        <span>{{ unavailableReason }}</span>
      </div>
      <div v-else-if="visibleCategories.length === 0" class="skill-book__empty" data-testid="skill-book__empty">
        <template v-if="hasAny">
          <span>沒有符合「{{ query.trim() }}」的技能</span>
          <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm" @click="clearSearch">清除搜尋</button>
        </template>
        <span v-else>{{ tab === 'active' ? '尚未習得主動技能' : '尚未習得被動技能' }}</span>
      </div>

      <div
        v-else
        ref="treeEl"
        class="skill-book__tree"
        role="tree"
        :aria-label="tab === 'active' ? '主動技能' : '被動技能'"
        data-testid="skill-book__tree"
        @keydown="onTreeKeydown"
      >
        <section
          v-for="category in visibleCategories"
          :key="category.category"
          class="skill-book__category"
          data-testid="skill-book__category"
          :data-category="category.category"
          :data-open="String(isOpen(category.category))"
        >
          <button
            type="button"
            role="treeitem"
            aria-level="1"
            class="skill-book__category-head"
            :aria-expanded="String(isOpen(category.category))"
            :tabindex="focusedId === `cat:${category.category}` ? 0 : -1"
            :data-node-id="`cat:${category.category}`"
            data-testid="skill-book__category-head"
            @click="toggleCategory(category.category); focusedId = `cat:${category.category}`"
          >
            <span class="skill-book__category-chevron" aria-hidden="true">▸</span>
            <span class="skill-book__category-label">{{ category.label }}</span>
            <span class="skill-book__category-rule" aria-hidden="true"></span>
            <span class="skill-book__category-count" data-testid="skill-book__category-count">{{ categorySkillCount(category) }}</span>
          </button>
          <div v-if="isOpen(category.category)" role="group" :aria-label="category.label">
            <div
              v-for="group in category.groups"
              :key="group.group ?? `${category.category}-ungrouped`"
              class="skill-book__group"
              :data-testid="`skill-book__group--${group.group ?? 'ungrouped'}`"
              :data-group="group.group ?? ''"
            >
              <p v-if="group.label" class="skill-book__group-label" data-testid="skill-book__group-label">
                <span
                  v-if="lozenge(category.category, group.group)"
                  class="skill-book__lozenge"
                  data-testid="skill-book__group-dot"
                  aria-hidden="true"
                  :style="{ background: lozenge(category.category, group.group) }"
                ></span>
                {{ group.label }}
              </p>
              <div
                v-for="row in group.skills"
                :key="row.key"
                role="treeitem"
                aria-level="2"
                class="skill-book__skill"
                :class="{ 'is-selected': row.key === selectedKey }"
                :aria-selected="String(row.key === selectedKey)"
                :tabindex="focusedId === `skill:${row.key}` ? 0 : -1"
                :data-node-id="`skill:${row.key}`"
                data-testid="skill-book__skill"
                :data-key="row.key"
                @click="onRowClick({ row, group, category })"
                @dblclick="focusFirstAction"
              >
                <span class="skill-book__caret" aria-hidden="true">▸</span>
                <span class="skill-book__skill-name">{{ row.label }}</span>
                <span v-if="targetText(row)" class="skill-book__target" data-testid="skill-book__target">{{ targetText(row) }}</span>
                <span v-else></span>
                <span class="skill-book__field-cell">
                  <span
                    v-if="isActiveTab && row.usable_out_of_combat === true"
                    class="status-marker status-marker--ok skill-book__field"
                    data-testid="skill-book__field"
                  >戰鬥外可用</span>
                </span>
                <span
                  v-if="isActiveTab && costText(row)"
                  class="skill-book__cost"
                  :class="costText(row).tone"
                  data-testid="skill-book__cost"
                ><small v-if="costText(row).prefix">{{ costText(row).prefix }}</small>{{ costText(row).value }}</span>
                <span v-else-if="!isActiveTab" class="skill-book__passive-badge" data-testid="skill-book__passive-badge">被動</span>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <aside
      v-if="!unavailableReason"
      class="skill-book__detail"
      data-testid="skill-book__detail"
      aria-label="技能詳情"
    >
      <template v-if="selected">
        <p class="skill-book__eyebrow">
          {{ isActiveTab ? selected.category.label : '被動技能' }}<template v-if="isActiveTab && selected.group.label"> ‧ {{ selected.group.label }}</template>
        </p>
        <h3 class="skill-book__title" aria-live="polite" data-testid="skill-book__detail-title">{{ selected.row.label }}</h3>

        <template v-if="isActiveTab">
          <dl v-if="selected.row.target_spec || 'cost' in selected.row" class="skill-book__facts">
            <template v-if="selected.row.target_spec">
              <dt>目標</dt><dd>{{ targetText(selected.row) }}</dd>
            </template>
            <template v-if="'cost' in selected.row">
              <dt>消耗</dt><dd>{{ detailCost(selected.row) }}<span v-if="selected.row.freeform_scales?.length" class="skill-book__muted">（威力 ×1）</span></dd>
            </template>
          </dl>

          <table v-if="selected.row.freeform_scales?.length" class="skill-book__scales" data-testid="skill-book__scales">
            <caption>威力與消耗</caption>
            <thead>
              <tr><th v-for="entry in selected.row.freeform_scales" :key="entry.scale" scope="col" :class="{ 'is-standard': entry.scale === 1 }">×{{ entry.label }}</th></tr>
            </thead>
            <tbody>
              <tr><td v-for="entry in selected.row.freeform_scales" :key="entry.scale" :class="{ 'is-standard': entry.scale === 1 }">MP {{ entry.mp_cost }}</td></tr>
            </tbody>
          </table>

          <div v-if="typeof selected.row.usable_out_of_combat === 'boolean'" class="skill-book__capability" data-testid="skill-book__capability">
            <template v-if="selected.row.usable_out_of_combat">
              <span class="status-marker status-marker--ok">可於戰鬥外使用</span>
              <p v-if="selected.row.target_spec === 'single' || selected.row.target_spec === 'area'">對同場魔物施放將直接開戰。</p>
            </template>
            <span v-else class="status-marker">僅能在戰鬥中使用</span>
            <p class="skill-book__note">實際能否施放與可選目標，於施放時依當下狀態判定。</p>
          </div>

          <div class="skill-book__actions">
            <button
              v-if="useAction"
              type="button"
              class="ui-btn ui-btn--primary skill-book__use"
              data-testid="skill-book__use"
              :disabled="!useAction.enabled"
              :aria-busy="useAction.busy ? 'true' : undefined"
              :aria-label="`${useAction.label}${selected.row.label}`"
              @click="onUse"
              @keydown="onActionKeydown"
            >{{ useAction.label }}</button>
            <button
              type="button"
              class="ui-btn skill-book__practice"
              data-testid="skill-book__practice"
              :disabled="practiceDisabled"
              :aria-label="`修煉${selected.row.label}`"
              @click="openPractice(selected.row.key)"
              @keydown="onActionKeydown"
            >修煉</button>
          </div>
          <p v-if="notice" class="skill-book__alert" role="alert" data-testid="skill-book__notice">無法施放：{{ notice }}</p>
          <p v-else-if="useAction?.note" class="skill-book__status" role="status" data-testid="skill-book__use-note">{{ useAction.note }}</p>
        </template>
        <p v-else class="skill-book__capability skill-book__note" data-testid="skill-book__passive-note">常駐生效，不需施放。</p>
      </template>
      <p v-else class="skill-book__note">選擇左側的技能以查看詳情。</p>
    </aside>
  </section>
</template>

<style scoped>
.skill-book {
  display: grid;
  grid-template-columns: minmax(0, 1fr) clamp(calc(392px * var(--ui-scale)), 28%, calc(480px * var(--ui-scale)));
  grid-template-rows: auto minmax(0, 1fr);
  column-gap: var(--sp-6);
  row-gap: var(--sp-4);
  justify-content: space-between;
  min-width: 0;
  min-height: 100%;
  box-sizing: border-box;
  font-family: var(--f-sans);
}

/* No committed rows (the panel's unavailable form): no detail card. */
.skill-book--bare {
  grid-template-columns: minmax(0, 1fr);
}

/* ---- toolbar ---- */
.skill-book__toolbar {
  grid-column: 1;
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  min-width: 0;
}
.skill-book__tabs {
  flex: none;
  align-self: center;
}
.skill-book__search-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: calc(9px * var(--ui-scale));
  min-height: calc(36px * var(--ui-scale));
  padding: 0 calc(12px * var(--ui-scale));
  background: var(--ink-820);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius);
  box-sizing: border-box;
}
.skill-book__search-wrap svg {
  flex: none;
  width: calc(16px * var(--ui-scale));
  height: calc(16px * var(--ui-scale));
  color: var(--paper-500);
}
.skill-book__search-wrap:focus-within {
  border-color: var(--gold-500);
  box-shadow: var(--focus);
}
.skill-book__search {
  flex: 1;
  min-width: 0;
  color: var(--paper-50);
  background: transparent;
  border: 0;
  outline: none;
  font-size: var(--text-sm);
  font-family: var(--f-sans);
}
.skill-book__search:focus-visible {
  box-shadow: none;
}

/* ---- list ---- */
.skill-book__list {
  grid-column: 1;
  min-width: 0;
}
.skill-book__empty {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  padding: var(--sp-4);
  color: var(--paper-500);
  font-size: var(--text-sm);
  border: 1px dashed var(--ink-600);
  border-radius: var(--radius);
}
.skill-book__combat-note {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  margin-bottom: var(--sp-3);
  padding: var(--sp-3) var(--sp-4);
  border: 1px solid rgba(185, 154, 96, 0.32);
  border-radius: var(--radius);
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.12), transparent);
}
.skill-book__combat-note p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--paper-200);
}
.skill-book__category + .skill-book__category {
  margin-top: var(--sp-4);
}
.skill-book__category-head {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  width: 100%;
  min-height: calc(36px * var(--ui-scale));
  padding: 0 var(--sp-2);
  color: var(--gold-400);
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-align: left;
}
.skill-book__category-head:hover {
  background: rgba(255, 255, 255, 0.03);
}
.skill-book__category-chevron {
  flex: none;
  width: calc(14px * var(--ui-scale));
  color: var(--paper-500);
  font-size: var(--text-xs);
  transition: transform var(--motion-fast) var(--ease-standard);
}
.skill-book__category-head[aria-expanded="true"] .skill-book__category-chevron {
  transform: rotate(90deg);
  color: var(--gold-400);
}
.skill-book__category-label {
  flex: none;
  font-family: var(--f-serif);
  font-size: var(--text-md);
  letter-spacing: 0.12em;
}
.skill-book__category-rule {
  flex: 1;
  height: 1px;
  min-width: var(--sp-4);
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.42), transparent);
}
.skill-book__category-count {
  flex: none;
  font-family: var(--f-num);
  font-size: var(--text-xs);
  color: var(--paper-500);
  font-variant-numeric: tabular-nums lining-nums;
}

.skill-book__group-label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: var(--sp-3) 0 var(--sp-1) calc(24px * var(--ui-scale));
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  color: var(--paper-400);
}
.skill-book__lozenge {
  flex: none;
  width: calc(6px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  transform: rotate(45deg);
}

.skill-book__skill {
  display: grid;
  grid-template-columns:
    calc(18px * var(--ui-scale))
    minmax(8em, 1fr)
    calc(96px * var(--ui-scale))
    calc(132px * var(--ui-scale))
    calc(110px * var(--ui-scale));
  align-items: center;
  column-gap: var(--sp-2);
  min-height: calc(36px * var(--ui-scale));
  margin-top: 1px;
  padding: 2px var(--sp-3) 2px var(--sp-2);
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}
.skill-book__skill:hover {
  background: rgba(255, 255, 255, 0.03);
}
.skill-book__skill.is-selected {
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.24), rgba(185, 154, 96, 0.05));
  border-color: rgba(185, 154, 96, 0.42);
}
.skill-book__caret {
  color: transparent;
  font-size: var(--text-xs);
}
.skill-book__skill.is-selected .skill-book__caret {
  color: var(--gold-400);
}
.skill-book__skill-name {
  min-width: 0;
  font-family: var(--f-serif);
  font-size: var(--text-md);
  letter-spacing: 0.04em;
  color: var(--paper-200);
  overflow-wrap: anywhere;
}
.skill-book__skill.is-selected .skill-book__skill-name {
  color: var(--paper-50);
}
.skill-book__target {
  font-size: var(--text-xs);
  color: var(--paper-500);
  white-space: nowrap;
}
.skill-book__field-cell {
  min-width: 0;
}
.skill-book__field {
  font-size: var(--text-xs);
  white-space: nowrap;
}
.skill-book__cost {
  justify-self: end;
  font-family: var(--f-num);
  font-size: var(--text-sm);
  white-space: nowrap;
  font-variant-numeric: tabular-nums lining-nums;
}
.skill-book__cost small {
  margin-right: 0.3em;
  font-size: var(--text-xs);
  opacity: 0.85;
}
.skill-book__cost.mp {
  color: var(--vit-mp);
}
.skill-book__cost.sp {
  color: var(--vit-sp);
}
.skill-book__cost.free {
  color: var(--paper-500);
}
.skill-book__passive-badge {
  justify-self: end;
  font-size: var(--text-xs);
  color: var(--paper-500);
}

/* ---- detail card ---- */
.skill-book__detail {
  grid-column: 2;
  grid-row: 1 / -1;
  align-self: start;
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
  min-height: calc(360px * var(--ui-scale));
  max-height: 100%;
  padding: var(--sp-5) var(--sp-6);
  box-sizing: border-box;
  background: linear-gradient(180deg, rgba(24, 25, 29, 0.78), rgba(12, 13, 16, 0.55));
  border: 1px solid rgba(185, 154, 96, 0.22);
  border-radius: var(--radius);
}
.skill-book__eyebrow {
  margin: 0;
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
  color: var(--paper-500);
}
.skill-book__title {
  position: relative;
  margin: calc(-1 * var(--sp-2)) 0 0;
  padding-bottom: var(--sp-3);
  font-family: var(--f-serif);
  font-size: var(--text-2xl);
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--paper-50);
  overflow-wrap: anywhere;
}
.skill-book__title::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  width: calc(40px * var(--ui-scale));
  height: 2px;
  background: var(--gold-500);
}
.skill-book__facts {
  display: grid;
  grid-template-columns: 5em 1fr;
  row-gap: var(--sp-2);
  margin: 0;
}
.skill-book__facts dt {
  font-size: var(--text-xs);
  color: var(--paper-500);
  align-self: center;
}
.skill-book__facts dd {
  margin: 0;
  font-size: var(--text-md);
  color: var(--paper-100);
}
.skill-book__muted {
  font-size: var(--text-xs);
  color: var(--paper-500);
}
.skill-book__scales {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums lining-nums;
}
.skill-book__scales caption {
  caption-side: top;
  text-align: left;
  padding-bottom: var(--sp-1);
  font-size: var(--text-xs);
  color: var(--paper-500);
}
.skill-book__scales th,
.skill-book__scales td {
  padding: var(--sp-1) 0;
  text-align: center;
  font-size: var(--text-xs);
  color: var(--paper-300);
}
.skill-book__scales th {
  font-weight: 500;
  border-bottom: var(--line);
}
.skill-book__scales .is-standard {
  color: var(--gold-400);
}
.skill-book__capability {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: var(--sp-2);
}
.skill-book__capability p {
  margin: 0;
  font-size: var(--text-sm);
  line-height: 1.6;
  color: var(--paper-300);
}
.skill-book__capability .skill-book__note,
.skill-book__note {
  margin: 0;
  font-size: var(--text-xs);
  line-height: 1.6;
  color: var(--paper-500);
}
.skill-book__actions {
  display: flex;
  gap: var(--sp-3);
  margin-top: auto;
  padding-top: var(--sp-4);
  border-top: var(--line);
}
.skill-book__use {
  min-width: 7em;
}
.skill-book__status {
  margin: calc(-1 * var(--sp-2)) 0 0;
  font-size: var(--text-xs);
  color: var(--paper-500);
}
.skill-book__alert {
  margin: calc(-1 * var(--sp-2)) 0 0;
  font-size: var(--text-sm);
  color: var(--seal-400);
}
.skill-book__alert::before {
  content: "✕ ";
}
</style>
