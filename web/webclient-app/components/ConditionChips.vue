<script setup>
// ConditionChips (H2, webclient-hud-02-status-islands, design D6/D7/D8):
// the left stack's conditions island. One 34×34 icon chip per committed
// condition, pairing a per-severity shape glyph with an accessible name
// carrying the label, the remaining duration (only when the payload
// supplies `remaining_seconds`, shown verbatim — never decremented between
// revisions) and every derived modifier. Visible chips are capped at 6;
// the remainder stays reachable in one action through a bounded,
// scrollable in-island disclosure that collapses on re-activation or
// Escape (H4 re-points this control at the character-status drawer).
import { computed, ref } from "vue";

const props = defineProps({
  // The committed `status.conditions[]` array (icon-only chips).
  conditions: { type: Array, default: () => [] },
});

// Five distinct glyph shapes: the `warning` glyph changed from the old
// panel's `▲` (shared with `beneficial`) to `▽`, so no two severities are
// separated by colour alone.
const SEVERITY_GLYPHS = {
  beneficial: "▲",
  informational: "◆",
  warning: "▽",
  harmful: "▼",
  critical: "✕",
};

const VISIBLE_CAP = 6;

const visible = computed(() => props.conditions.slice(0, VISIBLE_CAP));
const overflowCount = computed(() => Math.max(0, props.conditions.length - VISIBLE_CAP));
const overflowItems = computed(() => props.conditions.slice(VISIBLE_CAP));

// The in-island disclosure (design D7): bounded + scrollable, collapses on
// re-activation or Escape. The Escape handler is component-scoped (the
// island root), so it never steals the shell's drawer or full-log Escape.
const overflowOpen = ref(false);

function toggleOverflow() {
  overflowOpen.value = !overflowOpen.value;
}

// The focus/hover detail line: because the chip is icon-only, the label,
// duration, and modifier text are presented visibly when a chip is focused
// or hovered, so the information moved into the accessible name stays
// reachable by pointer and by keyboard.
const activeCode = ref(null);

function chipName(condition) {
  const parts = [condition.label ?? condition.code];
  if (typeof condition.remaining_seconds === "number") {
    parts.push(`剩 ${condition.remaining_seconds} 秒`);
  }
  const mods = condition.modifiers;
  if (mods && typeof mods === "object") {
    for (const [key, value] of Object.entries(mods)) {
      parts.push(`${key} ${value}`);
    }
  }
  return parts.join("，");
}

function onChipKeydown(event) {
  if (event.key === "Escape" && overflowOpen.value) {
    event.stopPropagation();
    event.preventDefault();
    overflowOpen.value = false;
  }
}
</script>

<template>
  <div
    v-if="conditions.length > 0"
    class="hud conditions"
    data-testid="status-panel__conditions"
    @keydown="onChipKeydown"
  >
    <p class="clab">狀態</p>
      <div class="chips">
        <button
          v-for="condition in visible"
          :key="condition.code"
          type="button"
          class="chip"
          :class="`chip--${condition.severity}`"
          :data-testid="`status-panel__condition--${condition.code}`"
          :data-severity="condition.severity"
          :data-code="condition.code"
          :aria-label="chipName(condition)"
          @focus="activeCode = condition.code"
          @blur="activeCode = null"
          @mouseenter="activeCode = condition.code"
          @mouseleave="activeCode = null"
        >
          <span class="glyph" aria-hidden="true">
            {{ SEVERITY_GLYPHS[condition.severity] ?? "◆" }}
          </span>
          <span
            v-if="typeof condition.remaining_seconds === 'number'"
            class="badge"
            data-testid="status-panel__condition-timer"
          >
            {{ condition.remaining_seconds }}
          </span>
        </button>
        <button
          v-if="overflowCount > 0"
          type="button"
          class="chip more"
          :class="{ open: overflowOpen }"
          data-testid="status-panel__condition-overflow"
          :aria-expanded="String(overflowOpen)"
          :aria-label="`剩餘 ${overflowCount} 個狀態`"
          @click="toggleOverflow"
        >
          +{{ overflowCount }}
        </button>
        <div
          v-if="overflowOpen && overflowCount > 0"
          class="disclosure"
          data-testid="status-panel__condition-disclosure"
        >
          <div
            v-for="condition in overflowItems"
            :key="condition.code"
            class="disclosure-row"
            :data-testid="`status-panel__condition--${condition.code}`"
            :data-severity="condition.severity"
          >
            <span class="disclosure-label">{{ condition.label ?? condition.code }}</span>
            <span v-if="typeof condition.remaining_seconds === 'number'" class="disclosure-timer">
              剩 {{ condition.remaining_seconds }} 秒
            </span>
            <span
              v-for="(value, key) in (condition.modifiers || {})"
              :key="key"
              class="disclosure-mod"
              :data-testid="`status-panel__condition-mod--${key}`"
            >
              {{ key }} {{ value }}
            </span>
          </div>
        </div>
      </div>
      <p
        v-if="activeCode"
        class="detail"
        data-testid="status-panel__condition-detail"
      >
        {{ chipName(conditions.find((c) => c.code === activeCode) || {}) }}
      </p>
  </div>
</template>

<style scoped>
/* The shared island chrome (design D1/D2.1), expressed through the shared
   design tokens only. */
.hud {
  background: var(--panel);
  backdrop-filter: blur(9px);
  -webkit-backdrop-filter: blur(9px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.conditions {
  padding: 9px 12px 11px;
  font-family: var(--f-sans);
}

.clab {
  margin: 0 0 7px;
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--paper-500);
}

.empty {
  margin: 0;
  color: var(--paper-500);
  font-size: 11px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  position: relative;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  border: 1px solid var(--ink-600);
  padding: 0;
  background: transparent;
  cursor: default;
  font-family: var(--f-mono);
}

.chip .glyph {
  font-size: 17px;
  line-height: 1;
}

.chip--beneficial {
  background: rgba(127, 191, 127, 0.14);
  border-color: rgba(127, 191, 127, 0.5);
  color: var(--buff);
}

.chip--informational {
  background: rgba(195, 185, 163, 0.1);
  border-color: var(--ink-600);
  color: var(--paper-300);
}

.chip--warning {
  background: rgba(199, 154, 74, 0.14);
  border-color: rgba(199, 154, 74, 0.55);
  color: var(--warn);
}

.chip--harmful {
  background: rgba(224, 138, 90, 0.14);
  border-color: rgba(224, 138, 90, 0.55);
  color: var(--debuff);
}

.chip--critical {
  background: rgba(224, 87, 79, 0.18);
  border-color: var(--crit);
  color: var(--crit);
}

/* The duration badge renders only when the payload supplies
   `remaining_seconds`; it shows the integer verbatim and is never counted
   down client-side between revisions. */
.chip .badge {
  position: absolute;
  bottom: -3px;
  right: -3px;
  font-family: var(--f-mono);
  font-size: 9px;
  font-weight: 700;
  background: var(--ink-900);
  border: 1px solid var(--ink-600);
  border-radius: 99px;
  padding: 0 4px;
  color: var(--paper-300);
}

/* The `+N` overflow chip opens a bounded, scrollable disclosure inside the
   island (design D7); re-activation or Escape collapses it. */
.chip.more {
  width: auto;
  min-width: 34px;
  background: var(--ink-780);
  color: var(--paper-300);
  font-size: 11px;
  padding: 0 8px;
  cursor: pointer;
}

.chip.more.open,
.chip.more:hover {
  border-color: var(--gold-500);
  color: var(--paper-50);
}

.disclosure {
  flex-basis: 100%;
  max-height: 96px;
  overflow-y: auto;
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
}

.disclosure-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  padding: 3px 0;
  font-size: 11px;
  color: var(--paper-100);
}

.disclosure-label {
  color: var(--paper-50);
  font-weight: 600;
}

.disclosure-timer {
  font-family: var(--f-mono);
  color: var(--paper-300);
}

.disclosure-mod {
  font-family: var(--f-mono);
  color: var(--paper-300);
}

/* The focus/hover detail line: the label, duration, and modifier text the
   icon-only chips move into their accessible name, kept reachable by
   pointer and keyboard. */
.detail {
  margin: 6px 0 0;
  padding: 4px 8px;
  color: var(--paper-300);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}
</style>
