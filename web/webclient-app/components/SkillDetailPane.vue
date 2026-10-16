<script setup>
// SkillDetailPane (H3 webclient-hud-03-action-dock, task 6.5): the
// draft's `.skdetail` pane — the focused skill's name, description, cost,
// target spec and disabled reason, rendered into the preserved
// `data-testid="combat-detail"` pane. No `戰鬥外` badge is rendered
// (design D14: the flag is serialized by no presenter, so the pane must not
// invent one).
//
// The pane is passive: it renders the committed focused-skill model and the
// client-local selection (the `✓` AREA marker) — it never mutates state.
//
// The `strip` variant (webclient-combat-command-card-centred D5) is the
// narrow combat card's detail: a fixed three-line strip under the rows. Its
// first line states the cost (in the 威力 step, the focused scale's cost),
// the target requirement and the element; the next two the description, or
// for a disabled skill the server-authored reason in its place, clipped with
// an ellipsis. The full text stays in the DOM, rides `title`, and is the
// focused row's accessible description (the row's `aria-describedby` names
// the strip's id). The 威力 chips are the step's own rows, so the strip
// renders no control.
import { computed, inject } from "vue";
import { elementLabel, targetSpecLabel } from "../lib/skill_labels.js";
import { DOCK_DETAIL_STRIP_ID, DOCK_DETAIL_VARIANT } from "./dock-panes.js";

const props = defineProps({
  // The focused skill model (the store's `combat.skillByKey[focusSkillKey]`):
  // `label`, `description`, `costText`, `targetSpec`, `enabled`,
  // `disabledReason`, `selected` (AREA identities).
  skill: { type: Object, default: null },
  // The client-local AREA selection (the `✓` marker source, task 6.6).
  selected: { type: Array, default: () => [] },
  // The 威力 scale step (task 6.6): the draft's `.scales` row — the
  // server-computed `mp_cost`, ascending, `1` preselected.
  scales: { type: Array, default: () => [] },
  // The chosen 威力 (the client-local selection state).
  scale: { type: Number, default: 1 },
  // "pane" (the band and drawer layout) or "strip" (the combat card); when
  // unset, the variant the hosting dock provides.
  variant: { type: String, default: null },
  // The router's focused row key: in the 威力 step (`scale-<label>`) the
  // strip states the focused scale's cost.
  focusKey: { type: String, default: null },
});

const providedVariant = inject(DOCK_DETAIL_VARIANT, null);
const isStrip = computed(() => (props.variant || providedVariant?.value || "pane") === "strip");

const emit = defineEmits(["choose-scale", "choose-shorthand"]);

const costText = computed(() => props.skill ? props.skill.costText || "" : "");
// The raw `targetSpec` / `element` identifiers stay the routing keys; the
// pane shows their readable names (webclient-zh-tw-copy-and-labels).
const targetSpec = computed(() => (props.skill && props.skill.targetSpec) || "");
const targetText = computed(() => (targetSpec.value ? targetSpecLabel(targetSpec.value) : ""));
const elementText = computed(() => (props.skill && props.skill.element ? elementLabel(props.skill.element) : ""));
const reason = computed(
  () =>
    (props.skill && props.skill.disabledReason && props.skill.disabledReason.message) || null,
);

// The scale whose cost the strip states: the focused 威力 row, else the
// chosen scale.
const stripScale = computed(() => {
  if (!props.scales.length) {
    return null;
  }
  const focused = props.scales.find((entry) => `scale-${entry.label}` === props.focusKey);
  return focused || props.scales.find((entry) => entry.scale === props.scale) || null;
});
const stripCost = computed(() => {
  const entry = stripScale.value;
  if (entry && entry.mp_cost != null) {
    return `威力×${entry.label || entry.scale} MP ${entry.mp_cost}`;
  }
  return costText.value;
});
// Every scale's cost, for the strip's full text (the step's rows show them).
const scalesText = computed(() =>
  props.scales
    .filter((entry) => entry.mp_cost != null)
    .map((entry) => `威力×${entry.label || entry.scale} MP ${entry.mp_cost}`)
    .join("、"),
);
const stripTitle = computed(() =>
  [
    props.skill?.label,
    stripCost.value,
    targetText.value && `目標類型 ${targetText.value}`,
    elementText.value,
    reason.value || props.skill?.description,
    scalesText.value,
  ]
    .filter(Boolean)
    .join(" ‧ "),
);

function onScale(entry) {
  emit("choose-scale", { scale: entry.scale });
}
</script>

<template>
  <!-- The strip (the combat card). The visually hidden name and labels keep
       the full reading in the DOM; the name is aria-hidden because the row
       it describes already names itself. -->
  <aside
    v-if="skill && isStrip"
    :id="DOCK_DETAIL_STRIP_ID"
    class="skill-detail-pane skill-detail-pane--strip"
    data-testid="combat-detail"
    aria-label="技能詳情"
    :title="stripTitle"
  >
    <span class="skill-detail-pane__sr" aria-hidden="true">{{ skill.label }}</span>
    <div class="skill-detail-pane__meta">
      <span v-if="stripCost" class="skill-detail-pane__cost"><span class="skill-detail-pane__sr">消耗</span>{{ stripCost }}</span>
      <span v-if="targetSpec" class="skill-detail-pane__target"><span class="skill-detail-pane__label skill-detail-pane__sr">目標類型</span><span>{{ targetText }}</span></span>
      <span v-if="elementText" class="skill-detail-pane__rank" :data-element="skill.element">{{ elementText }}</span>
    </div>
    <p v-if="reason" class="skill-detail-pane__disabled skill-detail-pane__body">{{ reason }}</p>
    <p v-else-if="skill.description" class="skill-detail-pane__desc skill-detail-pane__body">{{ skill.description }}</p>
    <span v-if="scalesText" class="skill-detail-pane__sr">{{ scalesText }}</span>
  </aside>
  <aside
    v-else-if="skill"
    class="skill-detail-pane"
    data-testid="combat-detail"
    aria-label="技能詳情"
  >
    <div class="skill-detail-pane__name">
      <span>{{ skill.label }}</span>
      <span v-if="elementText" class="skill-detail-pane__rank" :data-element="skill.element">{{ elementText }}</span>
    </div>
    <p v-if="skill.description" class="skill-detail-pane__desc">{{ skill.description }}</p>
    <div v-if="costText" class="skill-detail-pane__cost">
      <span class="skill-detail-pane__label">消耗</span>
      {{ costText }}
    </div>
    <div v-if="targetSpec" class="skill-detail-pane__target">
      <span class="skill-detail-pane__label">目標類型</span>
      {{ targetText }}
    </div>
    <p v-if="reason" class="skill-detail-pane__disabled">{{ reason }}</p>

    <!-- The 威力 step (task 6.6): the `.scales` row — ascending, the
         server-computed `mp_cost`, `1` preselected. No `戰鬥外` badge
         (design D14). -->
    <div v-if="scales.length" class="skill-detail-pane__scales">
      <button
        v-for="entry in scales"
        :key="entry.scale"
        type="button"
        class="skill-detail-pane__scale"
        :class="{ 'skill-detail-pane__scale--on': entry.scale === scale }"
        :aria-pressed="entry.scale === scale"
        @click="onScale(entry)"
      >
        <span>{{ entry.label || entry.scale }}</span>
        <span v-if="entry.mp_cost != null" class="skill-detail-pane__scale-cost">MP {{ entry.mp_cost }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
/* The draft's `.skdetail` pane. */
.skill-detail-pane {
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius-sm);
  padding: calc(14px * var(--ui-scale)) calc(18px * var(--ui-scale));
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  color: var(--paper-100);
  flex: 1 1 calc(260px * var(--ui-scale));
  min-width: calc(220px * var(--ui-scale));
  overflow-y: auto;
}

.skill-detail-pane__name {
  font: var(--text-xl) var(--f-serif);
  color: var(--paper-50);
  display: flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
}

.skill-detail-pane__rank {
  font-size: var(--text-xs);
  color: var(--gold-400);
  font-family: var(--f-sans);
  font-weight: 400;
}

.skill-detail-pane__desc {
  font: var(--text-md)/1.8 var(--f-serif);
  color: var(--paper-300);
  margin: calc(6px * var(--ui-scale)) 0 calc(11px * var(--ui-scale));
}

.skill-detail-pane__label {
  display: block;
  font-size: var(--text-xs);
  letter-spacing: 0.1em;
  color: var(--paper-500);
  margin-bottom: calc(6px * var(--ui-scale));
}

.skill-detail-pane__cost,
.skill-detail-pane__target {
  font-size: var(--text-md);
  color: var(--paper-300);
  margin-bottom: calc(8px * var(--ui-scale));
}

.skill-detail-pane__disabled {
  color: var(--warn);
  font-size: var(--text-xs);
  margin-top: calc(8px * var(--ui-scale));
}

.skill-detail-pane__scales {
  display: flex;
  gap: calc(6px * var(--ui-scale));
  margin-top: calc(10px * var(--ui-scale));
}

.skill-detail-pane__scale {
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

.skill-detail-pane__scale--on {
  background: var(--seal-600);
  border-color: var(--seal-500);
  color: #fff;
}

.skill-detail-pane__scale-cost {
  font-size: var(--text-xs);
  color: var(--paper-500);
}

/* The strip (webclient-combat-command-card-centred D5): three lines of
   `--text-sm` under a fine gold rule, fixed in height; the meta line never
   wraps, and the body clamps at two lines with an ellipsis. */
.skill-detail-pane.skill-detail-pane--strip {
  --strip-lh: calc(var(--text-sm) * 1.5);
  position: relative;
  flex: none;
  min-width: 0;
  box-sizing: border-box;
  height: calc(3 * var(--strip-lh) + 10px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(4px * var(--ui-scale)) calc(2px * var(--ui-scale));
  overflow: hidden;
  background: none;
  border: 0;
  border-radius: 0;
  font-size: var(--text-sm);
  line-height: var(--strip-lh);
}
.skill-detail-pane--strip::before {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 1px;
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.5), rgba(185, 154, 96, 0.12) 70%, transparent);
  pointer-events: none;
}
.skill-detail-pane__meta {
  display: flex;
  align-items: baseline;
  min-width: 0;
  height: var(--strip-lh);
  overflow: hidden;
  white-space: nowrap;
  font-family: var(--f-num);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  font-variant-numeric: tabular-nums lining-nums;
}
.skill-detail-pane__meta > * {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
  font-size: inherit;
}
.skill-detail-pane__meta > * + *::before {
  content: "‧";
  padding: 0 0.5em;
  color: var(--gold-600);
}
.skill-detail-pane--strip .skill-detail-pane__cost {
  flex: none;
  color: var(--vit-mp);
}
.skill-detail-pane--strip .skill-detail-pane__target {
  color: var(--paper-300);
}
.skill-detail-pane--strip .skill-detail-pane__rank {
  font-size: inherit;
}
.skill-detail-pane__body {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  margin: 0;
  font: var(--text-sm) / var(--strip-lh) var(--f-serif);
}
.skill-detail-pane--strip .skill-detail-pane__desc {
  color: var(--paper-300);
}
.skill-detail-pane--strip .skill-detail-pane__disabled {
  color: var(--warn);
}
/* Visually hidden, still read by innerText and assistive technology. */
.skill-detail-pane__sr {
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
