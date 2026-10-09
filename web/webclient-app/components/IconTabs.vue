<script setup>
// IconTabs (quest-drawer-ui-primitives, design Decisions 1-4): an icon-only
// tablist that serves both the horizontal first level and the vertical
// second-level rail of the quest drawer, so focus, tooltip, and badge
// behavior is identical at both levels.
//
// Selection follows activation, not focus: arrow keys, Home, and End move a
// roving focus (with wraparound), and Enter, Space, or a click selects. A
// disabled tab uses `aria-disabled` rather than native `disabled`, so it
// stays focusable and its reason stays reachable; selecting it does nothing.
// A tab's `reason` (the why of a disabled tab, or a note such as a locked
// grade's) shows in the tooltip and is wired as the tab's description.
import { computed, nextTick, ref, useId, watch } from "vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";

const props = defineProps({
  // [{ key, label, glyph?, count?, hot?, disabled?, reason?, locked?, dim?,
  //    mark?, controls? }]
  tabs: { type: Array, required: true },
  modelValue: { type: String, default: null },
  orientation: {
    type: String,
    default: "horizontal",
    validator: (value) => ["horizontal", "vertical"].includes(value),
  },
  ariaLabel: { type: String, default: null },
});

const emit = defineEmits(["update:modelValue"]);

const uid = useId();
const reasonId = (tab) => `icon-tabs-reason-${uid}-${tab.key}`;

const keys = computed(() => props.tabs.map((tab) => tab.key));
const hasKey = (key) => key != null && keys.value.includes(key);

// The last tab focused by arrow keys. The tab that carries `tabindex="0"`
// falls back to the selected tab and then the first tab, so the list stays
// keyboard-reachable when the tabs or the selection change underneath it.
const focusKey = ref(props.modelValue);
const rovingKey = computed(() => {
  if (hasKey(focusKey.value)) return focusKey.value;
  if (hasKey(props.modelValue)) return props.modelValue;
  return keys.value[0] ?? null;
});

watch(
  () => props.modelValue,
  (value) => {
    focusKey.value = value;
  },
);

const hasCount = (tab) => typeof tab.count === "number" && Number.isFinite(tab.count);
// The badge is never color-only: the accessible name carries the count.
const accessibleName = (tab) => (hasCount(tab) ? `${tab.label}（${tab.count}）` : tab.label);
const tipText = (tab) => (tab.reason ? `${tab.label} · ${tab.reason}` : tab.label);

// Tab buttons by key, for moving focus; never read during render.
const buttons = {};
function setButton(key, el) {
  if (el) buttons[key] = el;
  else delete buttons[key];
}

function select(key) {
  const tab = props.tabs.find((candidate) => candidate.key === key);
  if (!tab || tab.disabled || key === props.modelValue) return;
  emit("update:modelValue", key);
}

async function focusTab(key) {
  focusKey.value = key;
  await nextTick();
  buttons[key]?.focus();
}

const NEXT_KEY = { horizontal: "ArrowRight", vertical: "ArrowDown" };
const PREV_KEY = { horizontal: "ArrowLeft", vertical: "ArrowUp" };

function tabKeyOf(event) {
  return event.target?.closest?.('[role="tab"]')?.dataset.tabKey ?? null;
}

function onKeydown(event) {
  // Leave modified keys (Alt+Arrow history navigation, Ctrl+Home, ...) to
  // the browser.
  if (event.altKey || event.ctrlKey || event.metaKey) return;
  const current = tabKeyOf(event);
  if (current == null || keys.value.length === 0) return;
  const index = keys.value.indexOf(current);
  const last = keys.value.length - 1;
  let target = null;
  switch (event.key) {
    case NEXT_KEY[props.orientation]:
      target = index >= last ? 0 : index + 1;
      break;
    case PREV_KEY[props.orientation]:
      target = index <= 0 ? last : index - 1;
      break;
    case "Home":
      target = 0;
      break;
    case "End":
      target = last;
      break;
    case "Enter":
    case " ":
      // Handled here rather than by the native button click, so the
      // keyboard path selects exactly once; the click this keydown would
      // synthesize is cancelled.
      event.preventDefault();
      select(current);
      return;
    default:
      return;
  }
  event.preventDefault();
  focusTab(keys.value[target]);
}

// When focus leaves the list, the roving stop returns to the selected tab.
function onFocusout(event) {
  if (!event.currentTarget.contains(event.relatedTarget)) {
    focusKey.value = props.modelValue;
  }
}

function onFocusin(event) {
  const key = tabKeyOf(event);
  if (key != null) focusKey.value = key;
}
</script>

<template>
  <div
    class="icon-tabs"
    :class="`icon-tabs--${orientation}`"
    role="tablist"
    :aria-label="ariaLabel || undefined"
    :aria-orientation="orientation"
    @keydown="onKeydown"
    @focusin="onFocusin"
    @focusout="onFocusout"
  >
    <button
      v-for="tab in tabs"
      :key="tab.key"
      :ref="(el) => setButton(tab.key, el)"
      type="button"
      role="tab"
      class="icon-tabs__tab"
      :class="{
        'is-active': tab.key === modelValue,
        'is-disabled': tab.disabled,
        'is-locked': tab.locked,
        'is-dim': tab.dim,
        'is-mark': tab.mark,
      }"
      :data-tab-key="tab.key"
      :data-testid="`icon-tabs__tab--${tab.key}`"
      :data-tip="tipText(tab)"
      :tabindex="tab.key === rovingKey ? 0 : -1"
      :aria-selected="String(tab.key === modelValue)"
      :aria-label="accessibleName(tab)"
      :aria-disabled="tab.disabled ? 'true' : undefined"
      :aria-controls="tab.controls || undefined"
      :aria-describedby="tab.reason ? reasonId(tab) : undefined"
      @click="select(tab.key)"
      @keyup.space.prevent
    >
      <span class="icon-tabs__icon" aria-hidden="true">
        <slot name="icon" :tab="tab">
          <svg v-if="tab.glyph && glyphPath(tab.glyph)" viewBox="0 0 24 24" fill="none">
            <path :d="glyphPath(tab.glyph)" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs(tab.glyph)" />
          </svg>
        </slot>
      </span>
      <span
        v-if="hasCount(tab) && tab.count > 0"
        class="icon-tabs__count"
        :class="{ 'icon-tabs__count--hot': tab.hot }"
        data-testid="icon-tabs__count"
        aria-hidden="true"
      >{{ tab.count }}</span>
      <svg v-if="tab.locked" class="icon-tabs__lock" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path :d="glyphPath('lock')" stroke="currentColor" stroke-width="2" v-bind="glyphAttrs('lock')" />
      </svg>
      <span v-if="tab.mark" class="icon-tabs__mark" aria-hidden="true"></span>
      <span v-if="tab.reason" :id="reasonId(tab)" class="icon-tabs__reason">{{ tab.reason }}</span>
    </button>
  </div>
</template>

<style scoped>
/* Geometry, colors, and the tooltip follow the approved prototype's `.qd-top`
   (horizontal) and `.qd-rail` (vertical) rules
   (docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue). */
.icon-tabs {
  display: flex;
  gap: var(--sp-1);
}

.icon-tabs__tab {
  position: relative;
  display: grid;
  place-items: center;
  box-sizing: border-box;
  color: var(--paper-500);
  background: transparent;
  border: 0;
  cursor: pointer;
  transition: color var(--motion-fast) ease, background-color var(--motion-fast) ease;
}

.icon-tabs__icon {
  display: grid;
  place-items: center;
  transition: opacity var(--motion-fast) ease;
}

.icon-tabs__icon svg {
  stroke-linecap: round;
  stroke-linejoin: round;
}

.icon-tabs__tab:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.icon-tabs__tab:hover:not(.is-disabled) {
  color: var(--paper-100);
}

.icon-tabs__tab.is-active {
  color: var(--gold-300);
}

.icon-tabs__tab.is-disabled {
  cursor: not-allowed;
}

.icon-tabs__tab.is-disabled .icon-tabs__icon {
  opacity: 0.35;
}

.icon-tabs__tab.is-dim .icon-tabs__icon {
  opacity: 0.38;
  filter: grayscale(0.7);
}

.icon-tabs__tab.is-locked .icon-tabs__icon {
  opacity: 0.22;
}

/* ---- Horizontal: icon tabs on the header rule. The active tab carries a
   seal-red underline over the host's rule and a gold glow. */
.icon-tabs--horizontal {
  align-self: end;
}

.icon-tabs--horizontal .icon-tabs__tab {
  min-width: calc(64px * var(--ui-scale));
  padding: var(--sp-2) var(--sp-3) var(--sp-3);
}

.icon-tabs--horizontal .icon-tabs__icon :deep(svg) {
  width: calc(28px * var(--ui-scale));
  height: calc(28px * var(--ui-scale));
}

.icon-tabs--horizontal .icon-tabs__tab::before {
  content: "";
  position: absolute;
  left: 18%;
  right: 18%;
  bottom: -1px;
  height: 2px;
  background: transparent;
  border-radius: 2px;
}

.icon-tabs--horizontal .icon-tabs__tab.is-active .icon-tabs__icon :deep(svg) {
  filter: drop-shadow(0 0 calc(6px * var(--ui-scale)) rgba(228, 200, 142, 0.45));
}

.icon-tabs--horizontal .icon-tabs__tab.is-active::before {
  background: var(--seal-500);
  box-shadow: 0 0 calc(10px * var(--ui-scale)) var(--seal-glow);
}

/* ---- Vertical: the rail. The active tab "opens" into the content column
   beside it: no right border, the content background, a seal-red marker. */
.icon-tabs--vertical {
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-4) 0 var(--sp-4) var(--sp-2);
  background: rgba(0, 0, 0, 0.28);
  border-right: 1px solid var(--icon-tabs-line, rgba(185, 154, 96, 0.28));
}

.icon-tabs--vertical .icon-tabs__tab {
  height: var(--icon-tabs-tab-h, calc(58px * var(--ui-scale)));
  margin-right: -1px;
  border: 1px solid transparent;
  border-right: 0;
  border-radius: var(--radius) 0 0 var(--radius);
}

.icon-tabs--vertical .icon-tabs__icon :deep(svg) {
  width: calc(26px * var(--ui-scale));
  height: calc(26px * var(--ui-scale));
}

.icon-tabs--vertical .icon-tabs__tab:hover:not(.is-disabled) {
  background: rgba(255, 255, 255, 0.03);
}

.icon-tabs--vertical .icon-tabs__tab.is-active {
  background: var(--icon-tabs-active-bg, #15171c);
  border-color: var(--icon-tabs-line, rgba(185, 154, 96, 0.28));
}

.icon-tabs--vertical .icon-tabs__tab.is-active::before {
  content: "";
  position: absolute;
  left: -1px;
  top: 22%;
  bottom: 22%;
  width: 3px;
  background: var(--seal-500);
  border-radius: 0 2px 2px 0;
  box-shadow: 0 0 calc(8px * var(--ui-scale)) var(--seal-glow);
}

/* ---- Count badge: ink and gold; `hot` is seal-red with a glow. */
.icon-tabs__count {
  position: absolute;
  top: calc(6px * var(--ui-scale));
  right: calc(6px * var(--ui-scale));
  display: grid;
  place-items: center;
  box-sizing: border-box;
  min-width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  padding: 0 calc(4px * var(--ui-scale));
  color: var(--gold-300);
  font: 600 calc(12px * var(--ui-scale)) / 1 var(--f-num);
  background: var(--ink-950);
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-pill);
}

.icon-tabs__count--hot {
  color: var(--paper-50);
  background: var(--seal-600);
  border-color: var(--ink-950);
  box-shadow: 0 0 calc(8px * var(--ui-scale)) var(--seal-glow);
}

/* ---- Locked corner mark and the gold "this is yours" dot. */
.icon-tabs__lock {
  position: absolute;
  right: calc(7px * var(--ui-scale));
  bottom: calc(6px * var(--ui-scale));
  width: calc(12px * var(--ui-scale));
  height: calc(12px * var(--ui-scale));
  color: var(--paper-500);
}

.icon-tabs__mark {
  position: absolute;
  right: calc(8px * var(--ui-scale));
  bottom: calc(7px * var(--ui-scale));
  width: calc(5px * var(--ui-scale));
  height: calc(5px * var(--ui-scale));
  border-radius: 50%;
  background: var(--gold-400);
}

.icon-tabs__tab.is-locked .icon-tabs__mark {
  right: calc(22px * var(--ui-scale));
}

/* The reason is read through `aria-describedby`; the tooltip shows it. */
.icon-tabs__reason {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

/* ---- Tooltip: hover and keyboard focus, never stealing the pointer.
   Right of a vertical tab, below a horizontal one. */
.icon-tabs__tab:hover::after,
.icon-tabs__tab:focus-visible::after {
  content: attr(data-tip);
  position: absolute;
  z-index: 5;
  padding: calc(4px * var(--ui-scale)) calc(10px * var(--ui-scale));
  white-space: nowrap;
  color: var(--paper-50);
  font: var(--text-xs) var(--f-sans);
  background: #0b0d10f2;
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  box-shadow: 0 calc(6px * var(--ui-scale)) calc(18px * var(--ui-scale)) rgba(0, 0, 0, 0.5);
  pointer-events: none;
}

.icon-tabs--vertical .icon-tabs__tab:hover::after,
.icon-tabs--vertical .icon-tabs__tab:focus-visible::after {
  left: calc(100% + calc(10px * var(--ui-scale)));
  top: 50%;
  transform: translateY(-50%);
}

.icon-tabs--horizontal .icon-tabs__tab:hover::after,
.icon-tabs--horizontal .icon-tabs__tab:focus-visible::after {
  left: 50%;
  top: calc(100% + calc(8px * var(--ui-scale)));
  transform: translateX(-50%);
}

@media (prefers-reduced-motion: reduce) {
  .icon-tabs__tab,
  .icon-tabs__icon {
    transition: none;
  }
}
</style>
