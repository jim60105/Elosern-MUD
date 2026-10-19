<script setup>
// PartyStatusTab (webclient-party-status-tab, design §6.3): the party
// window's 狀態 tab for the viewed member, in every mode. The list column is
// the hero row (portrait, name, the composed full title, and the guild
// GradeGem with merit only while the member holds a rank), the HP/MP/SP
// gauges of the committed `party` row, and one listbox of the four static
// trait rows (label, base, effective — raised totals in the buff colour,
// lowered ones in the debuff colour, each also signed with a ▲/▼ glyph) and
// the condition rows (a severity glyph whose shape differs per severity,
// label, remaining time and modifier summary). The detail column shows the
// selected trait's breakdown waterfall — base, each committed layer in
// payload order with its source bar, glyph and text label (裝備/技能/狀態),
// then the effective total — or the selected condition's source, remaining
// time and modifiers. An active disguise sits at the detail's foot with its
// displayed values labelled as displayed; every row keeps its true value.
//
// The selection is client-local: the first trait with layers is selected on
// open (or the `initialTrait` a story names), and a changed viewed member
// resets it. The `character` payload is shown only for the member it
// describes; an unavailable panel states its committed reason. The tab has
// no possession input and no combat gate: it renders the committed values
// identically while possessing and in combat.
import { computed, ref, watch } from "vue";
import AvatarArtwork from "./AvatarArtwork.vue";
import GradeGem from "./GradeGem.vue";
import ListDetail from "./ListDetail.vue";
import { glyphAttrs, glyphPath } from "./dock-icons.js";
import { portraitFor } from "./party-helpers.js";
import { gaugePercent, panelReason } from "./party-window-model.js";
import {
  INDEFINITE_TEXT,
  NO_MODIFIER_TEXT,
  TREND_GLYPHS,
  activeDisguise,
  conditionKeys,
  defaultSelection,
  formatLayerAmount,
  formatRemaining,
  fullTitle,
  guildStanding,
  layerKindLabel,
  layerSource,
  layerTrend,
  modifierSummary,
  selectionExists,
  severityOf,
  signedDelta,
  statusConditions,
  statusTraits,
  traitTrend,
} from "./party-status-model.js";

const props = defineProps({
  // The selected committed `party` v3 row (the viewed member).
  member: { type: Object, default: null },
  // The committed `character` v9 panel for the viewed member.
  character: { type: Object, default: null },
  // The committed `art` panel (the hero portrait's catalog).
  artPanel: { type: Object, default: null },
  // A trait key to select on open instead of the first layered trait.
  initialTrait: { type: String, default: null },
});

// ---------------------------------------------------------------- data

const characterReason = computed(() => panelReason(props.character));
// The payload is shown only for the member it describes; a transient
// disagreement renders no character section rather than another member's.
const detail = computed(() => {
  const panel = props.character;
  if (!props.member || !panel || panel.available !== true) return null;
  return panel.member_id === props.member.identity ? panel : null;
});
const traits = computed(() => statusTraits(detail.value));
const conditions = computed(() => statusConditions(detail.value));
// Each condition row's local key: its code, suffixed by its occurrence when
// the payload lists the same code twice (the wire does not forbid it).
const conditionRows = computed(() => conditionKeys(conditions.value));
const guild = computed(() => guildStanding(detail.value));
const title = computed(() => fullTitle(detail.value));
const disguise = computed(() => activeDisguise(detail.value));

const portrait = computed(() => (props.member ? portraitFor(props.artPanel, props.member.portrait_ref) : null));
const hasReference = computed(() => props.member?.portrait_ref !== null && props.member?.portrait_ref !== undefined);

// The vitals dock's gauge icons (VitalsTrack): a heart, a star and a bolt,
// so each gauge pairs a shape and a text label with its numbers.
const GAUGE_ICONS = Object.freeze({
  hp: "M12 21s-8-5.5-8-11a4.5 4.5 0 0 1 8-2 4.5 4.5 0 0 1 8 2c0 5.5-8 11-8 11z",
  mp: "M12 2l2.7 6.3 6.3 2.7-6.3 2.7L12 20l-2.7-6.3L3 11l6.3-2.7L12 2z",
  sp: "M13 2L4.5 13H11l-1 9L19 10h-6.5L13 2z",
});
const gauges = computed(() => {
  const row = props.member;
  if (!row) return [];
  return [
    { key: "hp", label: "HP", name: "生命", tone: "hp", icon: GAUGE_ICONS.hp, current: row.hp_current, maximum: row.hp_maximum },
    { key: "mp", label: "MP", name: "魔力", tone: "mp", icon: GAUGE_ICONS.mp, current: row.mp_current, maximum: row.mp_maximum },
    { key: "sp", label: "SP", name: "耐力", tone: "sp", icon: GAUGE_ICONS.sp, current: row.sp_current, maximum: row.sp_maximum },
  ];
});

// ---------------------------------------------------------------- selection

const selection = ref(null);
// The requested trait applies to a first selection only; a later payload
// that drops the selected row falls back to the first layered trait.
function reselect(first) {
  selection.value = defaultSelection(traits.value, conditionRows.value, first ? props.initialTrait : null);
}
watch(() => props.member?.identity ?? null, () => reselect(true), { immediate: true });
watch([traits, conditionRows], () => {
  if (!selectionExists(selection.value, traits.value, conditionRows.value)) reselect(selection.value === null);
});

const selectedTrait = computed(() =>
  selection.value?.type === "trait" ? (traits.value.find((row) => row.key === selection.value.key) ?? null) : null,
);
const selectedCondition = computed(() =>
  selection.value?.type === "condition" ? (conditionRows.value.find((row) => row.code === selection.value.key)?.condition ?? null) : null,
);
const selectedConditionKey = computed(() => (selectedCondition.value ? selection.value.key : null));
function isSelected(type, key) {
  return selection.value?.type === type && selection.value.key === key;
}
function select(type, key) {
  selection.value = { type, key };
}

// The listbox keeps one tab stop (the selected option, else the first) and
// moves focus across both groups with the arrow keys, Home and End; Enter,
// Space and click select.
const listbox = ref(null);
const tabStop = computed(() => {
  if (selectedTrait.value) return `trait:${selectedTrait.value.key}`;
  if (selectedCondition.value) return `condition:${selectedConditionKey.value}`;
  if (traits.value.length) return `trait:${traits.value[0].key}`;
  return conditionRows.value.length ? `condition:${conditionRows.value[0].code}` : null;
});
function onListKeydown(event) {
  const options = [...(listbox.value?.querySelectorAll('[role="option"]') ?? [])];
  const index = options.indexOf(document.activeElement);
  if (index === -1) return;
  let next = null;
  if (event.key === "ArrowDown") next = Math.min(index + 1, options.length - 1);
  else if (event.key === "ArrowUp") next = Math.max(index - 1, 0);
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = options.length - 1;
  if (next === null) return;
  event.preventDefault();
  options[next].focus();
}

// ---------------------------------------------------------------- display

function traitLabel(row) {
  const delta = signedDelta(row);
  return delta ? `${row.label}，基礎 ${row.base}，有效 ${row.effective}（${delta}）` : `${row.label}，基礎 ${row.base}，有效 ${row.effective}`;
}
function remainingText(condition) {
  return formatRemaining(condition.remaining_seconds);
}
function summaryText(condition) {
  return modifierSummary(condition);
}
</script>

<template>
  <div class="party-status-tab" data-testid="party-status-tab" :data-member="member ? member.identity : undefined">
    <ListDetail list-label="屬性與狀態" detail-label="狀態詳情">
      <template #rail><slot name="rail" /></template>

      <template #list>
        <template v-if="member">
          <header class="party-status-tab__hero" data-testid="party-status-tab__hero">
            <div class="party-status-tab__portrait" :class="{ 'is-down': member.knocked_out }">
              <AvatarArtwork
                :artwork="portrait"
                :panel="artPanel"
                :has-reference="hasReference"
                :name="member.display_name"
                :initial-of="member.display_name"
              />
            </div>
            <div class="party-status-tab__identity">
              <h3 class="party-status-tab__name" data-testid="party-status-tab__name">{{ member.display_name }}</h3>
              <p v-if="title" class="party-status-tab__title" data-testid="party-status-tab__title">{{ title }}</p>
              <p v-if="member.knocked_out" class="party-status-tab__down" data-testid="party-status-tab__down">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path :d="glyphPath('knocked_out')" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs('knocked_out')" />
                </svg>倒地
              </p>
            </div>
            <div v-if="guild" class="party-status-tab__guild" data-testid="party-status-tab__guild">
              <GradeGem :grade="guild.rank" size="md" :label="`公會階級 ${guild.rank}`" />
              <span class="party-status-tab__merit" data-testid="party-status-tab__merit">功績 <b>{{ guild.merit }}</b></span>
            </div>
          </header>

          <div class="party-status-tab__gauges" data-testid="party-status-tab__gauges">
            <div
              v-for="gauge in gauges"
              :key="gauge.key"
              class="party-status-tab__gauge"
              :class="`party-status-tab__gauge--${gauge.tone}`"
              :data-testid="`party-status-tab__gauge--${gauge.key}`"
            >
              <svg class="party-status-tab__gauge-icon" viewBox="0 0 24 24" aria-hidden="true"><path :d="gauge.icon" fill="currentColor" /></svg>
              <span class="party-status-tab__gauge-label" :title="gauge.name">{{ gauge.label }}</span>
              <span class="party-status-tab__track" aria-hidden="true"><i :style="{ width: `${gaugePercent(gauge.current, gauge.maximum)}%` }"></i></span>
              <span class="party-status-tab__gauge-value">{{ gauge.current }}<small> / {{ gauge.maximum }}</small></span>
            </div>
          </div>

          <p
            v-if="characterReason"
            class="party-status-tab__reason"
            data-testid="party-window__tab-unavailable"
            :data-reason-code="characterReason.code || undefined"
          >{{ characterReason.message }}</p>

          <div
            v-else-if="detail"
            ref="listbox"
            class="party-status-tab__listbox"
            role="listbox"
            aria-label="屬性與狀態"
            aria-orientation="vertical"
            data-testid="party-status-tab__listbox"
            @keydown="onListKeydown"
          >
            <div class="party-status-tab__group" role="group" aria-label="屬性">
              <div class="party-status-tab__sech" aria-hidden="true">屬性<span class="party-status-tab__sech-count">基礎 → 有效</span></div>
              <button
                v-for="row in traits"
                :key="row.key"
                type="button"
                role="option"
                class="party-status-tab__row party-status-tab__trait"
                :class="[`is-${traitTrend(row)}`, { 'is-selected': isSelected('trait', row.key) }]"
                :aria-selected="isSelected('trait', row.key) ? 'true' : 'false'"
                :aria-label="traitLabel(row)"
                :tabindex="tabStop === `trait:${row.key}` ? 0 : -1"
                :data-trend="traitTrend(row)"
                :data-testid="`party-status-tab__trait--${row.key}`"
                @click="select('trait', row.key)"
              >
                <span class="party-status-tab__row-name">{{ row.label }}<span v-if="row.layers.length" class="party-status-tab__layer-count" aria-hidden="true">{{ row.layers.length }} 層</span></span>
                <span class="party-status-tab__base" :data-testid="`party-status-tab__base--${row.key}`">{{ row.base }}</span>
                <span class="party-status-tab__arrow" aria-hidden="true">→</span>
                <span class="party-status-tab__eff" :data-testid="`party-status-tab__effective--${row.key}`">{{ row.effective }}</span>
                <span class="party-status-tab__delta" :data-testid="`party-status-tab__delta--${row.key}`"><template v-if="signedDelta(row)">{{ TREND_GLYPHS[traitTrend(row)] }} {{ signedDelta(row) }}</template></span>
              </button>
            </div>

            <div v-if="conditionRows.length" class="party-status-tab__group" role="group" aria-label="狀態">
              <div class="party-status-tab__sech" aria-hidden="true">狀態<span class="party-status-tab__sech-count">{{ conditionRows.length }}</span></div>
              <button
                v-for="{ code: rowKey, condition } in conditionRows"
                :key="rowKey"
                type="button"
                role="option"
                class="party-status-tab__row party-status-tab__condition"
                :class="{ 'is-selected': isSelected('condition', rowKey) }"
                :aria-selected="isSelected('condition', rowKey) ? 'true' : 'false'"
                :tabindex="tabStop === `condition:${rowKey}` ? 0 : -1"
                :data-severity="condition.severity"
                :data-testid="`party-status-tab__condition--${rowKey}`"
                @click="select('condition', rowKey)"
              >
                <span class="party-status-tab__sev" :class="`party-status-tab__sev--${condition.severity}`" aria-hidden="true">{{ severityOf(condition).glyph }}</span>
                <span class="party-status-tab__row-name">
                  <span class="visually-hidden">{{ severityOf(condition).word }}，</span>{{ condition.label }}
                  <span v-if="remainingText(condition)" class="party-status-tab__row-sub" :data-testid="`party-status-tab__remaining--${condition.code}`">{{ condition.remaining_seconds === null ? INDEFINITE_TEXT : `剩 ${remainingText(condition)}` }}</span>
                </span>
                <span class="party-status-tab__row-end" :data-testid="`party-status-tab__modifiers--${condition.code}`">{{ summaryText(condition) }}</span>
              </button>
            </div>
          </div>
          <template v-if="detail && !conditionRows.length">
            <h4 class="party-status-tab__sech">狀態<span class="party-status-tab__sech-count">0</span></h4>
            <p class="party-status-tab__empty" data-testid="party-status-tab__no-conditions">無</p>
          </template>
        </template>
      </template>

      <template #detail>
        <template v-if="selectedTrait">
          <span class="party-status-tab__ribbon">屬性</span>
          <h3 class="party-status-tab__detail-title" data-testid="party-status-tab__detail-title">{{ selectedTrait.label }} <b :class="`is-${traitTrend(selectedTrait)}`">{{ selectedTrait.effective }}</b></h3>
          <ol class="party-status-tab__fall" aria-label="數值組成" data-testid="party-status-tab__waterfall">
            <li class="party-status-tab__step party-status-tab__step--base" data-testid="party-status-tab__step--base">
              <span class="party-status-tab__step-glyph" aria-hidden="true"></span>
              <span class="party-status-tab__step-name">基礎值</span>
              <span class="party-status-tab__amt">{{ selectedTrait.base }}</span>
            </li>
            <li
              v-for="(layer, index) in selectedTrait.layers"
              :key="index"
              class="party-status-tab__step"
              :class="`party-status-tab__step--${layerSource(layer).tone}`"
              :data-source="layer.source"
              :data-testid="`party-status-tab__layer--${index}`"
            >
              <span class="party-status-tab__step-glyph" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none"><path :d="glyphPath(layerSource(layer).glyph)" stroke="currentColor" stroke-width="1.6" v-bind="glyphAttrs(layerSource(layer).glyph)" /></svg>
              </span>
              <span class="party-status-tab__step-name">{{ layer.name }}<small :data-testid="`party-status-tab__layer-source--${index}`">{{ layerSource(layer).label }} ‧ {{ layerKindLabel(layer) }}</small></span>
              <span class="party-status-tab__amt" :class="`is-${layerTrend(layer)}`" :data-testid="`party-status-tab__layer-amount--${index}`">{{ formatLayerAmount(layer.kind, layer.amount) }}</span>
            </li>
            <li class="party-status-tab__step party-status-tab__step--total" data-testid="party-status-tab__step--total">
              <span class="party-status-tab__step-glyph" aria-hidden="true"></span>
              <span class="party-status-tab__step-name">有效值</span>
              <span class="party-status-tab__amt">{{ selectedTrait.effective }}</span>
            </li>
          </ol>
        </template>

        <template v-else-if="selectedCondition">
          <span class="party-status-tab__ribbon" :class="`party-status-tab__ribbon--${selectedCondition.severity}`" data-testid="party-status-tab__severity">
            <span aria-hidden="true">{{ severityOf(selectedCondition).glyph }}</span>{{ severityOf(selectedCondition).word }}
          </span>
          <h3 class="party-status-tab__detail-title" data-testid="party-status-tab__detail-title">{{ selectedCondition.label }}</h3>
          <dl class="party-status-tab__facts" data-testid="party-status-tab__condition-detail">
            <div class="party-status-tab__fact"><dt>來源</dt><dd data-testid="party-status-tab__fact--source">{{ selectedCondition.source }}</dd></div>
            <div class="party-status-tab__fact"><dt>剩餘</dt><dd data-testid="party-status-tab__fact--remaining">{{ remainingText(selectedCondition) || "—" }}</dd></div>
            <div class="party-status-tab__fact"><dt>修正</dt><dd data-testid="party-status-tab__fact--modifiers">{{ summaryText(selectedCondition) || NO_MODIFIER_TEXT }}</dd></div>
          </dl>
        </template>
      </template>

      <template v-if="disguise" #actions>
        <aside class="party-status-tab__disguise" aria-label="偽裝" data-testid="party-status-tab__disguise">
          <p class="party-status-tab__disguise-head"><b>偽裝中</b><span data-testid="party-status-tab__disguise-description">{{ disguise.description }}</span></p>
          <p v-if="disguise.displayed.length" class="party-status-tab__disguise-shown" data-testid="party-status-tab__disguise-displayed">
            對外顯示：<template v-for="(row, index) in disguise.displayed" :key="row.key">{{ index ? "、" : "" }}<span :data-testid="`party-status-tab__displayed--${row.key}`">{{ row.label }} {{ row.value }}</span></template>
          </p>
        </aside>
      </template>
    </ListDetail>
  </div>
</template>

<style scoped>
/* The approved prototype's 狀態 tab (docs/design/party-member-management/
   tabs/StatusTab.vue and prototype.css `.pm-sech`, `.pm-row`, `.pm-gauge`,
   `.pm-ribbon`, `.pm-facts`). Raised and lowered values carry a ▲/▼ glyph
   and a sign besides their colour; the waterfall's source carries a glyph
   and a text label besides its bar colour. */
.party-status-tab {
  --party-status-line: rgba(185, 154, 96, 0.28);
  --party-status-line-soft: rgba(185, 154, 96, 0.14);
  --party-status-src-equipment: #c9a46a;
  --party-status-src-skill: #8fa8e0;
  --party-status-src-condition: #b98be0;
  display: flex;
  flex: 1;
  min-width: 0;
  min-height: 0;
  height: 100%;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

/* ── hero ─────────────────────────────────────────────────────── */
.party-status-tab__hero {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: var(--sp-3);
  align-items: center;
  padding-bottom: var(--sp-3);
  margin-bottom: var(--sp-3);
  border-bottom: calc(1px * var(--ui-scale)) solid var(--party-status-line);
}

.party-status-tab__portrait {
  position: relative;
  width: calc(58px * var(--ui-scale));
  height: calc(58px * var(--ui-scale));
  overflow: hidden;
  background: radial-gradient(circle at 50% 30%, #3a332a, #16181c);
  border: calc(1px * var(--ui-scale)) solid var(--gold-600);
  border-radius: 50%;
  box-shadow: 0 0 0 calc(3px * var(--ui-scale)) rgba(0, 0, 0, 0.35), 0 0 calc(12px * var(--ui-scale)) rgba(228, 200, 142, 0.12);
}

.party-status-tab__portrait :deep(.avatar-artwork) {
  position: absolute;
  inset: 0;
}

.party-status-tab__portrait :deep(.avatar-artwork__initial) {
  color: var(--gold-300);
  font-family: var(--f-display);
  font-size: var(--text-2xl);
}

.party-status-tab__portrait.is-down {
  filter: grayscale(0.8) brightness(0.6);
}

.party-status-tab__identity {
  min-width: 0;
}

.party-status-tab__name {
  margin: 0;
  overflow: hidden;
  color: var(--paper-50);
  font: var(--text-xl) var(--f-display);
  letter-spacing: 0.04em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.party-status-tab__title {
  margin: calc(2px * var(--ui-scale)) 0 0;
  overflow: hidden;
  color: var(--gold-400);
  font-size: var(--text-xs);
  letter-spacing: 0.06em;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.party-status-tab__down {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  margin: calc(2px * var(--ui-scale)) 0 0;
  color: var(--seal-400);
  font-size: var(--text-xs);
}

.party-status-tab__down svg {
  width: 1em;
  height: 1em;
}

.party-status-tab__guild {
  display: grid;
  justify-items: center;
  gap: calc(2px * var(--ui-scale));
  color: var(--paper-500);
  font-size: var(--text-xs);
}

.party-status-tab__merit b {
  color: var(--paper-100);
  font: 500 var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

/* ── gauges ───────────────────────────────────────────────────── */
.party-status-tab__gauges {
  display: grid;
  gap: calc(6px * var(--ui-scale));
}

.party-status-tab__gauge {
  display: grid;
  grid-template-columns: calc(14px * var(--ui-scale)) calc(26px * var(--ui-scale)) 1fr auto;
  gap: var(--sp-2);
  align-items: center;
  font-size: var(--text-xs);
}

.party-status-tab__gauge-icon {
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
  color: var(--gauge);
  filter: drop-shadow(0 0 calc(4px * var(--ui-scale)) color-mix(in srgb, var(--gauge) 45%, transparent));
}

.party-status-tab__gauge--hp { --gauge: var(--vit-hp); }
.party-status-tab__gauge--mp { --gauge: var(--vit-mp); }
.party-status-tab__gauge--sp { --gauge: var(--vit-sp); }

.party-status-tab__gauge-label {
  color: var(--gauge);
  font: 600 var(--text-xs) var(--f-num);
  letter-spacing: 0.06em;
}

.party-status-tab__track {
  height: calc(6px * var(--ui-scale));
  overflow: hidden;
  background: #25272b;
  border-radius: calc(3px * var(--ui-scale));
  box-shadow: inset 0 calc(1px * var(--ui-scale)) calc(2px * var(--ui-scale)) rgba(0, 0, 0, 0.5);
}

.party-status-tab__track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, color-mix(in srgb, var(--gauge) 70%, #000), var(--gauge));
  border-radius: inherit;
}

.party-status-tab__gauge-value {
  min-width: calc(72px * var(--ui-scale));
  color: var(--paper-100);
  font: var(--text-sm) var(--f-num);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.party-status-tab__gauge-value small {
  color: var(--paper-500);
  font-size: var(--text-xs);
}

.party-status-tab__reason {
  margin: var(--sp-4) 0 0;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

/* ── list ─────────────────────────────────────────────────────── */
.party-status-tab__sech {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin: var(--sp-5) 0 var(--sp-2);
  color: var(--gold-300);
  font: 400 var(--text-base) var(--f-display);
  letter-spacing: 0.06em;
}

.party-status-tab__sech::after {
  content: "";
  flex: 1;
  height: calc(1px * var(--ui-scale));
  background: linear-gradient(90deg, var(--party-status-line), transparent);
}

.party-status-tab__sech-count {
  order: 3;
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  letter-spacing: 0;
}

.party-status-tab__group {
  display: flex;
  flex-direction: column;
}

.party-status-tab__row {
  display: grid;
  gap: var(--sp-3);
  align-items: center;
  width: 100%;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-100);
  font: var(--text-sm) var(--f-sans);
  text-align: left;
  background: transparent;
  border: calc(1px * var(--ui-scale)) solid transparent;
  border-bottom: calc(1px * var(--ui-scale)) dashed var(--party-status-line-soft);
  border-radius: 0;
  cursor: pointer;
  transition: background-color var(--motion-fast) ease, border-color var(--motion-fast) ease;
}

.party-status-tab__row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.party-status-tab__row:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}

.party-status-tab__row.is-selected {
  background: linear-gradient(90deg, rgba(207, 68, 68, 0.22), rgba(228, 200, 142, 0.06));
  border: calc(1px * var(--ui-scale)) solid var(--seal-700);
  border-radius: var(--radius-sm);
  box-shadow: inset calc(3px * var(--ui-scale)) 0 0 var(--seal-500);
}

.party-status-tab__row-name {
  min-width: 0;
  overflow: hidden;
  font-family: var(--f-serif);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.party-status-tab__row-sub {
  display: block;
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
}

.party-status-tab__row-end {
  max-width: calc(170px * var(--ui-scale));
  overflow: hidden;
  color: var(--paper-400);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums;
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.party-status-tab__trait {
  grid-template-columns: minmax(0, 1fr) auto auto minmax(calc(40px * var(--ui-scale)), auto) calc(58px * var(--ui-scale));
  gap: var(--sp-2);
}

.party-status-tab__layer-count {
  margin-left: var(--sp-2);
  color: var(--paper-700);
  font: var(--text-xs) var(--f-sans);
}

.party-status-tab__base {
  color: var(--paper-500);
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.party-status-tab__arrow {
  color: var(--paper-700);
  font-size: var(--text-xs);
}

.party-status-tab__eff {
  color: var(--paper-50);
  font: 600 var(--text-lg) var(--f-num);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.party-status-tab__delta {
  font: var(--text-xs) var(--f-num);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.party-status-tab__trait.is-up .party-status-tab__eff,
.party-status-tab__trait.is-up .party-status-tab__delta { color: var(--buff); }
.party-status-tab__trait.is-down .party-status-tab__eff,
.party-status-tab__trait.is-down .party-status-tab__delta { color: var(--debuff); }

.party-status-tab__condition {
  grid-template-columns: auto minmax(0, 1fr) auto;
}

/* Each severity has its own glyph and a badge shape: a circle for a
   benefit, a square for the rest. */
.party-status-tab__sev {
  display: grid;
  place-items: center;
  width: calc(26px * var(--ui-scale));
  height: calc(26px * var(--ui-scale));
  color: var(--sev);
  font-size: var(--text-sm);
  line-height: 1;
  background: color-mix(in srgb, var(--sev) 12%, transparent);
  border: calc(1px * var(--ui-scale)) solid var(--sev);
  border-radius: calc(3px * var(--ui-scale));
}

.party-status-tab__sev--beneficial { --sev: var(--buff); border-radius: 50%; }
.party-status-tab__sev--informational { --sev: var(--paper-300); }
.party-status-tab__sev--warning { --sev: var(--warn); }
.party-status-tab__sev--harmful { --sev: var(--debuff); }
.party-status-tab__sev--critical { --sev: var(--crit); font-weight: 700; }

.party-status-tab__empty {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-700);
}

/* ── detail ───────────────────────────────────────────────────── */
.party-status-tab__ribbon {
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

.party-status-tab__detail-title {
  margin: 0;
  color: var(--paper-50);
  font: var(--text-3xl) var(--f-display);
  letter-spacing: 0.04em;
}

.party-status-tab__detail-title b {
  margin-left: var(--sp-2);
  font: 600 var(--text-3xl) var(--f-num);
  font-variant-numeric: tabular-nums;
}

.party-status-tab__detail-title b.is-up { color: var(--buff); }
.party-status-tab__detail-title b.is-down { color: var(--debuff); }

.party-status-tab__fall {
  display: grid;
  gap: var(--sp-1);
  margin: var(--sp-4) 0 0;
  padding: 0;
  list-style: none;
}

.party-status-tab__step {
  --src: var(--ink-600);
  display: grid;
  grid-template-columns: calc(20px * var(--ui-scale)) minmax(0, 1fr) auto;
  gap: var(--sp-3);
  align-items: center;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-200);
  background: linear-gradient(90deg, color-mix(in srgb, var(--src) 10%, rgba(0, 0, 0, 0.2)), rgba(0, 0, 0, 0.2) 45%);
  border-left: calc(3px * var(--ui-scale)) solid var(--src);
  border-radius: var(--radius-sm);
}

.party-status-tab__step-glyph {
  display: grid;
  place-items: center;
  color: var(--src);
}

.party-status-tab__step-glyph svg {
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
}

.party-status-tab__step-name {
  min-width: 0;
  font-family: var(--f-serif);
}

.party-status-tab__step-name small {
  margin-left: var(--sp-2);
  color: var(--paper-500);
  font: var(--text-xs) var(--f-sans);
  letter-spacing: 0.04em;
}

.party-status-tab__step--equipment { --src: var(--party-status-src-equipment); color: var(--paper-100); }
.party-status-tab__step--skill { --src: var(--party-status-src-skill); }
.party-status-tab__step--condition { --src: var(--party-status-src-condition); }
.party-status-tab__step--other { --src: var(--paper-500); }

.party-status-tab__step--base {
  color: var(--paper-300);
}

.party-status-tab__step--total {
  --src: var(--seal-500);
  margin-top: var(--sp-1);
  color: var(--paper-50);
  font-weight: 600;
  background: linear-gradient(90deg, rgba(207, 68, 68, 0.16), rgba(207, 68, 68, 0.04));
}

.party-status-tab__amt {
  font: var(--text-md) var(--f-num);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.party-status-tab__amt.is-up { color: var(--buff); }
.party-status-tab__amt.is-down { color: var(--debuff); }

.party-status-tab__step--total .party-status-tab__amt {
  color: var(--paper-50);
  font-size: var(--text-xl);
}

.party-status-tab__ribbon--beneficial { background: color-mix(in srgb, var(--buff) 45%, var(--ink-900, #121418)); }
.party-status-tab__ribbon--warning { background: color-mix(in srgb, var(--warn) 45%, var(--ink-900, #121418)); }
.party-status-tab__ribbon--informational { background: var(--ink-600); }

.party-status-tab__facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--sp-2);
  margin: var(--sp-4) 0 0;
}

.party-status-tab__fact {
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-500);
  font-size: var(--text-xs);
  border: calc(1px * var(--ui-scale)) solid var(--party-status-line);
  border-radius: var(--radius-sm);
}

.party-status-tab__fact dt {
  letter-spacing: 0.1em;
}

.party-status-tab__fact dd {
  margin: calc(2px * var(--ui-scale)) 0 0;
  color: var(--paper-50);
  font: 500 var(--text-sm) var(--f-sans);
  overflow-wrap: anywhere;
}

/* The disguise sits at the detail's foot, outside its scroll region. */
.party-status-tab__disguise {
  margin-top: var(--sp-3);
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-400);
  font-size: var(--text-xs);
  line-height: 1.7;
  background: rgba(185, 154, 96, 0.04);
  border: calc(1px * var(--ui-scale)) dashed var(--gold-600);
  border-radius: var(--radius-sm);
}

.party-status-tab__disguise p {
  margin: 0;
}

.party-status-tab__disguise b {
  margin-right: var(--sp-2);
  color: var(--gold-300);
  font-weight: 500;
}
</style>
