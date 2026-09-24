<script setup>
// PartyStrip (webclient-align-05-party-hud, design D1/D2/D3;
// webclient-avg-stage-hud-anchors design D3): the compact companion quickbar
// (.comps) under the vitals in the stage's `vitals` anchor. One compact cell
// per committed `party.slots` row: the avatar (portrait, or the initial glyph),
// the HP hairline beneath it, and the joined combat token (`a2`) as a badge
// on the avatar. The name, HP numerals, and bond stage are the cell's
// accessible name and tooltip; the party drawer shows them as text. No invite
// padding: inviting lives in the drawer. When empty, renders nothing.
// Activating the island or any cell opens the 同伴 · 隊伍 drawer and dispatches nothing.
import { computed } from "vue";
import {
  buildCombatTokenMap,
  hpFillRatio,
  portraitFor,
  portraitGlyph,
} from "./party-helpers.js";
import { faceObjectPosition } from "./face-rect.js";

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

const tokenById = computed(() => buildCombatTokenMap(props.combatParticipants));

function combatToken(slot) {
  if (!slot || slot.identity == null) return null;
  return tokenById.value.get(String(slot.identity)) || null;
}

function cellLabel(slot) {
  return `${slot.display_name} HP ${slot.hp_current}/${slot.hp_maximum} 羈絆 ${slot.bond_stage}`;
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
    v-if="safeSlots.length > 0"
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
        :aria-label="cellLabel(slot)"
        :title="cellLabel(slot)"
        @click.stop="onActivate"
        @keydown.enter.stop.prevent="onActivate"
        @keydown.space.stop.prevent="onActivate"
      >
        <div class="av" data-testid="party-strip__avatar">
          <img
            v-if="portraitEntry(slot)"
            class="av-img"
            :src="portraitEntry(slot).url"
            alt=""
            :style="{ objectPosition: faceObjectPosition(portraitEntry(slot).face_rect) }"
          />
          <span v-else class="av-glyph" aria-hidden="true">{{ portraitGlyph(slot.display_name) }}</span>
          <span
            v-if="combatToken(slot)"
            class="tk"
            data-testid="party-strip__token"
            aria-hidden="true"
          >{{ combatToken(slot) }}</span>
        </div>
        <div class="cbar" data-testid="party-strip__hp-bar">
          <div class="f" :style="{ width: `${hpFillRatio(slot.hp_current, slot.hp_maximum)}%` }"></div>
        </div>
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
  margin-bottom: 8px;
  display: flex;
  align-items: center;
}

.comps .clab .c {
  margin-left: auto;
  font-family: var(--f-mono);
  color: var(--paper-500);
}

/* Four tracks of at most 40px that shrink together, so a full party fits
   one row even in the 184px anchor at 1280x720 (design D3). */
.comprow {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 40px));
  gap: 6px;
}

.comp {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-radius: 8px;
}

.comp:focus-visible {
  outline: none;
}

.comp .av {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border: 1px solid var(--ink-600);
  border-radius: 8px;
  background: linear-gradient(160deg, #2a2431, #16131b);
  font-family: var(--f-display);
  font-size: 17px;
  line-height: 1;
  color: var(--gold-400);
  transition: border-color var(--motion-base, 150ms) var(--ease-standard, ease);
}

.comp:hover .av {
  border-color: var(--gold-500);
}

.comp:focus-visible .av {
  border-color: var(--gold-500);
  box-shadow: var(--focus);
}

.av-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 7px;
}

.av-glyph {
  display: inline-block;
  line-height: 1;
}

/* The joined combat token as a corner badge on the avatar. */
.comp .tk {
  position: absolute;
  top: -5px;
  right: -5px;
  padding: 1px 3px;
  border: 1px solid var(--vit-mp);
  border-radius: 4px;
  background: var(--ink-950);
  font-family: var(--f-mono);
  font-size: 9px;
  font-weight: 700;
  line-height: 1.1;
  color: var(--vit-mp);
}

.cbar {
  height: 3px;
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

/* Short viewports (webclient-avg-stage-hud-anchors design D6). */
@media (max-height: 820px) {
  .comps {
    padding: 7px 12px 9px;
  }

  .comps .clab {
    margin-bottom: 5px;
    line-height: 1.2;
  }
}
</style>
