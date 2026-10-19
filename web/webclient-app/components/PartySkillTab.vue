<script setup>
// PartySkillTab (webclient-party-skill-tab, design §6.4): the party window's
// 技能 tab for the viewed member, after the approved prototype
// docs/design/party-member-management/tabs/SkillTab.vue. It replaces the
// retired SkillBook drawer and keeps its browsing: the 主動/被動 segment
// (each with its count), the bounded search, and the keyboard category tree
// in the payload's own category → group → skill order. Each active row adds
// the member's proficiency meter and level (見頂 when capped), a 新 tag for a
// skill in the session's recent-unlock set and a 修煉中 tag while its
// practice is booked. The detail column shows the target, cost and field
// capability, the 威力與消耗 ladder and the lineage position (prerequisite →
// skill → next unlock, linking into the 系譜 tab) from the committed
// `selected_skill` only while it names the row on screen, and the action bar
// offers 施放 (the viewed member casts through the existing server preview
// and the dock's target flow) and 排入修煉 (one standing booking for that
// member). In combat both are disabled with their committed reasons; combat
// casting stays on the command card.
//
// Selection rides `party.view_member` (tab `skills`): `requestSkill` returns
// the admitted request id or null, so a refused request (the shared dispatch
// lock) is retried when the lock opens instead of being lost. Opening the
// tab sends one selection when the member is unread or the committed
// selection differs, which clears the rail's unread dot; 新 tags stay for the
// session. Nothing here decides availability: the capability line restates
// the static `usable_out_of_combat` flag, and whether a cast is possible now,
// and at whom, is the server preview's answer once 施放 is pressed.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import ActionBar from "./ActionBar.vue";
import ListDetail from "./ListDetail.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { targetSpecLabel } from "../lib/skill_labels.js";
import { panelReason } from "./party-window-model.js";
import {
  COMBAT_ONLY_TEXT,
  FIELD_CAPABLE_TEXT,
  castAction,
  costOf,
  filterCategories,
  flattenSkills,
  groupDot,
  growthOf,
  hasDescriptor,
  ladderOf,
  lineageOf,
  practiceAction,
  selectedSectionFor,
  skillCount,
} from "./party-skill-model.js";

const props = defineProps({
  // The selected committed `party` v3 row (the viewed member).
  member: { type: Object, default: null },
  // The committed `character` v9 panel for the viewed member.
  character: { type: Object, default: null },
  // True in combat: 施放 and 排入修煉 are disabled with their reasons.
  combat: { type: Boolean, default: false },
  // The committed presentation mode; it decides what 施放 offers, never
  // whether a cast is legal.
  mode: { type: String, default: "exploration" },
  // The shared booking lock (the time-skip lock) and the server's booking line.
  practiceDisabled: { type: Boolean, default: false },
  practiceFeedback: { type: String, default: "" },
  // True while the shared dispatch lock forbids a new request.
  useLocked: { type: Boolean, default: false },
  // `{ actorId, skillKey }` whose preview request is in flight, or null.
  usePending: { type: Object, default: null },
  // The last refused 施放 `{ actorId, skillKey, message }` (server message).
  useNotice: { type: Object, default: null },
  // `{ actorId, skillKey, seq }`: reopened after leaving the dock flow.
  returnTarget: { type: Object, default: null },
  // `({ member_id, skill_key }) => requestId | null`: one `party.view_member`.
  requestSkill: { type: Function, default: null },
  // Story seams: the segment and the skill selected on open.
  initialSegment: { type: String, default: "active" },
  initialSkill: { type: String, default: null },
});

const emit = defineEmits(["practice", "use", "lineage"]);

// Element ids: each category treeitem owns its group of skill rows.
const uid = useId();
const groupId = (category) => `party-skill-tab-${uid}-group-${category}`;

// ---------------------------------------------------------------- data

const characterReason = computed(() => panelReason(props.character));
// The payload renders only for the member it describes (as on 狀態).
const detail = computed(() => {
  const panel = props.character;
  if (!props.member || !panel || panel.available !== true) return null;
  return panel.member_id === props.member.identity ? panel : null;
});
const memberId = computed(() => {
  const id = detail.value?.member_id;
  return Number.isSafeInteger(id) && id > 0 ? id : null;
});

const segment = ref(props.initialSegment === "passive" ? "passive" : "active");
const isActive = computed(() => segment.value === "active");
const query = ref("");
const activeCount = computed(() => skillCount(detail.value?.actives));
const passiveCount = computed(() => skillCount(detail.value?.passives));

const sourceRows = computed(() => (isActive.value ? detail.value?.actives : detail.value?.passives) ?? []);
const visibleCategories = computed(() => filterCategories(sourceRows.value, query.value));
const visibleSkills = computed(() => flattenSkills(visibleCategories.value));
const hasAny = computed(() => skillCount(sourceRows.value) > 0);
const searching = computed(() => query.value.trim() !== "");

// ---------------------------------------------------------------- tree

// Every category opens on a selection reset; a search shows every match;
// the player's own toggles win until the segment or the member changes.
const expanded = ref(new Set());
function isOpen(category) {
  return searching.value || expanded.value.has(category);
}
function toggleCategory(category, open) {
  const next = new Set(expanded.value);
  const want = open === undefined ? !next.has(category) : open;
  if (want) next.add(category);
  else next.delete(category);
  expanded.value = next;
}

const nodes = computed(() => {
  const list = [];
  for (const category of visibleCategories.value) {
    list.push({ id: `cat:${category.category}`, type: "category", category });
    if (!isOpen(category.category)) continue;
    for (const group of category.groups) {
      for (const row of group.skills) list.push({ id: `skill:${row.key}`, type: "skill", row, group, category });
    }
  }
  return list;
});

const selectedKey = ref(null);
const focusedId = ref(null);

function entryFor(key) {
  return visibleSkills.value.find((entry) => entry.row.key === key) ?? null;
}

// Selection on open, on a segment change and on a member change: the
// committed selection when it is on screen, else the story's initial skill,
// else the first visible row.
function reselect(preferInitial) {
  const committed = isActive.value ? detail.value?.selected_skill?.key : null;
  const wanted = [committed, preferInitial ? props.initialSkill : null].find((key) => key && entryFor(key));
  const entry = wanted ? entryFor(wanted) : (visibleSkills.value[0] ?? null);
  // Every category opens (the approved prototype lists every group); the
  // player's own collapses hold until the segment or the member changes.
  expanded.value = new Set(visibleCategories.value.map((category) => category.category));
  selectedKey.value = entry ? entry.row.key : null;
  focusedId.value = entry ? `skill:${entry.row.key}` : (nodes.value[0]?.id ?? null);
}
reselect(true);
// The selected row is scrolled into the list column's view on open, so a
// committed selection deep in the tree is never hidden below the fold.
function revealSelected() {
  nextTick(() => {
    const el = selectedKey.value ? nodeElement(`skill:${selectedKey.value}`) : null;
    if (el && typeof el.scrollIntoView === "function") el.scrollIntoView({ block: "nearest" });
  });
}
onMounted(revealSelected);
watch(memberId, () => {
  query.value = "";
  reselect(false);
});
watch(segment, () => reselect(false));
watch(query, () => {
  if (!entryFor(selectedKey.value)) {
    const first = visibleSkills.value[0] ?? null;
    selectedKey.value = first ? first.row.key : null;
    focusedId.value = first ? `skill:${first.row.key}` : (nodes.value[0]?.id ?? null);
  }
});
// A republished payload that drops the selected row falls back to the
// first visible row; the player's collapses hold.
watch(visibleSkills, () => {
  if (selectedKey.value !== null && !entryFor(selectedKey.value)) {
    const first = visibleSkills.value[0] ?? null;
    selectedKey.value = first ? first.row.key : null;
    focusedId.value = first ? `skill:${first.row.key}` : (nodes.value[0]?.id ?? null);
  }
});

const selected = computed(() => entryFor(selectedKey.value));

// ---------------------------------------------------------------- selection sync

// The key the server should hold: the selected registered active row (an
// unregistered row would only be answered with null).
const desiredKey = computed(() => {
  const entry = selected.value;
  return isActive.value && entry && hasDescriptor(entry.row) ? entry.row.key : null;
});
const committedKey = computed(() => detail.value?.selected_skill?.key ?? null);
// Opening the tab owes one selection while the member is unread or the
// committed selection differs; afterwards a selection is sent only when the
// wanted key differs. One admitted request per (member, key): a server that
// answers null for it is not asked again.
const openPending = ref(true);
let requested = null;
function syncSelection() {
  if (!props.requestSkill || memberId.value === null || props.useLocked) return;
  const want = desiredKey.value;
  const opening = openPending.value;
  const needed = opening ? want !== committedKey.value || props.member?.unread === true : want !== null && want !== committedKey.value;
  if (!needed) {
    openPending.value = false;
    return;
  }
  if (!opening && requested && requested.memberId === memberId.value && requested.key === want) return;
  const requestId = props.requestSkill({ member_id: memberId.value, skill_key: want });
  if (requestId === null || requestId === undefined) return; // refused: retried when the lock opens
  requested = { memberId: memberId.value, key: want };
  openPending.value = false;
}
watch(memberId, () => {
  requested = null;
});
watch([memberId, desiredKey, committedKey, () => props.useLocked, () => props.member?.unread], syncSelection, {
  flush: "post",
  immediate: true,
});

// ---------------------------------------------------------------- detail

const section = computed(() => (selected.value && isActive.value ? selectedSectionFor(detail.value, selected.value.row.key) : null));
const ladder = computed(() => ladderOf(section.value));
const lineage = computed(() => lineageOf(section.value));
const growth = computed(() => (selected.value && isActive.value ? growthOf(selected.value.row) : null));
const cost = computed(() => (selected.value ? costOf(selected.value.row) : null));
const eyebrow = computed(() => {
  const entry = selected.value;
  if (!entry) return "";
  return entry.group?.label ? `${entry.category.label} ‧ ${entry.group.label}` : entry.category.label;
});

function rowGrowth(row) {
  return isActive.value ? growthOf(row) : null;
}

// ---------------------------------------------------------------- actions

const pendingHere = computed(() => {
  const pending = props.usePending;
  const entry = selected.value;
  return !!pending && !!entry && pending.skillKey === entry.row.key && (pending.actorId == null || pending.actorId === memberId.value);
});
const notice = computed(() => {
  const value = props.useNotice;
  const entry = selected.value;
  if (!value || !entry || value.skillKey !== entry.row.key) return null;
  return value.actorId == null || value.actorId === memberId.value ? value.message : null;
});

const actions = computed(() => {
  const entry = selected.value;
  if (!entry || !detail.value) return [];
  const practice = practiceAction({
    row: entry.row,
    active: isActive.value,
    combat: props.combat,
    disabled: props.practiceDisabled,
    memberId: memberId.value,
  });
  const cast = castAction({
    row: entry.row,
    active: isActive.value,
    mode: props.mode,
    combat: props.combat,
    locked: props.useLocked || (props.usePending !== null && !pendingHere.value),
    pending: pendingHere.value,
  });
  return [practice, cast].filter(Boolean);
});

function onAction(key) {
  const entry = selected.value;
  if (!entry) return;
  if (key === "practice" && memberId.value !== null) {
    emit("practice", { actor_id: memberId.value, skill: entry.row.key });
  } else if (key === "cast") {
    emit("use", entry.row.key);
  }
}

// ---------------------------------------------------------------- keyboard

const root = ref(null);
const treeEl = ref(null);
const searchEl = ref(null);

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
function actionButton(key) {
  return root.value?.querySelector(`[data-testid="action-bar__btn--${key}"]`) ?? null;
}
function focusAction(keys) {
  for (const key of keys) {
    const button = actionButton(key);
    if (button && button.getAttribute("aria-disabled") !== "true") {
      button.focus();
      return true;
    }
  }
  return false;
}
function focusFirstAction() {
  nextTick(() => focusAction(["cast", "practice"]));
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
  // Inside the focus-trapped window the tree owns its arrows.
  event.stopPropagation();
}

// ← from an action bar button returns to the selected row.
function onDetailKeydown(event) {
  if (event.key !== "ArrowLeft" || !selectedKey.value) return;
  const target = event.target;
  if (!target?.closest?.('[data-testid="action-bar"]')) return;
  event.preventDefault();
  focusNode(`skill:${selectedKey.value}`);
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

function clearSearch() {
  query.value = "";
  nextTick(() => searchEl.value?.focus());
}

// `/` focuses the search from anywhere in the window (its close control
// holds focus when the window opens, outside this tab's element).
let windowEl = null;
function onWindowKeydown(event) {
  if (event.key !== "/") return;
  const target = event.target;
  if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA")) return;
  event.preventDefault();
  searchEl.value?.focus();
}
onMounted(() => {
  windowEl = root.value?.closest('[data-testid="hud-drawer"]') ?? root.value?.parentElement ?? null;
  windowEl?.addEventListener("keydown", onWindowKeydown);
});
onBeforeUnmount(() => windowEl?.removeEventListener("keydown", onWindowKeydown));

// Returning from the dock flow: select the invoking skill and focus its
// 施放 once the window's own focus trap has entered (it focuses the close
// control first). Only for the member who cast.
function applyReturn(target) {
  if (!target || !target.skillKey) return;
  if (target.actorId != null && target.actorId !== memberId.value) return;
  segment.value = "active";
  query.value = "";
  nextTick(() => {
    const entry = entryFor(target.skillKey);
    if (!entry) return;
    toggleCategory(entry.category.category, true);
    selectedKey.value = entry.row.key;
    focusedId.value = `skill:${entry.row.key}`;
    setTimeout(() => {
      if (!focusAction(["cast"])) nodeElement(`skill:${entry.row.key}`)?.focus();
    }, 0);
  });
}
onMounted(() => applyReturn(props.returnTarget));
watch(() => props.returnTarget?.seq, () => applyReturn(props.returnTarget));

const glyph = (name) => ({ d: glyphPath(name), attrs: glyphAttrs(name) });
</script>

<template>
  <div ref="root" class="party-skill-tab" data-testid="party-skill-tab" :data-member="member ? member.identity : undefined">
    <ListDetail list-label="技能" detail-label="技能詳情">
      <template #rail><slot name="rail" /></template>

      <template #list>
        <p
          v-if="characterReason"
          class="party-skill-tab__reason"
          role="status"
          data-testid="party-window__tab-unavailable"
          :data-reason-code="characterReason.code || undefined"
        >{{ characterReason.message }}</p>

        <template v-else-if="detail">
          <div class="party-skill-tab__seg" role="group" aria-label="技能種類" data-testid="party-skill-tab__segment">
            <button
              type="button"
              :aria-pressed="isActive ? 'true' : 'false'"
              :class="{ 'is-active': isActive }"
              data-testid="party-skill-tab__segment--active"
              @click="segment = 'active'"
            >主動 <b>{{ activeCount }}</b></button>
            <button
              type="button"
              :aria-pressed="!isActive ? 'true' : 'false'"
              :class="{ 'is-active': !isActive }"
              data-testid="party-skill-tab__segment--passive"
              @click="segment = 'passive'"
            >被動 <b>{{ passiveCount }}</b></button>
          </div>

          <label class="party-skill-tab__search">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="glyph('look').d" stroke="currentColor" stroke-width="1.6" v-bind="glyph('look').attrs" /></svg>
            <input
              ref="searchEl"
              v-model="query"
              type="search"
              placeholder="搜尋技能"
              aria-label="搜尋技能"
              data-testid="party-skill-tab__search"
              @keydown="onSearchKeydown"
            />
            <kbd aria-hidden="true">/</kbd>
          </label>

          <div v-if="visibleCategories.length === 0" class="party-skill-tab__empty" data-testid="party-skill-tab__empty">
            <template v-if="hasAny">
              <span>沒有符合「{{ query.trim() }}」的技能</span>
              <button type="button" class="party-skill-tab__clear" @click="clearSearch">清除搜尋</button>
            </template>
            <span v-else>{{ isActive ? "尚未習得主動技能" : "尚未習得被動技能" }}</span>
          </div>

          <div
            v-else
            ref="treeEl"
            class="party-skill-tab__tree"
            role="tree"
            :aria-label="isActive ? '主動技能' : '被動技能'"
            data-testid="party-skill-tab__tree"
            @keydown="onTreeKeydown"
          >
            <section
              v-for="category in visibleCategories"
              :key="category.category"
              role="none"
              class="party-skill-tab__category"
              data-testid="party-skill-tab__category"
              :data-category="category.category"
              :data-open="String(isOpen(category.category))"
            >
              <button
                type="button"
                role="treeitem"
                aria-level="1"
                class="party-skill-tab__sech"
                :aria-expanded="String(isOpen(category.category))"
                :aria-owns="isOpen(category.category) ? groupId(category.category) : undefined"
                :tabindex="focusedId === `cat:${category.category}` ? 0 : -1"
                :data-node-id="`cat:${category.category}`"
                data-testid="party-skill-tab__category-head"
                @click="toggleCategory(category.category); focusedId = `cat:${category.category}`"
              >
                <span class="party-skill-tab__chevron" aria-hidden="true">▸</span>
                <span class="party-skill-tab__sech-label">{{ category.label }}</span>
                <span class="party-skill-tab__sech-rule" aria-hidden="true"></span>
                <span class="party-skill-tab__sech-count" data-testid="party-skill-tab__category-count">{{ category.groups.reduce((n, g) => n + g.skills.length, 0) }}</span>
              </button>
              <div v-if="isOpen(category.category)" :id="groupId(category.category)" role="group" :aria-label="category.label">
                <div
                  v-for="group in category.groups"
                  :key="group.group ?? `${category.category}-ungrouped`"
                  role="none"
                  class="party-skill-tab__group"
                  :class="{ 'party-skill-tab__group--bare': !group.label }"
                  :data-group="group.group ?? ''"
                >
                  <p v-if="group.label" role="none" class="party-skill-tab__group-label" data-testid="party-skill-tab__group-label">
                    <span
                      v-if="groupDot(category.category, group.group)"
                      class="party-skill-tab__dot"
                      data-testid="party-skill-tab__group-dot"
                      aria-hidden="true"
                      :style="{ background: groupDot(category.category, group.group) }"
                    ></span>{{ group.label }}
                  </p>
                  <div
                    v-for="row in group.skills"
                    :key="row.key"
                    role="treeitem"
                    aria-level="2"
                    class="party-skill-tab__row"
                    :class="{ 'is-selected': row.key === selectedKey }"
                    :aria-selected="String(row.key === selectedKey)"
                    :tabindex="focusedId === `skill:${row.key}` ? 0 : -1"
                    :data-node-id="`skill:${row.key}`"
                    data-testid="party-skill-tab__row"
                    :data-key="row.key"
                    @click="focusNode(`skill:${row.key}`)"
                    @dblclick="focusFirstAction"
                  >
                    <span class="party-skill-tab__icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" fill="none"><path :d="glyph(isActive ? 'skills' : 'buff').d" stroke="currentColor" stroke-width="1.5" v-bind="glyph(isActive ? 'skills' : 'buff').attrs" /></svg>
                    </span>
                    <span class="party-skill-tab__row-main">
                      <span class="party-skill-tab__row-name">
                        <span class="party-skill-tab__row-label">{{ row.label }}</span>
                        <span v-if="isActive && row.fresh" class="party-skill-tab__tag party-skill-tab__tag--new" data-testid="party-skill-tab__new">新</span>
                        <span v-if="isActive && row.booked" class="party-skill-tab__tag" data-testid="party-skill-tab__booked">修煉中</span>
                      </span>
                      <span
                        v-if="rowGrowth(row)"
                        class="party-skill-tab__meter"
                        :class="{ 'is-capped': rowGrowth(row).capped }"
                        aria-hidden="true"
                        data-testid="party-skill-tab__meter"
                      ><i :style="{ width: `${rowGrowth(row).percent}%` }"></i></span>
                    </span>
                    <span v-if="rowGrowth(row)" class="party-skill-tab__row-end" :class="{ 'is-capped': rowGrowth(row).capped }" data-testid="party-skill-tab__level">{{ rowGrowth(row).levelText }}</span>
                    <span v-else-if="!isActive" class="party-skill-tab__badge" data-testid="party-skill-tab__passive-badge">被動</span>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </template>
      </template>

      <template #detail>
        <div v-if="detail && selected" class="party-skill-tab__detail" data-testid="party-skill-tab__detail" @keydown="onDetailKeydown">
          <span class="party-skill-tab__ribbon" data-testid="party-skill-tab__ribbon">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="glyph(isActive ? 'skills' : 'buff').d" stroke="currentColor" stroke-width="1.6" v-bind="glyph(isActive ? 'skills' : 'buff').attrs" /></svg>{{ isActive ? "主動" : "被動" }}
          </span>
          <h3 class="party-skill-tab__title" aria-live="polite" data-testid="party-skill-tab__title">{{ selected.row.label }}</h3>
          <p class="party-skill-tab__eyebrow" data-testid="party-skill-tab__eyebrow">{{ eyebrow }}</p>

          <template v-if="isActive">
            <dl v-if="'target_spec' in selected.row || cost || typeof selected.row.usable_out_of_combat === 'boolean'" class="party-skill-tab__facts" data-testid="party-skill-tab__facts">
              <div v-if="selected.row.target_spec" class="party-skill-tab__fact">
                <dt>目標</dt><dd data-testid="party-skill-tab__fact--target">{{ targetSpecLabel(selected.row.target_spec) }}</dd>
              </div>
              <div v-if="cost" class="party-skill-tab__fact">
                <dt>消耗</dt><dd :class="`is-${cost.tone}`" data-testid="party-skill-tab__fact--cost">{{ cost.text }}<small v-if="ladder.length">（威力 ×1）</small></dd>
              </div>
              <div v-if="typeof selected.row.usable_out_of_combat === 'boolean'" class="party-skill-tab__fact">
                <dt>戰鬥外</dt>
                <dd :class="selected.row.usable_out_of_combat ? 'is-field' : 'is-combat-only'" data-testid="party-skill-tab__fact--field">{{ selected.row.usable_out_of_combat ? FIELD_CAPABLE_TEXT : COMBAT_ONLY_TEXT }}</dd>
              </div>
            </dl>

            <template v-if="ladder.length">
              <h4 class="party-skill-tab__label">威力與消耗</h4>
              <ol class="party-skill-tab__scales" aria-label="威力與消耗" data-testid="party-skill-tab__scales">
                <li
                  v-for="rung in ladder"
                  :key="rung.scale"
                  :class="{ 'is-locked': rung.locked, 'is-standard': rung.standard }"
                  :data-locked="String(rung.locked)"
                  data-testid="party-skill-tab__rung"
                >
                  <b>威力×{{ rung.label }}</b>
                  <span>
                    <svg v-if="rung.locked" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="glyph('lock').d" stroke="currentColor" stroke-width="1.6" v-bind="glyph('lock').attrs" /></svg>{{ rung.valueText }}
                  </span>
                </li>
              </ol>
            </template>

            <template v-if="growth">
              <h4 class="party-skill-tab__label">熟練度</h4>
              <div class="party-skill-tab__prog" :class="{ 'is-capped': growth.capped }" data-testid="party-skill-tab__proficiency">
                <span class="party-skill-tab__prog-level">{{ growth.levelText }}</span>
                <span class="party-skill-tab__track" aria-hidden="true"><i :style="{ width: `${growth.percent}%` }"></i></span>
                <span class="party-skill-tab__prog-xp">{{ growth.xpText }}</span>
              </div>
            </template>

            <template v-if="lineage">
              <h4 class="party-skill-tab__label">系譜位置</h4>
              <div class="party-skill-tab__path" data-testid="party-skill-tab__lineage">
                <span class="party-skill-tab__path-side">
                  <span v-if="!lineage.prerequisites.length" class="party-skill-tab__node is-none">—</span>
                  <span v-for="edge in lineage.prerequisites" :key="edge.key" class="party-skill-tab__node" data-testid="party-skill-tab__prerequisite">{{ edge.label }}<small>{{ edge.levelText }}</small></span>
                </span>
                <span class="party-skill-tab__arrow" aria-hidden="true">→</span>
                <span class="party-skill-tab__node is-current" data-testid="party-skill-tab__current">{{ selected.row.label }}</span>
                <span class="party-skill-tab__arrow" aria-hidden="true">→</span>
                <span class="party-skill-tab__path-side">
                  <span v-if="!lineage.next.length" class="party-skill-tab__node is-none">—</span>
                  <span v-for="edge in lineage.next" :key="edge.key" class="party-skill-tab__node is-locked" data-testid="party-skill-tab__next">{{ edge.label }}<small>{{ edge.levelText }}</small></span>
                </span>
              </div>
              <button type="button" class="party-skill-tab__link" data-testid="party-skill-tab__lineage-link" @click="emit('lineage')">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path :d="glyph('lineage').d" stroke="currentColor" stroke-width="1.6" v-bind="glyph('lineage').attrs" /></svg>在系譜中檢視
              </button>
            </template>
          </template>
          <p v-else class="party-skill-tab__note" data-testid="party-skill-tab__passive-note">常駐生效，不需施放。</p>
        </div>
      </template>

      <template v-if="detail && actions.length" #actions>
        <ActionBar :actions="actions" @action="onAction" @keydown="onDetailKeydown">
          <template #lead>
            <p v-if="notice" class="party-skill-tab__alert" role="alert" data-testid="party-skill-tab__notice">無法施放：{{ notice }}</p>
            <p v-if="practiceFeedback" class="party-skill-tab__status" role="status" data-testid="party-skill-tab__practice-feedback">{{ practiceFeedback }}</p>
          </template>
        </ActionBar>
      </template>
    </ListDetail>
  </div>
</template>

<style scoped>
/* The approved prototype's 技能 tab (docs/design/party-member-management/
   tabs/SkillTab.vue and prototype.css `.pm-sech`, `.pm-row`, `.pm-icon`,
   `.pm-tag`, `.pm-meter`, `.pm-ribbon`, `.pm-facts`, `.pm-label`). Every
   state that has a colour also has text or a shape: 新 and 修煉中 are text
   tags, a capped meter says 見頂, a locked rung is dashed with a lock glyph
   and 需 Lv, a cost names its resource. */
.party-skill-tab {
  --skill-line: rgba(185, 154, 96, 0.28);
  --skill-line-soft: rgba(185, 154, 96, 0.14);
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.party-skill-tab__reason {
  margin: var(--sp-4) 0 0;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

/* ── segment and search ───────────────────────────────────────── */
.party-skill-tab__seg {
  display: flex;
  margin-bottom: var(--sp-3);
  overflow: hidden;
  border: calc(1px * var(--ui-scale)) solid var(--skill-line);
  border-radius: var(--radius-sm);
}

.party-skill-tab__seg button {
  flex: 1;
  padding: calc(6px * var(--ui-scale)) 0;
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
  letter-spacing: 0.12em;
  background: transparent;
  border: 0;
  cursor: pointer;
  transition: color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}

.party-skill-tab__seg button + button {
  border-left: calc(1px * var(--ui-scale)) solid var(--skill-line);
}

.party-skill-tab__seg button b {
  margin-left: calc(2px * var(--ui-scale));
  font: 500 var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.party-skill-tab__seg button:hover {
  color: var(--paper-200);
}

.party-skill-tab__seg button.is-active {
  color: var(--gold-300);
  background: linear-gradient(180deg, rgba(207, 68, 68, 0.24), rgba(207, 68, 68, 0.12));
  box-shadow: inset 0 calc(-2px * var(--ui-scale)) 0 var(--seal-500);
}

.party-skill-tab__seg button:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-skill-tab__search {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
  padding: calc(5px * var(--ui-scale)) var(--sp-3);
  color: var(--paper-500);
  background: rgba(0, 0, 0, 0.22);
  border: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-radius: var(--radius-sm);
  transition: border-color var(--motion-fast) ease;
}

.party-skill-tab__search:focus-within {
  border-color: var(--gold-500);
  box-shadow: var(--focus);
}

.party-skill-tab__search svg {
  flex: none;
  width: calc(15px * var(--ui-scale));
  height: calc(15px * var(--ui-scale));
}

.party-skill-tab__search input {
  flex: 1;
  min-width: 0;
  color: var(--paper-100);
  font: var(--text-xs) var(--f-sans);
  background: transparent;
  border: 0;
  outline: none;
}

.party-skill-tab__search input:focus-visible {
  box-shadow: none;
}

.party-skill-tab__search kbd {
  padding: 0 calc(5px * var(--ui-scale));
  color: var(--paper-700);
  font: var(--text-xs) var(--f-num);
  border: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-radius: calc(3px * var(--ui-scale));
}

.party-skill-tab__empty {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-3);
  margin-top: var(--sp-3);
  padding: var(--sp-4);
  color: var(--paper-500);
  font-size: var(--text-sm);
  border: calc(1px * var(--ui-scale)) dashed var(--ink-600);
  border-radius: var(--radius-sm);
}

.party-skill-tab__clear,
.party-skill-tab__link {
  padding: 0;
  color: var(--gold-400);
  font: var(--text-xs) var(--f-sans);
  text-decoration: underline;
  text-underline-offset: calc(3px * var(--ui-scale));
  background: none;
  border: 0;
  cursor: pointer;
}

.party-skill-tab__clear:focus-visible,
.party-skill-tab__link:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

/* ── category tree ────────────────────────────────────────────── */
.party-skill-tab__category + .party-skill-tab__category {
  margin-top: var(--sp-2);
}

.party-skill-tab__sech {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  width: 100%;
  margin: var(--sp-3) 0 var(--sp-1);
  padding: calc(2px * var(--ui-scale)) var(--sp-1);
  color: var(--gold-300);
  font: var(--text-base) var(--f-display);
  letter-spacing: 0.06em;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.party-skill-tab__sech:hover {
  background: rgba(255, 255, 255, 0.025);
}

.party-skill-tab__sech:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-skill-tab__chevron {
  flex: none;
  width: calc(12px * var(--ui-scale));
  color: var(--paper-500);
  font-size: var(--text-xs);
  transition: transform var(--motion-fast) var(--ease-standard);
}

.party-skill-tab__sech[aria-expanded="true"] .party-skill-tab__chevron {
  color: var(--gold-400);
  transform: rotate(90deg);
}

.party-skill-tab__sech-label {
  flex: none;
}

.party-skill-tab__sech-rule {
  flex: 1;
  min-width: var(--sp-4);
  height: calc(1px * var(--ui-scale));
  background: linear-gradient(90deg, var(--skill-line), transparent);
}

.party-skill-tab__sech-count {
  flex: none;
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  letter-spacing: 0;
  font-variant-numeric: tabular-nums;
}

.party-skill-tab__group--bare {
  margin-top: var(--sp-2);
}

.party-skill-tab__group-label {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: var(--sp-2) 0 calc(2px * var(--ui-scale)) calc(20px * var(--ui-scale));
  color: var(--paper-400);
  font-size: var(--text-xs);
  letter-spacing: 0.1em;
}

.party-skill-tab__dot {
  flex: none;
  width: calc(6px * var(--ui-scale));
  height: calc(6px * var(--ui-scale));
  transform: rotate(45deg);
}

.party-skill-tab__row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--sp-3);
  align-items: center;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100);
  border: calc(1px * var(--ui-scale)) solid transparent;
  border-bottom: calc(1px * var(--ui-scale)) dashed var(--skill-line-soft);
  cursor: pointer;
  transition: background-color var(--motion-fast) ease, border-color var(--motion-fast) ease;
}

.party-skill-tab__row:hover {
  background: rgba(255, 255, 255, 0.025);
}

.party-skill-tab__row:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-skill-tab__row.is-selected {
  background: linear-gradient(90deg, rgba(207, 68, 68, 0.22), rgba(228, 200, 142, 0.06));
  border: calc(1px * var(--ui-scale)) solid var(--seal-700);
  border-radius: var(--radius-sm);
  box-shadow: inset calc(3px * var(--ui-scale)) 0 0 var(--seal-500);
}

.party-skill-tab__row.is-selected:focus-visible {
  box-shadow: inset calc(3px * var(--ui-scale)) 0 0 var(--seal-500), var(--focus);
}

.party-skill-tab__icon {
  display: grid;
  place-items: center;
  width: calc(32px * var(--ui-scale));
  height: calc(32px * var(--ui-scale));
  color: var(--gold-400);
  background: radial-gradient(circle at 50% 35%, rgba(228, 200, 142, 0.1), rgba(0, 0, 0, 0.3));
  border: calc(1px * var(--ui-scale)) solid var(--skill-line);
  border-radius: var(--radius-sm);
}

.party-skill-tab__icon svg {
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
}

.party-skill-tab__row.is-selected .party-skill-tab__icon {
  color: var(--gold-300);
  border-color: var(--seal-700);
}

.party-skill-tab__row-main {
  min-width: 0;
}

.party-skill-tab__row-name {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
  font-family: var(--f-serif);
  font-size: var(--text-sm);
}

.party-skill-tab__row-label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.party-skill-tab__tag {
  flex: none;
  padding: 0 calc(4px * var(--ui-scale));
  color: var(--gold-400);
  font: var(--text-xs) var(--f-sans);
  line-height: 1.5;
  border: calc(1px * var(--ui-scale)) solid var(--gold-600);
  border-radius: calc(2px * var(--ui-scale));
}

.party-skill-tab__tag--new {
  color: var(--paper-50);
  background: var(--seal-500);
  border-color: var(--seal-500);
}

.party-skill-tab__meter {
  display: block;
  height: calc(3px * var(--ui-scale));
  margin-top: calc(5px * var(--ui-scale));
  overflow: hidden;
  background: #2a2c30;
  border-radius: calc(2px * var(--ui-scale));
}

.party-skill-tab__meter i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--gold-600), var(--gold-500));
  border-radius: inherit;
}

.party-skill-tab__meter.is-capped i {
  background: var(--gold-300);
  box-shadow: 0 0 calc(6px * var(--ui-scale)) rgba(228, 200, 142, 0.45);
}

.party-skill-tab__row-end {
  min-width: calc(40px * var(--ui-scale));
  color: var(--paper-300);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

.party-skill-tab__row-end.is-capped {
  color: var(--gold-300);
}

.party-skill-tab__badge {
  padding: 0 calc(5px * var(--ui-scale));
  color: var(--paper-400);
  font-size: var(--text-xs);
  border: calc(1px * var(--ui-scale)) solid var(--ink-600);
  border-radius: calc(2px * var(--ui-scale));
}

/* ── detail ───────────────────────────────────────────────────── */
.party-skill-tab__detail {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.party-skill-tab__ribbon {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
  padding: calc(3px * var(--ui-scale)) var(--sp-5) calc(3px * var(--ui-scale)) var(--sp-3);
  color: var(--paper-50);
  font-size: var(--text-xs);
  letter-spacing: 0.08em;
  background: var(--seal-600);
  clip-path: polygon(0 0, 100% 0, calc(100% - calc(10px * var(--ui-scale))) 50%, 100% 100%, 0 100%);
}

.party-skill-tab__ribbon svg {
  width: 1.1em;
  height: 1.1em;
}

.party-skill-tab__title {
  margin: 0;
  color: var(--paper-50);
  font: var(--text-3xl) var(--f-display);
  letter-spacing: 0.04em;
  overflow-wrap: anywhere;
}

.party-skill-tab__eyebrow {
  margin: calc(2px * var(--ui-scale)) 0 0;
  color: var(--gold-400);
  font-size: var(--text-xs);
  letter-spacing: 0.12em;
}

.party-skill-tab__facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-2);
  align-self: stretch;
  margin: var(--sp-4) 0 0;
}

.party-skill-tab__fact {
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-500);
  font-size: var(--text-xs);
  background: rgba(0, 0, 0, 0.18);
  border: calc(1px * var(--ui-scale)) solid var(--skill-line);
  border-radius: var(--radius-sm);
}

.party-skill-tab__fact dt {
  letter-spacing: 0.1em;
}

.party-skill-tab__fact dd {
  margin: calc(2px * var(--ui-scale)) 0 0;
  color: var(--paper-50);
  font: 500 var(--text-sm) var(--f-sans);
  overflow-wrap: anywhere;
}

.party-skill-tab__fact dd small {
  margin-left: var(--sp-1);
  color: var(--paper-500);
  font-size: var(--text-xs);
  font-weight: 400;
}

.party-skill-tab__fact dd.is-mp { color: var(--vit-mp); }
.party-skill-tab__fact dd.is-sp { color: var(--vit-sp); }
.party-skill-tab__fact dd.is-free { color: var(--paper-300); }
.party-skill-tab__fact dd.is-field { color: var(--buff); }
.party-skill-tab__fact dd.is-combat-only { color: var(--paper-300); }

.party-skill-tab__label {
  align-self: stretch;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: var(--sp-5) 0 var(--sp-2);
  color: var(--gold-400);
  font-size: var(--text-xs);
  font-weight: 400;
  letter-spacing: 0.14em;
}

.party-skill-tab__label::after {
  content: "";
  flex: 1;
  height: calc(1px * var(--ui-scale));
  background: linear-gradient(90deg, var(--skill-line-soft), transparent);
}

.party-skill-tab__scales {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: var(--sp-2);
  align-self: stretch;
  margin: 0;
  padding: 0;
  list-style: none;
}

.party-skill-tab__scales li {
  display: grid;
  justify-items: center;
  gap: calc(2px * var(--ui-scale));
  padding: var(--sp-2) var(--sp-1);
  color: var(--paper-300);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
  background: rgba(0, 0, 0, 0.18);
  border: calc(1px * var(--ui-scale)) solid var(--skill-line);
  border-radius: var(--radius-sm);
}

.party-skill-tab__scales b {
  color: var(--paper-50);
  font: 500 var(--text-sm) var(--f-num);
}

.party-skill-tab__scales li.is-standard {
  border-color: var(--gold-500);
  box-shadow: inset 0 0 0 calc(1px * var(--ui-scale)) rgba(228, 200, 142, 0.18);
}

.party-skill-tab__scales li.is-standard b {
  color: var(--gold-300);
}

.party-skill-tab__scales li.is-locked {
  color: var(--paper-500);
  background: transparent;
  border-style: dashed;
  border-color: var(--ink-600);
}

.party-skill-tab__scales li.is-locked b {
  color: var(--paper-500);
}

.party-skill-tab__scales span {
  display: inline-flex;
  align-items: center;
  gap: calc(3px * var(--ui-scale));
}

.party-skill-tab__scales svg {
  width: 1em;
  height: 1em;
}

.party-skill-tab__prog {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: var(--sp-3);
  align-items: center;
  align-self: stretch;
  color: var(--paper-200);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.party-skill-tab__prog-level {
  color: var(--paper-50);
  font: 500 var(--text-sm) var(--f-num);
}

.party-skill-tab__prog.is-capped .party-skill-tab__prog-level {
  color: var(--gold-300);
}

.party-skill-tab__track {
  height: calc(6px * var(--ui-scale));
  overflow: hidden;
  background: #25272b;
  border-radius: calc(3px * var(--ui-scale));
  box-shadow: inset 0 calc(1px * var(--ui-scale)) calc(2px * var(--ui-scale)) rgba(0, 0, 0, 0.5);
}

.party-skill-tab__track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--gold-600), var(--gold-500));
  border-radius: inherit;
}

.party-skill-tab__prog.is-capped .party-skill-tab__track i {
  background: var(--gold-300);
}

.party-skill-tab__prog-xp {
  color: var(--paper-400);
}

.party-skill-tab__path {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
  color: var(--paper-500);
  font-size: var(--text-xs);
}

.party-skill-tab__path-side {
  display: inline-flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
}

.party-skill-tab__arrow {
  color: var(--paper-700);
}

.party-skill-tab__node {
  display: inline-flex;
  align-items: baseline;
  gap: var(--sp-1);
  padding: calc(3px * var(--ui-scale)) var(--sp-3);
  color: var(--paper-100);
  font-family: var(--f-serif);
  font-size: var(--text-sm);
  border: calc(1px * var(--ui-scale)) solid var(--skill-line);
  border-radius: var(--radius-sm);
}

.party-skill-tab__node small {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
}

.party-skill-tab__node.is-current {
  color: var(--gold-300);
  background: rgba(207, 68, 68, 0.12);
  border-color: var(--seal-500);
}

.party-skill-tab__node.is-locked {
  color: var(--paper-400);
  border-style: dashed;
}

.party-skill-tab__node.is-none {
  color: var(--paper-700);
  border-color: transparent;
}

.party-skill-tab__link {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  margin-top: var(--sp-3);
}

.party-skill-tab__link svg {
  width: 1.1em;
  height: 1.1em;
}

.party-skill-tab__note {
  margin: var(--sp-4) 0 0;
  color: var(--paper-400);
  font-size: var(--text-sm);
}

.party-skill-tab__alert {
  margin: 0;
  color: var(--seal-400);
  font-size: var(--text-xs);
}

.party-skill-tab__alert::before {
  content: "✕ ";
}

.party-skill-tab__status {
  margin: 0;
  color: var(--paper-300);
  font-size: var(--text-xs);
}

@media (prefers-reduced-motion: reduce) {
  .party-skill-tab__seg button,
  .party-skill-tab__search,
  .party-skill-tab__chevron,
  .party-skill-tab__row {
    transition: none;
  }
}
</style>
