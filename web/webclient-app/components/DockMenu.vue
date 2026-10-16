<script setup>
// DockMenu (H3 webclient-hud-03-action-dock, task 5.8): the pane host. One
// row container carries the listbox role, the single tab stop,
// `aria-activedescendant`, and `data-testid="dock-menu"`. The pane renders
// its rows by pane kind (task 5.1): `commands` (the combat root, category,
// and group lists — webclient-combat-command-window) / `skills` /
// `targets` / `scales` / `confirm` / `plain`. The exploration root is not a
// DockMenu frame at all — it is the exit compass's pane, an empty router
// menu (exploration-room-actions); a target's affordances render on the
// stage's verb card (exploration-presence-rail), and the suggestions on the
// centred suggestions card, not here.
//
// Every row keeps the preserved `#<idPrefix>-<i>` row id and the
// `data-item-key` identity (defined in exactly one place, task 5.2). The
// detail pane keeps `exploration-detail` / `combat-detail` as the pane's
// testid (task 5.8).
//
// The `strip` detail (webclient-combat-command-card-centred D5): in the narrow
// combat card the detail is a fixed three-line strip under the rows — a meta
// line (a command's count or next key, an item's cost), then the description
// or a disabled entry's reason clamped to two lines. Its full text stays in
// the DOM and rides `title`; the focused row's `aria-describedby` names the
// strip (the same id SkillDetailPane's strip carries; one strip renders).
import { computed, inject, nextTick, watch } from "vue";
import { classifyPane, DOCK_DETAIL_STRIP_ID, DOCK_DETAIL_VARIANT } from "./dock-panes.js";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { actionIntentForItem, disabledReasonText, dockItemKeys } from "./dock-items.js";

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
  // The router's menu depth (kept for the hosts that pass it).
  depth: { type: Number, default: 1 },
  // "pane" or "strip" (the combat card); when unset, the variant the hosting
  // dock provides.
  variant: { type: String, default: null },
});

const providedVariant = inject(DOCK_DETAIL_VARIANT, null);
const isStrip = computed(() => (props.variant || providedVariant?.value || "pane") === "strip");
// In the strip variant the focused row is described by the strip, whichever
// component renders it (this detail, or SkillDetailPane while a skill is
// focused).
function describedBy(row) {
  return isStrip.value && row.key === props.focusedKey ? DOCK_DETAIL_STRIP_ID : null;
}

const emit = defineEmits(["activate", "focus-change"]);

const paneKind = computed(() => classifyPane({ items: props.items }));

const rows = computed(() =>
  dockItemKeys(props.items).map((key, index) => ({
    key,
    item: props.items[index],
    rowId: `${props.idPrefix}-${index}`,
    intent: actionIntentForItem(props.items[index]),
    reason: disabledReasonText(props.items[index]),
    glyph: props.items[index].command ? glyphPath(key) : null,
  })),
);

// The detail's next-key hint: a row that submits "executes"; a row that
// opens a frame, a drawer, or a confirmation "opens".
function actionHint(item) {
  return item.action_id && !String(item.action_id).startsWith("open-") ? "執行" : "開啟";
}

const focusedRow = computed(
  () => rows.value.find((row) => row.key === props.focusedKey) ?? null,
);

// The strip's meta line: a command's count, its next key (or 無法使用); an
// item's cost.
const stripMeta = computed(() => {
  const row = focusedRow.value;
  if (!row) {
    return null;
  }
  if (paneKind.value === "commands") {
    if (row.item.enabled === false) {
      return { text: "無法使用", tone: "off" };
    }
    if (row.item.count) {
      return { text: `共 ${row.item.count} 項技能`, tone: "count" };
    }
    return { key: "Enter", text: actionHint(row.item), tone: "hint" };
  }
  if (row.item.cost_text) {
    return { text: row.item.cost_text, tone: "cost" };
  }
  return null;
});
const stripBody = computed(() => {
  const row = focusedRow.value;
  if (props.detailMessage) {
    return { text: props.detailMessage, reason: true };
  }
  if (!row) {
    return null;
  }
  if (row.item.enabled === false) {
    return { text: row.reason || "（無法使用）", reason: true };
  }
  return row.item.description ? { text: row.item.description, reason: false } : null;
});
const stripTitle = computed(() =>
  [
    focusedRow.value?.item.label,
    stripMeta.value && (stripMeta.value.key ? `${stripMeta.value.key} ${stripMeta.value.text}` : stripMeta.value.text),
    stripBody.value?.text,
  ]
    .filter(Boolean)
    .join(" ‧ "),
);

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

// A 威力 row's label split into its prefix and its magnitude (`威力×2` →
// `威力` + `×2`); any other label is all magnitude.
function scaleParts(label) {
  const text = String(label ?? "");
  return text.startsWith("威力") ? { prefix: "威力", magnitude: text.slice(2) } : { prefix: "", magnitude: text };
}

// The fixed framed-grid geometry (the `.dock-menu` container's `:style`
// carries the attribute the B2 gate reads); the row container applies the
// same `grid-template-columns` so the fixed column count actually lays out
// the rows. Every pane kind keeps the stretch-to-fill `1fr` track function:
// the one content-sized consumer was the retired scripted-keyword nav pane
// (webclient-talk-open-dock). Whether a pane form fills its width or leaves
// width empty is the form's own styles' decision; this inline template only
// fixes the column count.
const paneGridStyle = computed(() => {
  if (!props.gridCols) {
    return {};
  }
  return { "grid-template-columns": `repeat(${props.gridCols}, 1fr)` };
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
  <!-- Fragment root (remove-redundant-dock-menu-layout): the row region and
       the optional detail pane are the component's only roots, so the host
       that owns the split (`.dock-pane-host`, or the drawer body) lays them
       out as direct flex children. No anonymous wrapper sits between the
       host and either child.

       The single row container (the active row container at depth ≥ 2).
       The listbox composite: `role="listbox"`, one tab stop,
       `aria-activedescendant`, and `data-testid="dock-menu"` only at
       depth ≥ 2 (task 1.1/5.8). -->
  <div
    class="dock-menu"
      role="listbox"
      tabindex="0"
      :aria-activedescendant="focusedRow ? focusedRow.rowId : null"
      :style="gridCols ? { 'grid-template-columns': 'repeat(' + gridCols + ', 1fr)' } : {}"
      data-testid="dock-menu"
      :data-pane-kind="paneKind"
    >
      <!-- COMMANDS (webclient-combat-command-window): the combat root,
           category, and group frames as one vertical list — a glyph slot,
           the label, and a neutral inline count; the focused row carries the
           muted-gold fill and the leading caret. -->
      <div v-if="paneKind === 'commands'" class="dock-menu__commands">
        <button
          v-for="row in rows"
          :id="row.rowId"
          :key="row.key"
          type="button"
          role="option"
          :aria-selected="row.key === focusedKey"
          class="dock-menu__command"
          :class="{
            'dock-menu__command--on': row.key === focusedKey,
            'dock-menu__command--disabled': row.item.enabled === false,
          }"
          :aria-disabled="row.item.enabled === false"
          :data-item-key="row.key"
          :aria-describedby="describedBy(row)"
          tabindex="-1"
          @click="onCellClick(row)"
        >
          <svg
            v-if="row.glyph"
            class="dock-menu__command-icon"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <path :d="row.glyph" stroke="currentColor" stroke-width="1.8" v-bind="glyphAttrs(row.key)" />
          </svg>
          <span v-else class="dock-menu__command-mark" aria-hidden="true"></span>
          <span class="dock-menu__command-label">{{ row.item.label }}</span>
          <span v-if="row.item.count" class="dock-menu__command-count">{{ row.item.count }}</span>
          <span v-if="row.item.enabled === false" class="dock-menu__command-unavailable" aria-hidden="true">無法使用</span>
          <span v-if="row.item.enabled === false && row.reason" class="visually-hidden">{{ row.reason }}</span>
        </button>
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
          :aria-describedby="describedBy(row)"
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
          :aria-describedby="describedBy(row)"
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
          :aria-describedby="describedBy(row)"
          tabindex="-1"
          @click="onCellClick(row)"
        >
          <!-- The label's 威力 prefix and its magnitude are two inline runs,
               so the narrow card can set the magnitude apart while the
               label's text stays one run. -->
          <span class="dock-menu__scale-label"><span v-if="scaleParts(row.item.label).prefix" class="dock-menu__scale-prefix">{{ scaleParts(row.item.label).prefix }}</span><span class="dock-menu__scale-magnitude">{{ scaleParts(row.item.label).magnitude }}</span></span>
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
          :aria-describedby="describedBy(row)"
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
          :aria-describedby="describedBy(row)"
          :data-team="row.item.team || null"
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

    <!-- The detail pane: names the focused skill/item (tasks 5.8/6.5).
         The scene overview (the exploration root) is not a DockMenu frame,
         so every pane kind here renders the aside by the same rule. -->
    <aside
      v-if="isStrip && ((props.showDetail && focusedRow && !props.hideGenericDetail) || props.detailMessage)"
      :id="DOCK_DETAIL_STRIP_ID"
      class="dock-detail dock-detail--strip"
      :class="{ 'dock-detail--command': paneKind === 'commands' }"
      :data-testid="props.detailTestId"
      tabindex="-1"
      aria-label="項目詳情"
      :title="stripTitle"
    >
      <span v-if="focusedRow" class="visually-hidden" aria-hidden="true">{{ focusedRow.item.label }}</span>
      <div class="dock-detail__meta" :data-tone="stripMeta ? stripMeta.tone : null">
        <template v-if="stripMeta">
          <kbd v-if="stripMeta.key">{{ stripMeta.key }}</kbd>
          <span :class="stripMeta.tone === 'count' ? 'dock-detail__count' : null">{{ stripMeta.text }}</span>
        </template>
      </div>
      <div
        v-if="stripBody"
        class="dock-detail__body"
        :class="stripBody.reason ? 'dock-detail__disabled' : 'dock-detail__desc'"
      >{{ stripBody.text }}</div>
    </aside>
    <aside
      v-else-if="(props.showDetail && focusedRow && !props.hideGenericDetail) || props.detailMessage"
      class="dock-detail"
      :class="{ 'dock-detail--command': paneKind === 'commands' }"
      :data-testid="props.detailTestId"
      tabindex="-1"
      aria-label="項目詳情"
    >
      <template v-if="props.detailMessage">
        <div class="dock-detail__disabled">{{ props.detailMessage }}</div>
      </template>
      <template v-else-if="paneKind === 'commands'">
        <div class="dock-detail__label dock-detail__label--command">{{ focusedRow.item.label }}</div>
        <div v-if="focusedRow.item.count" class="dock-detail__count">共 {{ focusedRow.item.count }} 項技能</div>
        <div v-if="focusedRow.item.description" class="dock-detail__desc">
          {{ focusedRow.item.description }}
        </div>
        <div v-if="focusedRow.item.enabled === false" class="dock-detail__disabled">
          {{ focusedRow.reason || "（無法使用）" }}
        </div>
        <div v-else class="dock-detail__action">
          <kbd>Enter</kbd> {{ actionHint(focusedRow.item) }}
        </div>
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
</template>

<style scoped>
/* The row region is a flex child of its host (`.dock-pane-host`, or the
   drawer body that hosts a service frame); the host owns the side-by-side
   split with the detail pane (remove-redundant-dock-menu-layout: no
   anonymous wrapper between host and row region). */
.dock-menu {
  flex: 1 1 auto;
  min-width: 0;
}
.dock-menu:focus {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}

/* COMMANDS (webclient-combat-command-window): the JRPG command window — a
   single column of glyph + label rows set in the serif face, the focused row
   in a muted-gold wash with a gold caret, a neutral tabular count. */
.dock-menu__commands {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.dock-menu__command {
  position: relative;
  display: grid;
  grid-template-columns: calc(18px * var(--ui-scale)) auto minmax(0, 1fr);
  align-items: center;
  column-gap: calc(12px * var(--ui-scale));
  box-sizing: border-box;
  min-height: calc(32px * var(--ui-scale));
  padding: 2px calc(12px * var(--ui-scale)) 2px calc(24px * var(--ui-scale));
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font-family: var(--f-serif);
  font-size: var(--text-base);
  line-height: 1.3;
  letter-spacing: 0.08em;
  text-align: left;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.dock-menu__command:hover {
  color: var(--paper-50);
  background: rgba(255, 255, 255, 0.03);
}
.dock-menu__command--on {
  color: var(--paper-50);
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.24), rgba(185, 154, 96, 0.05) 75%, transparent);
  border-color: rgba(185, 154, 96, 0.42);
}
.dock-menu__command--on::before {
  content: "▸";
  position: absolute;
  left: calc(8px * var(--ui-scale));
  top: 50%;
  transform: translateY(-50%);
  color: var(--gold-400);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
}
.dock-menu__command-icon {
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  color: var(--gold-500);
}
.dock-menu__command--on .dock-menu__command-icon {
  color: var(--gold-400);
}
/* Rows without a concept glyph (背包, a category, a group) keep the glyph
   column with a small lozenge, so every label starts on one edge. */
.dock-menu__command-mark {
  justify-self: center;
  width: calc(5px * var(--ui-scale));
  height: calc(5px * var(--ui-scale));
  border: 1px solid var(--gold-600);
  transform: rotate(45deg);
}
.dock-menu__command--on .dock-menu__command-mark {
  border-color: var(--gold-400);
  background: rgba(222, 189, 129, 0.35);
}
/* A command label never breaks: the trailing count or suffix yields first. */
.dock-menu__command-label {
  white-space: nowrap;
}
.dock-menu__command-count {
  justify-self: end;
  min-width: 2ch;
  text-align: right;
  font-family: var(--f-num);
  font-size: var(--text-sm);
  letter-spacing: 0;
  color: var(--paper-500);
  font-variant-numeric: tabular-nums lining-nums;
}
.dock-menu__command--on .dock-menu__command-count {
  color: var(--paper-300);
}
.dock-menu__command--disabled {
  color: var(--paper-500);
  cursor: default;
}
.dock-menu__command--disabled .dock-menu__command-icon {
  opacity: 0.5;
}
.dock-menu__command--disabled.dock-menu__command--on {
  background: rgba(255, 255, 255, 0.03);
  border-color: var(--ink-600);
  border-style: dashed;
}
.dock-menu__command--disabled.dock-menu__command--on::before {
  color: var(--paper-500);
}
.dock-menu__command-unavailable {
  grid-column: 3;
  justify-self: end;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--paper-700);
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  letter-spacing: 0;
}

/* SKILLS (task 6.4): the draft's `.sk` rows beside the detail pane. */
.dock-menu__skills {
  display: flex;
  flex-direction: column;
  gap: calc(5px * var(--ui-scale));
  overflow-y: auto;
  padding-right: calc(4px * var(--ui-scale));
}
.dock-menu__skill {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  overflow-wrap: anywhere;
  gap: calc(8px * var(--ui-scale));
  background: var(--ink-780);
  border: 1px solid transparent;
  border-radius: var(--radius);
  padding: calc(7px * var(--ui-scale)) calc(10px * var(--ui-scale));
  font-size: var(--text-sm);
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
  font-family: var(--f-num);
  font-size: var(--text-xs);
  color: var(--vit-mp);
  font-variant-numeric: tabular-nums lining-nums;
}
.dock-menu__skill-check {
  color: var(--ok);
  font-weight: 700;
}

/* TARGETS (task 6.6): the draft's `.tok` tokens — party vs foes, `✓` marker. */
.dock-menu__targets {
  display: flex;
  flex-wrap: wrap;
  gap: calc(6px * var(--ui-scale));
}
.dock-menu__token {
  width: calc(38px * var(--ui-scale));
  height: calc(38px * var(--ui-scale));
  border-radius: var(--radius);
  display: grid;
  place-items: center;
  font-family: var(--f-mono);
  font-size: var(--text-sm);
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
  gap: calc(6px * var(--ui-scale));
}
.dock-menu__scale {
  flex: 1;
  font-family: var(--f-num);
  font-size: var(--text-xs);
  padding: calc(7px * var(--ui-scale));
  border-radius: var(--radius);
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  color: var(--paper-300);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-variant-numeric: tabular-nums lining-nums;
}
.dock-menu__scale--on {
  background: var(--gold-glow);
  border-color: var(--gold-500);
  color: var(--paper-50);
}
.dock-menu__scale-cost {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

/* CONFIRM (task 6.7): the draft's forfeit warning panel with 取消 / 確認投降
   rows. */
.dock-menu__confirm-warn {
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  padding: calc(12px * var(--ui-scale));
}
.dock-menu__confirm-title {
  margin: 0 0 calc(6px * var(--ui-scale));
  font-size: var(--text-md);
  font-weight: 600;
  color: var(--seal-400);
}
.dock-menu__confirm-note {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--paper-500);
}
.dock-menu__confirm-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: calc(8px * var(--ui-scale));
  margin-top: calc(10px * var(--ui-scale));
}
.dock-menu__confirm-btn {
  padding: calc(8px * var(--ui-scale)) calc(16px * var(--ui-scale));
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius);
  color: var(--paper-300);
  cursor: pointer;
  font-size: var(--text-sm);
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
  min-width: 0;
  min-height: calc(38px * var(--ui-scale));
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100);
  background: var(--ink-860);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  text-align: center;
  white-space: normal;
  overflow-wrap: anywhere;
  cursor: pointer;
}
.dock-menu-item--focused {
  background: var(--gold-glow);
  border-color: var(--gold-500);
  color: var(--paper-50);
}
.dock-menu-item--focused::before {
  content: "▶";
  color: var(--gold-400);
  font-size: max(var(--text-xs), 0.8em);
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
  font-size: max(var(--text-xs), 0.85em);
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
  flex: 0 0 calc(220px * var(--ui-scale));
  padding: var(--sp-2) var(--sp-3);
  background: var(--panel);
  border: var(--line);
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

/* The command window's detail (webclient-combat-command-window): the
   highlighted command, category, or group — its name over a short gold
   rule, the committed count, the local explanation, and the next key. */
.dock-detail--command {
  display: flex;
  flex-direction: column;
  gap: calc(8px * var(--ui-scale));
  padding: calc(12px * var(--ui-scale)) calc(14px * var(--ui-scale));
  background: linear-gradient(180deg, rgba(24, 25, 29, 0.78), rgba(12, 13, 16, 0.55));
  border: 1px solid rgba(185, 154, 96, 0.22);
}
.dock-detail__label--command {
  position: relative;
  margin: 0;
  padding-bottom: calc(8px * var(--ui-scale));
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  font-weight: 500;
  letter-spacing: 0.1em;
  color: var(--paper-50);
}
.dock-detail__label--command::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  width: calc(28px * var(--ui-scale));
  height: 1px;
  background: linear-gradient(90deg, var(--gold-400), transparent);
}
.dock-detail__count {
  font-family: var(--f-num);
  font-size: var(--text-sm);
  color: var(--gold-400);
  font-variant-numeric: tabular-nums lining-nums;
}
.dock-detail--command .dock-detail__desc {
  margin: 0;
  font-family: var(--f-serif);
  font-size: var(--text-md);
  line-height: 1.7;
  color: var(--paper-300);
}
.dock-detail--command .dock-detail__disabled {
  font-size: var(--text-md);
  line-height: 1.6;
  color: var(--warn);
}
.dock-detail--command .dock-detail__action {
  margin-top: auto;
  font-size: var(--text-xs);
  color: var(--paper-500);
}
.dock-detail__action kbd {
  font-family: var(--f-mono);
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: var(--radius-sm);
  padding: 0 calc(4px * var(--ui-scale));
  color: var(--paper-300);
}

/* The strip (webclient-combat-command-card-centred D5): three lines of
   `--text-sm` under a fine gold rule, fixed in height — the meta line, then
   the description or reason clamped at two lines with an ellipsis. */
.dock-detail.dock-detail--strip {
  --strip-lh: calc(var(--text-sm) * 1.5);
  position: relative;
  flex: none;
  display: block;
  min-width: 0;
  box-sizing: border-box;
  height: calc(3 * var(--strip-lh) + 8px * var(--ui-scale));
  padding: calc(6px * var(--ui-scale)) calc(4px * var(--ui-scale)) calc(2px * var(--ui-scale));
  overflow: hidden;
  background: none;
  border: 0;
  border-radius: 0;
  font-size: var(--text-sm);
  line-height: var(--strip-lh);
}
.dock-detail--strip::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.5), rgba(185, 154, 96, 0.12) 70%, transparent);
  pointer-events: none;
}
.dock-detail__meta {
  display: flex;
  align-items: center;
  gap: calc(6px * var(--ui-scale));
  height: var(--strip-lh);
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  color: var(--paper-500);
}
.dock-detail__meta > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dock-detail--strip .dock-detail__count {
  font-size: inherit;
}
.dock-detail__meta[data-tone="cost"] {
  font-family: var(--f-num);
  color: var(--vit-mp);
  font-variant-numeric: tabular-nums lining-nums;
}
.dock-detail__meta[data-tone="off"] {
  color: var(--paper-700);
}
.dock-detail__meta kbd {
  font-family: var(--f-mono);
  font-size: calc(var(--text-xs) * 0.9);
  line-height: 1.3;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: var(--radius-sm);
  padding: 0 calc(4px * var(--ui-scale));
  color: var(--paper-300);
}
.dock-detail--strip .dock-detail__body {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  margin: 0;
  font: var(--text-sm) / var(--strip-lh) var(--f-serif);
}
.dock-detail--strip .dock-detail__desc {
  color: var(--paper-300);
}
.dock-detail--strip .dock-detail__disabled {
  color: var(--warn);
}
</style>
