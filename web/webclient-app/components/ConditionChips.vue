<script setup>
// ConditionChips (H2, webclient-hud-02-status-islands, design D6/D7/D8):
// the left stack's conditions island. One chip per committed condition,
// pairing a per-severity shape glyph with the condition's readable name
// (bounded by the island width, ellipsised; webclient-zh-tw-copy-and-labels)
// and the remaining duration as a small secondary badge (only when the
// payload supplies `remaining_seconds`, shown verbatim — never decremented
// between revisions). The accessible name carries the label, the duration
// and every derived modifier in readable words. Visible chips are capped at 6;
// the remainder stays reachable in one action through a bounded,
// scrollable in-island disclosure that collapses on re-activation or
// Escape (H4 re-points this control at the character-status drawer).
import { computed, ref } from "vue";
import { conditionLabel, conditionModifiers } from "../lib/condition_label.js";

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

// The focus/hover detail line: the chip shows only the (possibly
// ellipsised) name and the duration, so the full label, duration, and
// modifier text are presented visibly when a chip is focused or hovered,
// and the information in the accessible name stays reachable by pointer and
// by keyboard.
const activeCode = ref(null);

// The accessible chip name is the shared condition label rule (the same
// label, duration, and modifier prose the character-status drawer roster
// renders) — one copy in lib/condition_label.js.
const chipName = conditionLabel;

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
        <div class="chip-rows">
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
          <span class="name" aria-hidden="true">{{ condition.label ?? condition.code }}</span>
          <span
            v-if="typeof condition.remaining_seconds === 'number'"
            class="badge"
            data-testid="status-panel__condition-timer"
          >
            {{ condition.remaining_seconds }}
          </span>
        </button>
        </div>
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
      </div>
      <!-- The disclosure sits outside the chip rows so the rows' own bounded
           scroll (short viewports) never hides it. -->
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
              v-for="modifier in conditionModifiers(condition)"
              :key="modifier.key"
              class="disclosure-mod"
              :data-testid="`status-panel__condition-mod--${modifier.key}`"
            >
              {{ modifier.text }}
            </span>
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
  font-size: var(--text-xs);
  letter-spacing: 0.14em;
  color: var(--paper-500);
}

.empty {
  margin: 0;
  color: var(--paper-500);
  font-size: var(--text-xs);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* The named chips; one flow with the `+N` chip except at short viewports. */
.chip-rows {
  display: contents;
}

/* A chip is a pill: severity glyph, the readable name (bounded by the
   island width and ellipsised; the full text is in the detail line and the
   accessible name), then the duration badge. The name keeps paper ink so a
   long label stays legible on every severity tint. */
.chip {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  max-width: 100%;
  min-width: 0;
  height: 30px;
  padding: 0 9px 0 7px;
  border-radius: 7px;
  border: 1px solid var(--ink-600);
  background: transparent;
  cursor: default;
  font-family: var(--f-sans);
}

.chip .glyph {
  flex: none;
  font-size: var(--text-md);
  line-height: 1;
}

.chip .name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--text-sm);
  letter-spacing: 0.02em;
  color: var(--paper-100);
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
  flex: none;
  font-family: var(--f-num);
  font-size: var(--text-xs);
  line-height: 1;
  background: var(--ink-900);
  border: 1px solid var(--ink-600);
  border-radius: 99px;
  padding: 2px 6px;
  color: var(--paper-300);
  font-variant-numeric: tabular-nums lining-nums;
}

/* The unit is decoration on the verbatim integer (the chip's accessible
   name already says 剩 N 秒). */
.chip .badge::after {
  content: "秒";
  margin-left: 1px;
  font-family: var(--f-sans);
  font-size: 10px;
  color: var(--paper-500);
}

/* The `+N` overflow chip opens a bounded, scrollable disclosure inside the
   island (design D7); re-activation or Escape collapses it. */
.chip.more {
  min-width: 34px;
  justify-content: center;
  background: var(--ink-780);
  color: var(--paper-300);
  font-size: var(--text-xs);
  padding: 0 8px;
  cursor: pointer;
}

.chip.more.open,
.chip.more:hover {
  border-color: var(--gold-500);
  color: var(--paper-50);
}

.disclosure {
  margin-top: 6px;
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
  font-size: var(--text-xs);
  color: var(--paper-100);
}

.disclosure-label {
  color: var(--paper-50);
  font-weight: 600;
}

.disclosure-timer {
  font-family: var(--f-num);
  color: var(--paper-300);
  font-variant-numeric: tabular-nums lining-nums;
}

.disclosure-mod {
  font-family: var(--f-num);
  color: var(--paper-300);
  font-variant-numeric: tabular-nums lining-nums;
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
  font-family: var(--f-sans);
  font-size: var(--text-sm);
}

/* Short viewports (webclient-avg-stage-hud-anchors design D6): smaller
   chips and a tighter island, so the vitals stack fits its anchor. */
@media (max-height: 820px) {
  .conditions {
    padding: 7px 12px 9px;
  }

  .clab {
    margin-bottom: 4px;
    line-height: 1.2;
  }

  /* At the short viewport the named chips can wrap to more rows than the
     vitals anchor holds (at 1280x720 the island is ~160px wide), so the
     named rows scroll inside a two-row box instead of shrinking the names
     away (a focused chip scrolls itself into view), and the `+N` chip stays
     outside that box, beside it, always in sight. */
  .chips {
    flex-wrap: nowrap;
    align-items: flex-start;
    gap: 5px;
  }

  .chip-rows {
    display: flex;
    flex-wrap: wrap;
    flex: 1;
    min-width: 0;
    gap: 5px;
    max-height: 57px;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: #55524b transparent;
  }

  .chip {
    height: 26px;
    gap: 5px;
    padding: 0 7px 0 6px;
  }

  .chip .glyph {
    font-size: var(--text-sm);
  }

  .chip .name {
    font-size: var(--text-xs);
  }

  .chip.more {
    min-width: 26px;
    padding: 0 6px;
  }

  .disclosure {
    max-height: 64px;
    padding: 4px 8px;
  }

  .disclosure-row {
    padding: 1px 0;
  }
}
</style>
