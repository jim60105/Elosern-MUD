<script setup>
// DockMenu (H3 webclient-hud-03-action-dock, task 5.8): the pane host. One
// row container carries the listbox role, the single tab stop,
// `aria-activedescendant`, and `data-testid="dock-menu"` at depth ≥ 2 (the
// tab bar carries the hook at depth 1, task 1.1). The pane renders its rows
// by pane kind (task 5.1): `outlet` / `nav` / `affordance` / `cards` /
// `skills` / `targets` / `scales` / `confirm` / `plain`.
//
// Every row keeps the preserved `#<idPrefix>-<i>` row id and the
// `data-item-key` identity (defined in exactly one place, task 5.2). The
// detail pane keeps `exploration-detail` / `combat-detail` as the pane's
// testid (task 5.8).
import { computed, nextTick, watch } from "vue";
import { classifyPane } from "./dock-panes.js";
import { glyphPath } from "./dock-icons.js";
import { actionIntentForItem, disabledReasonText, dockItemKeys } from "./dock-items.js";
import OptionCard from "./OptionCard.vue";

const props = defineProps({
  items: { type: Array, required: true },
  focusedKey: { type: String, default: null },
  idPrefix: { type: String, default: "dock-row" },
  gridCols: { type: Number, default: null },
  detailTestId: { type: String, default: "dock-detail" },
  detailMessage: { type: String, default: null },
  showDetail: { type: Boolean, default: true },
  // When a dedicated `SkillDetailPane` owns the `combat-detail` testid, the
  // generic detail aside is suppressed so exactly one `combat-detail` exists.
  hideGenericDetail: { type: Boolean, default: false },
  // The router's menu depth: the pane container carries `dock-menu` at
  // depth ≥ 2 (the tab bar owns the hook at depth 1).
  depth: { type: Number, default: 1 },
  // The committed view slice (the exit outlet reads the destination label
  // from `local_map.nodes[].label`, task 5.4).
  view: { type: Object, default: null },
  // The target's display_name for the affordance pane's head (task 5.6): the
  // frame's own `target.display_name` (the targetMenuFor title).
  targetName: { type: String, default: null },
});

const emit = defineEmits(["activate", "focus-change"]);

const paneKind = computed(() => classifyPane({ items: props.items }));

const rows = computed(() =>
  dockItemKeys(props.items).map((key, index) => ({
    key,
    item: props.items[index],
    rowId: `${props.idPrefix}-${index}`,
    intent: actionIntentForItem(props.items[index]),
    reason: disabledReasonText(props.items[index]),
  })),
);

// The exit-outlet pane renders one tile per exit: the standard `back` row
// (the breadcrumb chevron owns the close control) is a navigation cell, not
// an exit (task 5.4).
const outletRows = computed(() => rows.value.filter((row) => row.item.key !== "back"));

const focusedRow = computed(
  () => rows.value.find((row) => row.key === props.focusedKey) ?? null,
);

// The destination label for an exit row (task 5.4): joined from the
// committed `local_map.nodes[].label`. No sub-line when the destination is
// not in the committed lattice.
function destinationLabel(item) {
  if (!item.destination || !props.view) {
    return null;
  }
  const model = props.view.localMapModel;
  if (!model || !Array.isArray(model.nodes)) {
    return null;
  }
  const node = model.nodes.find((n) => n.id === item.destination);
  return node ? node.label : null;
}

function onCellFocus(key) {
  emit("focus-change", key);
}

function onCellActivate(key, row) {
  if (row.item.enabled !== false) {
    emit("activate", { key: row.key, item: row.item, intent: row.intent });
  }
}

// B2 Node-contract: a single pointer click focuses AND activates an enabled
// cell (the legacy dock's pointer-activation contract); a disabled cell
// focuses only.
function onCellClick(row) {
  onCellFocus(row.key);
  onCellActivate(row.key, row);
}

// The fixed framed-grid geometry (the `.dock-menu` container's `:style`
// carries the attribute the B2 gate reads); the row container applies the
// same `grid-template-columns` so the fixed column count actually lays out
// the rows (the draft's `repeat(auto-fill, …)` default is overridden).
// Outlet/nav panes size each fixed column to its content (`minmax(0,
// max-content)`) so a short exit list leaves the pane's remaining width
// empty instead of stretching; `min` of 0 lets the tracks compress — never
// overflow — when the pane is narrower than the combined content widths.
// Every other pane kind keeps the stretch-to-fill `1fr` track function.
const paneGridStyle = computed(() => {
  if (!props.gridCols) {
    return {};
  }
  const sizeFn = ["outlet", "nav"].includes(paneKind.value)
    ? "minmax(0, max-content)"
    : "1fr";
  return { "grid-template-columns": `repeat(${props.gridCols}, ${sizeFn})` };
});

// The focused row scrolls into view (task 5.9).
function scrollToFocused() {
  if (!focusedRow.value || typeof document === "undefined") {
    return;
  }
  const el = document.getElementById(focusedRow.value.rowId);
  if (el && typeof el.scrollIntoView === "function") {
    el.scrollIntoView({ block: "nearest" });
  }
}

// Task 5.9: scroll the focused row into view on every frame render and every
// focus change. The watch fires when the focused key, the item set (a frame
// replacement), or the pane kind changes; nextTick defers the scroll until
// the row's DOM element exists. The key is built by a helper because a
// template literal with a ref value access trips the SFC parser.
function focusScrollKey() {
  return [props.focusedKey, props.items.length, paneKind.value].join("|");
}
watch(
  focusScrollKey,
  () => {
    nextTick(() => {
      scrollToFocused();
    });
  },
  { immediate: true },
);
</script>

<template>
  <div class="dock-menu-layout">
    <!-- The single row container (the active row container at depth ≥ 2).
         The listbox composite: `role="listbox"`, one tab stop,
         `aria-activedescendant`, and `data-testid="dock-menu"` only at
         depth ≥ 2 (task 1.1/5.8). -->
    <div
      class="dock-menu"
      role="listbox"
      tabindex="0"
      :aria-activedescendant="focusedRow ? focusedRow.rowId : null"
      :style="gridCols ? { 'grid-template-columns': 'repeat(' + gridCols + ', 1fr)' } : {}"
      v-bind="depth >= 2 ? { 'data-testid': 'dock-menu' } : {}"
    >
      <!-- OUTLET: exit tiles — direction glyph, destination name, no
           sub-line when the destination is not in the committed lattice
           (task 5.4). -->
      <div v-if="paneKind === 'outlet'" class="dock-menu__outlet" :style="paneGridStyle">
        <button
          v-for="row in outletRows"
          :id="row.rowId"
          type="button"
          role="option"
          :aria-selected="row.key === focusedKey"
          class="dock-menu__outlet-tile"
          :class="{ 'dock-menu__outlet-tile--focused': row.key === focusedKey }"
          :data-item-key="row.key"
          tabindex="-1"
          @click="onCellClick(row)"
        >
          <span v-if="row.item.direction" class="dock-menu__outlet-glyph" aria-hidden="true">
            {{ { north: "↑", south: "↓", east: "→", west: "←", northeast: "↗", northwest: "↖", southeast: "↘", southwest: "↙", up: "↑", down: "↓" }[row.item.direction] }}
          </span>
          <b>{{ row.item.label }}</b>
          <small v-if="destinationLabel(row.item)">{{ destinationLabel(row.item) }}</small>
        </button>
      </div>

      <!-- NAV: look/interact target rows (task 5.5): icon, name, backed
           sub-line (entity kind / affordance labels), `›` chevron on rows
           that open a deeper frame. No stat line, no portrait slot. -->
      <div v-else-if="paneKind === 'nav'" class="dock-menu__nav" :style="paneGridStyle">
        <div
          v-for="row in rows"
          :id="row.rowId"
          role="option"
          :aria-selected="row.key === focusedKey"
          class="dock-menu__nav-row"
          :class="{ 'dock-menu__nav-row--focused': row.key === focusedKey }"
          :data-item-key="row.key"
          tabindex="-1"
          @click="onCellClick(row)"
        >
          <span v-if="glyphPath(row.item.kind)" class="dock-menu__nav-icon" aria-hidden="true"></span>
          <div class="dock-menu__nav-text">
            <span class="dock-menu__nav-name">{{ row.item.label }}</span>
            <span v-if="row.item.kind" class="dock-menu__nav-sub">{{ row.item.kind }}</span>
            <span v-else-if="row.item.affordanceLabels && row.item.affordanceLabels.length" class="dock-menu__nav-sub">
              {{ row.item.affordanceLabels.join("・") }}
            </span>
          </div>
          <span
            v-if="row.item.openSubmenu || row.item.openTarget || row.item.openKeywords"
            class="dock-menu__nav-chevron"
            aria-hidden="true"
          >›</span>
        </div>
      </div>

      <!-- AFFORDANCE: target-affordance buttons (task 5.6): the `對 <目標>
           可作：` head from the frame's own `target.display_name`. -->
      <div v-else-if="paneKind === 'affordance'" class="dock-menu__aff" :style="paneGridStyle">
        <p v-if="targetName" class="dock-menu__aff-head">
          對 <b>{{ targetName }}</b> 可作：
        </p>
        <div class="dock-menu__aff-buttons">
          <button
            v-for="row in rows"
            :id="row.rowId"
            type="button"
            role="option"
            :aria-selected="row.key === focusedKey"
            class="dock-menu__aff-btn"
            :class="{ 'dock-menu__aff-btn--focused': row.key === focusedKey }"
            :data-item-key="row.key"
            tabindex="-1"
            @click="onCellClick(row)"
          >
            <span class="dock-menu__aff-label">{{ row.item.label }}</span>
            <span v-if="!row.item.enabled" class="dock-menu__aff-reason">{{ row.reason || "（無法使用）" }}</span>
          </button>
        </div>
      </div>

      <!-- CARDS: the suggestions frame (task 5.7): the `.sug` card in row
           mode (`role="option"` + row id) — a card is a listbox option. -->
      <div v-else-if="paneKind === 'cards'" class="dock-menu__cards" :style="paneGridStyle">
        <OptionCard
          v-for="row in rows"
          :id="row.rowId"
          :item-key="row.key"
          :card="row.item"
          :focused="row.key === focusedKey"
          :row-mode="true"
          @focus="onCellFocus"
          @activate="(k) => onCellActivate(k, row)"
        />
      </div>

      <!-- SKILLS: the master-detail skill rows (task 6.4): label and cost
           beside the detail pane. Single-sub-group categories skip the group
           frame (design D11). -->
      <div v-else-if="paneKind === 'skills'" class="dock-menu__skills" :style="paneGridStyle">
        <button
          v-for="row in rows"
          :id="row.rowId"
          type="button"
          role="option"
          :aria-selected="row.key === focusedKey"
          class="dock-menu__skill"
          :class="{ 'dock-menu__skill--on': row.key === focusedKey }"
          :data-item-key="row.key"
          tabindex="-1"
          @click="onCellClick(row)"
        >
          <span class="dock-menu__skill-name">{{ row.item.label }}</span>
          <span v-if="row.item.cost_text" class="dock-menu__skill-cost">{{ row.item.cost_text }}</span>
          <span v-if="row.item.selected" class="dock-menu__skill-check" aria-hidden="true">✓</span>
        </button>
      </div>

      <!-- TARGETS: the `.tok` token rows (task 6.6): party vs foes, the
           `✓` AREA selection marker. -->
      <div v-else-if="paneKind === 'targets'" class="dock-menu__targets" :style="paneGridStyle">
        <button
          v-for="row in rows"
          :id="row.rowId"
          type="button"
          role="option"
          :aria-selected="row.key === focusedKey"
          class="dock-menu__token"
            :class="{
              'dock-menu__token--ally': row.item.team === 'party',
              'dock-menu__token--foe': row.item.team === 'foes',
              'dock-menu__token--pressed': row.item.selected,
            }"
          :aria-pressed="row.item.selected"
          :data-item-key="row.key"
          tabindex="-1"
          @click="onCellClick(row)"
        >
          {{ row.item.label }}
        </button>
      </div>

      <!-- SCALES: the 威力 step (task 6.6): the server-computed `mp_cost`,
           ascending, `1` preselected. -->
      <div v-else-if="paneKind === 'scales'" class="dock-menu__scales" :style="paneGridStyle">
        <button
          v-for="row in rows"
          :id="row.rowId"
          type="button"
          role="option"
          :aria-pressed="row.key === focusedKey"
          class="dock-menu__scale"
          :class="{ 'dock-menu__scale--on': row.key === focusedKey }"
          :data-item-key="row.key"
          tabindex="-1"
          @click="onCellClick(row)"
        >
          <span>{{ row.item.label }}</span>
          <span v-if="row.item.description" class="dock-menu__scale-cost">{{ row.item.description }}</span>
        </button>
      </div>

      <!-- CONFIRM: the forfeit confirmation panel (task 6.7): 取消 and
           確認投降 rows, still requiring an explicit confirm. -->
      <div v-else-if="paneKind === 'confirm'" class="dock-menu__confirm" :style="paneGridStyle">
        <div class="dock-menu__confirm-warn">
          <p class="dock-menu__confirm-title">確認投降？</p>
          <p class="dock-menu__confirm-note">投降後本場戰鬥結束，無法回復。</p>
        </div>
        <div class="dock-menu__confirm-buttons">
          <button
            v-for="row in rows"
            :id="row.rowId"
            type="button"
            role="option"
            :data-item-key="row.key"
            class="dock-menu__confirm-btn"
            :class="{
              'dock-menu__confirm-btn--primary': row.key.startsWith('confirm'),
              'dock-menu__confirm-btn--focused': row.key === focusedKey,
            }"
            :aria-selected="row.key === focusedKey"
            tabindex="-1"
            @click="onCellClick(row)"
          >
            {{ row.item.label }}
          </button>
        </div>
      </div>

      <!-- PLAIN / default: the legacy cell grid. -->
      <div v-else class="dock-menu__plain" :style="paneGridStyle">
        <button
          v-for="row in rows"
          :id="row.rowId"
          type="button"
          role="option"
          :aria-selected="row.key === focusedKey"
          class="dock-menu-item"
          :class="{
            'dock-menu-item--focused': row.key === focusedKey,
            'dock-menu-item--disabled': row.item.enabled === false,
          }"
          :aria-disabled="row.item.enabled === false"
          data-testid="dock-item"
          :data-item-key="row.key"
          tabindex="-1"
          @click="onCellClick(row)"
        >
          <span v-if="row.item.selected" class="dock-menu-item__checked" aria-hidden="true">✓</span>
          <span class="dock-menu-item__label">{{ row.item.label }}</span>
          <span v-if="row.item.enabled === false" class="dock-menu-item__unavailable" aria-hidden="true">（無法使用）</span>
          <span v-if="row.item.enabled === false && row.reason" class="visually-hidden">{{ row.reason }}</span>
        </button>
      </div>
    </div>

    <!-- The detail pane: names the focused skill/item (tasks 5.8/6.5). -->
    <aside
      v-if="((props.showDetail && focusedRow && !props.hideGenericDetail) || props.detailMessage)"
      class="dock-detail"
      :data-testid="props.detailTestId"
      tabindex="-1"
      aria-label="項目詳情"
    >
      <template v-if="props.detailMessage">
        <div class="dock-detail__disabled">{{ props.detailMessage }}</div>
      </template>
      <template v-else>
        <div class="dock-detail__label">{{ focusedRow.item.label }}</div>
        <div v-if="focusedRow.item.cost_text" class="dock-detail__cost">
          {{ focusedRow.item.cost_text }}
        </div>
        <div v-if="focusedRow.item.description" class="dock-detail__desc">
          {{ focusedRow.item.description }}
        </div>
        <div v-if="focusedRow.item.enabled !== false" class="dock-detail__action">
          Enter → 開啟
        </div>
        <div v-else class="dock-detail__disabled">
          {{ focusedRow.reason || "（無法使用）" }}
        </div>
      </template>
    </aside>
  </div>
</template>

<style scoped>
.dock-menu-layout {
  display: flex;
  gap: var(--sp-3);
  align-items: flex-start;
  flex: 1;
  min-height: 0;
}

.dock-menu {
  flex: 1 1 auto;
  min-width: 0;
}
.dock-menu:focus {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}

/* OUTLET (task 5.4): the draft's `.outlet` grid — direction glyph,
   destination name, no sub-line when the destination is not in the lattice. */
.dock-menu__outlet {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 8px;
}
.dock-menu__outlet-tile {
  display: grid;
  place-items: center;
  text-align: center;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: 9px;
  padding: 9px 8px;
  font-size: 12.5px;
  color: var(--paper-300);
  cursor: pointer;
  max-width: 220px;
  min-width: 0;
  overflow-wrap: break-word;
}
.dock-menu__outlet-tile b {
  display: block;
  font-size: 15px;
  color: var(--paper-100);
  font-family: var(--f-mono);
  margin-bottom: 2px;
}
.dock-menu__outlet-tile small {
  font-size: 10.5px;
  color: var(--paper-500);
}
.dock-menu__outlet-glyph {
  font-size: 14px;
  color: var(--gold-400);
}
.dock-menu__outlet-tile--focused {
  background: var(--seal-600);
  border-color: var(--seal-500);
  color: var(--paper-50);
}
.dock-menu__outlet-tile--focused::before {
  content: "▶";
  color: var(--gold-400);
  font-size: 0.8em;
}

/* NAV (task 5.5): the draft's `.nrow` rows — icon, name, backed sub-line,
   `›` chevron on rows that open a deeper frame. */
.dock-menu__nav {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 9px;
}
.dock-menu__nav-row {
  display: flex;
  gap: 11px;
  align-items: center;
  text-align: left;
  background: linear-gradient(180deg, var(--panel-hi), var(--panel));
  border: 1px solid var(--ink-600);
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  max-width: 320px;
  min-width: 0;
  overflow-wrap: break-word;
}
.dock-menu__nav-row--focused {
  background: var(--seal-600);
  border-color: var(--seal-500);
  color: var(--paper-50);
  transform: translateY(-1px);
}
.dock-menu__nav-row--focused::before {
  content: "▶";
  color: var(--gold-400);
  font-size: 0.8em;
}
.dock-menu__nav-icon {
  width: 26px;
  height: 26px;
  flex: none;
  color: var(--gold-400);
}
.dock-menu__nav-text {
  min-width: 0;
  overflow-wrap: break-word;
}
.dock-menu__nav-name {
  font-size: 14px;
  color: var(--paper-50);
  font-weight: 600;
}
.dock-menu__nav-sub {
  font-size: 11px;
  color: var(--paper-500);
  margin-top: 2px;
}
.dock-menu__nav-chevron {
  margin-left: auto;
  color: var(--paper-700);
  font-size: 16px;
}

/* AFFORDANCE (task 5.6): the draft's `.affbtn` buttons + the `對 <目標>
   可作：` head. */
.dock-menu__aff-head {
  font-size: 12.5px;
  color: var(--paper-300);
  margin: 0 0 10px;
  display: flex;
  gap: 8px;
  align-items: center;
}
.dock-menu__aff-head b {
  color: var(--gold-400);
  font-weight: 600;
}
.dock-menu__aff-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
}
.dock-menu__aff-btn {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  background: linear-gradient(180deg, var(--panel-hi), var(--panel));
  border: 1px solid var(--ink-600);
  border-radius: 9px;
  padding: 10px 14px;
  font-size: 13.5px;
  color: var(--paper-100);
  cursor: pointer;
}
.dock-menu__aff-btn--focused {
  background: var(--seal-600);
  border-color: var(--seal-500);
  color: var(--paper-50);
  transform: translateY(-1px);
}
.dock-menu__aff-btn--focused::before {
  content: "▶";
  color: var(--gold-400);
  font-size: 0.8em;
}
.dock-menu__aff-reason {
  color: var(--paper-500);
  font-size: 11px;
}

/* CARDS (task 5.7): the `.sug` card in row mode (OptionCard). */
.dock-menu__cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 10px;
}

/* SKILLS (task 6.4): the draft's `.sk` rows beside the detail pane. */
.dock-menu__skills {
  display: flex;
  flex-direction: column;
  gap: 5px;
  overflow-y: auto;
  padding-right: 4px;
}
.dock-menu__skill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--ink-780);
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 7px 10px;
  font-size: 13px;
  color: var(--paper-100);
  cursor: pointer;
}
.dock-menu__skill--on {
  border-color: var(--gold-500);
  background: var(--panel-hi);
}
.dock-menu__skill-name {
  font-weight: 500;
}
.dock-menu__skill-cost {
  margin-left: auto;
  font-family: var(--f-mono);
  font-size: 10.5px;
  color: var(--vit-mp);
}
.dock-menu__skill-check {
  color: var(--ok);
  font-weight: 700;
}

/* TARGETS (task 6.6): the draft's `.tok` tokens — party vs foes, `✓` marker. */
.dock-menu__targets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.dock-menu__token {
  width: 38px;
  height: 38px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  font-family: var(--f-mono);
  font-size: 13px;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  color: var(--paper-100);
  cursor: pointer;
}
.dock-menu__token--ally {
  color: var(--vit-mp);
}
.dock-menu__token--foe {
  color: var(--seal-400);
}
.dock-menu__token--pressed {
  border-color: var(--gold-500);
  background: var(--panel-hi);
}

/* SCALES (task 6.6): the draft's `.sc` scale chips — server-computed
   `mp_cost`, ascending, `1` preselected. */
.dock-menu__scales {
  display: flex;
  gap: 6px;
}
.dock-menu__scale {
  flex: 1;
  font-family: var(--f-mono);
  font-size: 12px;
  padding: 7px;
  border-radius: 8px;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  color: var(--paper-300);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.dock-menu__scale--on {
  background: var(--seal-600);
  border-color: var(--seal-500);
  color: #fff;
}
.dock-menu__scale-cost {
  font-size: 10px;
  color: var(--paper-500);
}

/* CONFIRM (task 6.7): the draft's forfeit warning panel with 取消 / 確認投降
   rows. */
.dock-menu__confirm-warn {
  background: var(--panel);
  border: var(--line);
  border-radius: 10px;
  padding: 12px;
}
.dock-menu__confirm-title {
  margin: 0 0 6px;
  font-size: 14px;
  font-weight: 600;
  color: var(--seal-400);
}
.dock-menu__confirm-note {
  margin: 0;
  font-size: 11.5px;
  color: var(--paper-500);
}
.dock-menu__confirm-buttons {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.dock-menu__confirm-btn {
  padding: 8px 16px;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: 8px;
  color: var(--paper-300);
  cursor: pointer;
  font-size: 13px;
}
.dock-menu__confirm-btn--primary {
  background: linear-gradient(180deg, var(--seal-500), var(--seal-700));
  border-color: var(--seal-400);
  color: #fff;
  font-weight: 600;
}
.dock-menu__confirm-btn--focused {
  border-color: var(--gold-500);
}

/* PLAIN: the legacy cell grid. */
.dock-menu-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  text-align: center;
  white-space: nowrap;
  cursor: pointer;
}
.dock-menu-item--focused {
  background: var(--seal-600);
  border-color: var(--seal-500);
  color: var(--paper-50);
}
.dock-menu-item--focused::before {
  content: "▶";
  color: var(--gold-400);
  font-size: 0.8em;
}
.dock-menu-item--disabled {
  color: var(--paper-500);
  background: var(--ink-900);
  border-style: dashed;
  border-color: var(--ink-600);
  cursor: default;
}
.dock-menu-item__checked {
  color: var(--ok);
  font-weight: 700;
}
.dock-menu-item__unavailable {
  color: var(--paper-700);
  font-size: 0.85em;
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
}

/* The detail pane keeps the preserved testid (exploration-detail /
   combat-detail). */
.dock-detail {
  flex: 0 0 220px;
  padding: var(--sp-2) var(--sp-3);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  color: var(--paper-100);
}
.dock-detail__label {
  font-weight: 600;
  margin-bottom: var(--sp-1);
}
.dock-detail__cost {
  color: var(--paper-300);
  margin-bottom: var(--sp-1);
}
.dock-detail__desc {
  color: var(--paper-500);
  margin-bottom: var(--sp-1);
  line-height: 1.5;
}
.dock-detail__action {
  color: var(--paper-500);
}
.dock-detail__disabled {
  color: var(--seal-400);
}
</style>
