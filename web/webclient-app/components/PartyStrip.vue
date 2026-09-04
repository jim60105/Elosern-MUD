<script setup>
// PartyStrip (webclient-align-05-party-hud, design D1/D2/D3):
// the left-HUD companion quickbar (.comps). Renders the committed `party.slots`
// with avatar initial fallback, display name, HP hairline bar, state row with
// joined combat token prefix `a2`, padded with dashed `+ 邀請` cells up to 4.
// Empty party renders one row of 4 dashed invite cells.
// Activating the island or any cell opens the 同伴 · 隊伍 drawer and dispatches nothing.
import { computed } from "vue";
import {
  buildCombatTokenMap,
  hpFillRatio,
  portraitFor,
  portraitGlyph,
} from "./party-helpers.js";

const props = defineProps({
  // The committed `party.slots` array.
  slots: { type: Array, default: () => [] },
  // The committed combat participants (joined by identity for combat token prefix).
  combatParticipants: { type: Array, default: () => [] },
  // The committed `art` panel (the portrait catalog source).
  artPanel: { type: Object, default: null },
});

const emit = defineEmits(["open-drawer"]);

const MAX_PARTY_SLOTS = 4;

const safeSlots = computed(() => (Array.isArray(props.slots) ? props.slots : []));
const countLabel = computed(() => `${safeSlots.value.length} / ${MAX_PARTY_SLOTS}`);
const emptyCount = computed(() => Math.max(0, MAX_PARTY_SLOTS - safeSlots.value.length));

const tokenById = computed(() => buildCombatTokenMap(props.combatParticipants));

function combatToken(slot) {
  if (!slot || slot.identity == null) return null;
  return tokenById.value.get(String(slot.identity)) || null;
}

function portraitEntry(slot) {
  return portraitFor(props.artPanel, slot.portrait_ref);
}

function onActivate() {
  emit("open-drawer");
}
</script>

<template>
  <div
    class="hud comps"
    data-testid="party-strip"
    role="region"
    aria-label="隊伍"
    tabindex="0"
    @click="onActivate"
    @keydown.enter.prevent="onActivate"
    @keydown.space.prevent="onActivate"
  >
    <div class="clab" data-testid="party-strip__header">
      同伴<span class="c" data-testid="party-strip__count">{{ countLabel }}</span>
    </div>
    <div class="comprow" data-testid="party-strip__row">
      <div
        v-for="slot in safeSlots"
        :key="slot.identity"
        class="comp"
        :data-testid="`party-strip__slot-${slot.identity}`"
        role="button"
        tabindex="0"
        :aria-label="`${slot.display_name} HP ${slot.hp_current}/${slot.hp_maximum} 羈絆 ${slot.bond_stage}`"
        @click.stop="onActivate"
        @keydown.enter.stop.prevent="onActivate"
        @keydown.space.stop.prevent="onActivate"
      >
        <div class="av" data-testid="party-strip__avatar">
          <img
            v-if="portraitEntry(slot)"
            class="av-img"
            :src="portraitEntry(slot).url"
            :alt="slot.display_name"
          />
          <span v-else class="mono av-glyph">{{ portraitGlyph(slot.display_name) }}</span>
        </div>
        <div class="nm" data-testid="party-strip__name" :title="slot.display_name">
          {{ slot.display_name }}
        </div>
        <div class="cbar" data-testid="party-strip__hp-bar">
          <div class="f" :style="{ width: `${hpFillRatio(slot.hp_current, slot.hp_maximum)}%` }"></div>
        </div>
        <div class="st" data-testid="party-strip__state">
          <span
            v-if="combatToken(slot)"
            class="tk"
            data-testid="party-strip__token"
          >{{ combatToken(slot) }}</span>
          <span class="hp-num">{{ slot.hp_current }}/{{ slot.hp_maximum }}</span>
          <span class="bond">{{ slot.bond_stage }}</span>
        </div>
      </div>

      <div
        v-for="i in emptyCount"
        :key="`empty-${i}`"
        class="comp empty"
        data-testid="party-strip__empty-slot"
        role="button"
        tabindex="0"
        aria-label="邀請同伴"
        @click.stop="onActivate"
        @keydown.enter.stop.prevent="onActivate"
        @keydown.space.stop.prevent="onActivate"
      >
        + 邀請
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Shared island chrome */
.hud {
  background: var(--panel);
  backdrop-filter: blur(9px);
  -webkit-backdrop-filter: blur(9px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.comps {
  padding: 9px 12px 11px;
  font-family: var(--f-sans);
  cursor: pointer;
  user-select: none;
}

.comps:focus-visible {
  outline: 2px solid var(--gold-500);
  outline-offset: 2px;
}

.comps .clab {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--paper-500);
  margin-bottom: 7px;
  display: flex;
  align-items: center;
}

.comps .clab .c {
  margin-left: auto;
  font-family: var(--f-mono);
  color: var(--paper-500);
}

.comprow {
  display: flex;
  gap: 8px;
}

.comp {
  flex: 1;
  min-width: 0;
  border: 1px solid var(--ink-600);
  border-radius: 9px;
  padding: 7px;
  background: rgba(34, 29, 41, 0.5);
  position: relative;
  transition: border-color var(--motion-base, 150ms) var(--ease-standard, ease);
}

.comp:hover {
  border-color: var(--gold-500);
}

.comp:focus-visible {
  outline: 2px solid var(--gold-500);
  outline-offset: 1px;
}

.comp .av {
  font-family: var(--f-display);
  font-size: 19px;
  color: var(--gold-400);
  line-height: 1;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 6px;
}

.av-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: inherit;
}

.av-glyph {
  display: inline-block;
  line-height: 1;
}

.comp .nm {
  font-size: 11px;
  color: var(--paper-100);
  margin: 3px 0 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.cbar {
  height: 5px;
  border-radius: 99px;
  background: var(--ink-780);
  overflow: hidden;
}

.cbar .f {
  height: 100%;
  background: var(--vit-hp);
  border-radius: 99px;
  transition: width var(--motion-base, 150ms) var(--ease-standard, ease);
}

.comp .st {
  font-size: 9.5px;
  color: var(--paper-500);
  margin-top: 5px;
  display: flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.comp .st .bond {
  color: var(--gold-400);
}

.comp .st .hp-num {
  font-family: var(--f-mono);
}

.comp .st .tk {
  font-family: var(--f-mono);
  color: var(--vit-mp);
  font-weight: 700;
}

.comp.empty {
  display: grid;
  place-items: center;
  border-style: dashed;
  color: var(--paper-700);
  font-size: 11px;
  cursor: pointer;
  background: transparent;
  min-height: 64px;
}

.comp.empty:hover {
  border-color: var(--gold-500);
  color: var(--paper-300);
}
</style>
