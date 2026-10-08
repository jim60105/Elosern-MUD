<script setup>
// SkillUseDock (skillbook-authoritative-casting D8): the dock pane for the
// SkillBook casting flow. It renders the keyboard router's current
// `skilluse.*` frame — the use frame (威力 opener, NONE/SELF confirmation,
// target rows, AREA toggles and their confirm, the 開戰 divider and monster
// openings), the 威力 frame, and the opening confirmation — beside a detail
// card. It is a passive renderer of the router's resolved menu: the listbox
// contract matches DockMenu (one tab stop, `aria-activedescendant`, row ids,
// `data-item-key`), pointer focus/activation route back through the store,
// and every label, cost, reason, and line-up is server-authored.
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps({
  // The router's current resolved menu (`store.view.combatMenu`).
  menu: { type: Object, default: null },
  focusedKey: { type: String, default: null },
  // The store's committed detail model (`store.view.skillUse`).
  detail: { type: Object, default: null },
  // True while a preview or cast is in flight (confirms are locked).
  locked: { type: Boolean, default: false },
});
const emit = defineEmits(["activate", "focus-change"]);

const items = computed(() => (props.menu && Array.isArray(props.menu.items) ? props.menu.items : []));
const isConfirmFrame = computed(() => items.value.some((item) => item.key === "confirm-opening"));
const isScaleFrame = computed(() => items.value.length > 0 && items.value.every((item) => item.kind === "scale" && item.scaleChoice));

const rows = computed(() => {
  let dividerShown = false;
  return items.value.map((item, index) => {
    const divider = item.kind === "opening" && !dividerShown;
    if (divider) dividerShown = true;
    return {
      item,
      key: item.key,
      rowId: `skill-use-row-${index}`,
      divider,
      disabled: item.enabled === false,
    };
  });
});

const focusedRow = computed(() => rows.value.find((row) => row.key === props.focusedKey) ?? null);
const opening = computed(() => (props.menu && props.menu.opening) || null);

function onClick(row) {
  emit("focus-change", row.key);
  if (!row.disabled) {
    emit("activate", { key: row.key });
  }
}

function scaleText(detail) {
  if (!detail) return "";
  const parts = [detail.costText];
  if (detail.scaled) {
    const label = { 0.25: "1/4", 0.5: "1/2", 1: "1", 2: "2", 4: "4" }[detail.scale] || String(detail.scale);
    parts.push(`威力 ×${label}`);
  }
  return parts.join(" ‧ ");
}

const consequence = computed(() => {
  const row = focusedRow.value;
  if (isConfirmFrame.value && opening.value) {
    const count = opening.value.target_ids.length;
    return {
      tone: "fight",
      text: count > 1 ? `全場 ${count} 名敵人將一同參戰。` : "施放後立即進入戰鬥。",
    };
  }
  if (!row) return null;
  if (row.disabled && row.item.disabledReason) {
    return { tone: "reason", text: row.item.disabledReason.message };
  }
  if (row.item.kind === "opening") {
    const count = props.detail?.focused?.lineUpCount || 1;
    return {
      tone: "fight",
      text: count > 1 ? `將開戰，全場 ${count} 名敵人皆受波及。` : "將以這一擊開啟戰鬥。",
    };
  }
  return null;
});

const keyHint = computed(() => {
  const row = focusedRow.value;
  if (!row || row.disabled) return "Esc 返回";
  if (row.item.selectable) return "Space 選取 ‧ Esc 返回";
  if (row.item.kind === "opening" || row.item.kind === "scale") return "Enter 選擇 ‧ Esc 返回";
  return props.locked ? "處理中…" : "Enter 施放 ‧ Esc 返回";
});

const rowsEl = ref(null);

function scrollFocused() {
  const row = focusedRow.value;
  if (!row || typeof document === "undefined") return;
  if (isConfirmFrame.value) {
    // The two-row confirmation always shows its consequence line on top.
    if (rowsEl.value) rowsEl.value.scrollTop = 0;
    return;
  }
  const el = document.getElementById(row.rowId);
  if (el && typeof el.scrollIntoView === "function") el.scrollIntoView({ block: "nearest" });
}
watch(() => [props.focusedKey, items.value.length].join("|"), () => nextTick(scrollFocused), { immediate: true });
</script>

<template>
  <div class="skill-use-dock" data-testid="skill-use-dock" :data-frame="isConfirmFrame ? 'opening' : isScaleFrame ? 'scale' : 'use'">
    <div
      ref="rowsEl"
      class="skill-use-dock__rows"
      :class="{ 'skill-use-dock__rows--confirm': isConfirmFrame }"
      role="listbox"
      tabindex="0"
      :aria-label="menu?.title || '施放'"
      :aria-activedescendant="focusedRow ? focusedRow.rowId : null"
      data-testid="dock-menu"
      data-pane-kind="skill-use"
    >
      <p v-if="isConfirmFrame && opening" class="skill-use-dock__confirm-head" data-testid="skill-use-dock__confirm-head">
        ⚔ {{ opening.label }}
      </p>
      <template v-for="row in rows" :key="row.key">
        <p v-if="row.divider" class="skill-use-dock__divider" aria-hidden="true"><span>開戰</span></p>
        <button
          :id="row.rowId"
          type="button"
          role="option"
          tabindex="-1"
          class="skill-use-dock__row"
          :class="[
            `skill-use-dock__row--${row.item.kind || 'plain'}`,
            {
              'is-on': row.key === focusedKey,
              'is-disabled': row.disabled,
              'is-current': row.item.current,
              'is-locked': locked && !row.disabled && row.item.actionId === 'explore.cast',
            },
          ]"
          :aria-selected="String(row.key === focusedKey)"
          :aria-disabled="String(row.disabled)"
          :aria-checked="row.item.selectable ? String(!!row.item.selected) : undefined"
          :data-item-key="row.key"
          :data-testid="`skill-use-row--${row.key}`"
          @click="onClick(row)"
        >
          <span class="skill-use-dock__mark" aria-hidden="true">
            <template v-if="row.item.selectable">{{ row.item.selected ? "☑" : "☐" }}</template>
            <template v-else-if="row.item.kind === 'opening' || row.key === 'confirm-opening'">⚔</template>
            <template v-else-if="row.item.kind === 'scale' && !row.item.scaleChoice">✦</template>
            <template v-else-if="row.item.kind === 'note'">▲</template>
          </span>
          <span class="skill-use-dock__label">{{ row.item.label }}</span>
          <span v-if="row.disabled && row.item.kind !== 'note'" class="skill-use-dock__suffix">不可選</span>
          <span v-else-if="row.item.kind === 'scale' && row.item.description" class="skill-use-dock__suffix">{{ row.item.description }}</span>
          <span v-else-if="row.item.kind === 'scale' || row.item.kind === 'opening'" class="skill-use-dock__suffix" aria-hidden="true">▸</span>
          <span v-if="row.disabled && row.item.disabledReason" class="visually-hidden">{{ row.item.disabledReason.message }}</span>
        </button>
      </template>
    </div>

    <aside class="skill-use-dock__detail" data-testid="skill-use-detail" aria-label="施放詳情" tabindex="-1">
      <template v-if="detail">
        <p class="skill-use-dock__title">{{ detail.label }}</p>
        <p
          v-if="consequence"
          class="skill-use-dock__consequence"
          :class="`skill-use-dock__consequence--${consequence.tone}`"
          data-testid="skill-use-detail__consequence"
        >{{ consequence.tone === 'fight' ? '⚔ ' : '▲ ' }}{{ consequence.text }}</p>
        <p class="skill-use-dock__cost" data-testid="skill-use-detail__cost">{{ scaleText(detail) }}</p>
        <p class="skill-use-dock__desc">{{ detail.description }}</p>
        <p class="skill-use-dock__hint">{{ keyHint }}</p>
      </template>
    </aside>
  </div>
</template>

<style scoped>
.skill-use-dock {
  display: flex;
  gap: var(--sp-3);
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
}

/* ---- rows: the command-window vocabulary ---- */
.skill-use-dock__rows {
  flex: 1 1 auto;
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
  min-height: 0;
  max-height: 100%;
  overflow-y: auto;
  padding: 1px;
  scrollbar-width: thin;
}
.skill-use-dock__rows:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
  box-shadow: none;
}
.skill-use-dock__row {
  position: relative;
  display: grid;
  grid-template-columns: calc(20px * var(--ui-scale)) minmax(0, 1fr) auto;
  align-items: center;
  column-gap: var(--sp-2);
  flex: none;
  min-height: calc(32px * var(--ui-scale));
  padding: 2px var(--sp-3) 2px calc(22px * var(--ui-scale));
  color: var(--paper-300);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-family: var(--f-serif);
  font-size: var(--text-md);
  letter-spacing: 0.06em;
  line-height: 1.3;
  text-align: left;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.skill-use-dock__row:hover {
  color: var(--paper-50);
  background: rgba(255, 255, 255, 0.03);
}
.skill-use-dock__row.is-on {
  color: var(--paper-50);
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.24), rgba(185, 154, 96, 0.05) 75%, transparent);
  border-color: rgba(185, 154, 96, 0.42);
}
.skill-use-dock__row.is-on::before {
  content: "▸";
  position: absolute;
  left: calc(8px * var(--ui-scale));
  top: 50%;
  transform: translateY(-50%);
  color: var(--gold-400);
  font-family: var(--f-sans);
  font-size: var(--text-xs);
}
.skill-use-dock__mark {
  justify-self: center;
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--gold-500);
}
.skill-use-dock__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.skill-use-dock__suffix {
  justify-self: end;
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  letter-spacing: 0;
  color: var(--paper-500);
  white-space: nowrap;
}
.skill-use-dock__row.is-disabled {
  color: var(--paper-500);
  cursor: default;
}
.skill-use-dock__row.is-disabled.is-on {
  background: rgba(255, 255, 255, 0.03);
  border-color: var(--ink-600);
  border-style: dashed;
}
.skill-use-dock__row.is-disabled.is-on::before {
  color: var(--paper-500);
}
.skill-use-dock__row--confirm {
  color: var(--gold-400);
}
.skill-use-dock__row--confirm.is-on {
  color: var(--gold-300);
}
.skill-use-dock__row--note {
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  letter-spacing: 0;
  color: var(--warn);
}
.skill-use-dock__row--note .skill-use-dock__mark {
  color: var(--warn);
}
.skill-use-dock__row--opening .skill-use-dock__mark {
  color: var(--seal-400);
}
.skill-use-dock__row--scale.is-current .skill-use-dock__label::after {
  content: "　目前";
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  color: var(--gold-400);
}
.skill-use-dock__row.is-locked {
  opacity: 0.6;
}
.skill-use-dock__divider {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: var(--sp-2) 0 var(--sp-1);
  padding-left: calc(22px * var(--ui-scale));
  font-family: var(--f-serif);
  font-size: var(--text-xs);
  letter-spacing: 0.2em;
  color: var(--paper-500);
}
.skill-use-dock__divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--seal-glow), transparent);
}

/* ---- opening confirmation: the flow's only seal fill ---- */
.skill-use-dock__confirm-head {
  flex: 1 0 100%;
  margin: 0;
  padding-left: var(--sp-1);
  font-family: var(--f-serif);
  font-size: var(--text-sm);
  letter-spacing: 0.06em;
  color: var(--seal-400);
  overflow-wrap: anywhere;
}
.skill-use-dock__rows--confirm {
  flex-direction: row;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: var(--sp-2);
}
.skill-use-dock__rows--confirm .skill-use-dock__row--confirm {
  flex: 2 1 auto;
}
.skill-use-dock__rows--confirm .skill-use-dock__row--cancel {
  flex: 1 1 auto;
}
.skill-use-dock__rows--confirm .skill-use-dock__row {
  grid-template-columns: auto auto;
  justify-content: center;
  min-height: calc(32px * var(--ui-scale));
  padding: 0 var(--sp-4);
  border-color: var(--ink-600);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  letter-spacing: 0.08em;
}
.skill-use-dock__rows--confirm .skill-use-dock__label {
  overflow: visible;
  text-overflow: clip;
}
.skill-use-dock__rows--confirm .skill-use-dock__row.is-on::before {
  content: none;
}
.skill-use-dock__rows--confirm .skill-use-dock__row--confirm {
  color: var(--paper-50);
  background: linear-gradient(180deg, var(--seal-500), var(--seal-600));
  border-color: var(--seal-400);
  font-weight: 600;
}
.skill-use-dock__rows--confirm .skill-use-dock__row--confirm:hover {
  filter: brightness(1.08);
}
.skill-use-dock__rows--confirm .skill-use-dock__row--confirm .skill-use-dock__mark {
  color: var(--paper-50);
}
.skill-use-dock__rows--confirm .skill-use-dock__row.is-on {
  box-shadow: var(--focus);
}
.skill-use-dock__rows--confirm .skill-use-dock__row--cancel {
  background: var(--ink-780);
}
.skill-use-dock__rows--confirm .skill-use-dock__row--cancel.is-on {
  color: var(--paper-50);
}

/* ---- detail card ---- */
.skill-use-dock__detail {
  flex: 0 1 min(calc(220px * var(--ui-scale)), 45%);
  align-self: flex-start;
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
  min-width: 0;
  max-height: 100%;
  overflow-y: auto;
  box-sizing: border-box;
  padding: calc(10px * var(--ui-scale)) calc(12px * var(--ui-scale));
  background: linear-gradient(180deg, rgba(24, 25, 29, 0.78), rgba(12, 13, 16, 0.55));
  border: 1px solid rgba(185, 154, 96, 0.22);
  border-radius: var(--radius-sm);
  scrollbar-width: thin;
}
.skill-use-dock__detail p {
  margin: 0;
}
.skill-use-dock__title {
  position: relative;
  padding-bottom: var(--sp-1);
  font-family: var(--f-serif);
  font-size: var(--text-md);
  letter-spacing: 0.1em;
  color: var(--paper-50);
}
.skill-use-dock__title::after {
  content: "";
  position: absolute;
  left: 0;
  bottom: 0;
  width: calc(28px * var(--ui-scale));
  height: 1px;
  background: linear-gradient(90deg, var(--gold-400), transparent);
}
.skill-use-dock__consequence {
  font-size: var(--text-sm);
  line-height: 1.5;
}
.skill-use-dock__consequence--reason {
  color: var(--warn);
}
.skill-use-dock__consequence--fight {
  color: var(--seal-400);
}
.skill-use-dock__cost {
  font-family: var(--f-num);
  font-size: var(--text-sm);
  color: var(--vit-mp);
  font-variant-numeric: tabular-nums lining-nums;
}
.skill-use-dock__desc {
  font-family: var(--f-serif);
  font-size: var(--text-sm);
  line-height: 1.6;
  color: var(--paper-300);
}
.skill-use-dock__hint {
  margin-top: auto;
  font-size: var(--text-xs);
  color: var(--paper-500);
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
</style>
