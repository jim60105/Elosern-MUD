<script setup>
// PartyMedallions (OpenSpec change wilderness-travel-interface, design §8):
// the present party in travel, below the vitals dock in the `vitals` anchor,
// in place of the standing lineup. Each member is a round face crop
// (AvatarArtwork over the committed portrait descriptor, never a built URL)
// with its name, its own supplied 精力 reserve as a bar notched at 70 / 40 /
// 20 %, the supplied stage label when the stage is not the normal one, and a
// crescent while asleep. The controlled body is ringed.
//
// Every value is the member's own committed fatigue row
// (components/travel/travel-model.js `medallionMembers`); nothing here
// derives a stage or a percent. Colour is never the only cue: stages also
// lower the face's saturation and brightness and carry their label, sleep
// carries its crescent shape, and the controlled ring is a second rim. A
// member whose row is missing reads unavailable, never full.
import { computed } from "vue";
import AvatarArtwork from "../AvatarArtwork.vue";
import { RESERVE_NOTCHES, medallionLabel } from "./travel-model.js";

const props = defineProps({
  // `medallionMembers(...)` output, in display order.
  members: { type: Array, default: () => [] },
});

const rows = computed(() =>
  props.members.map((member) => ({
    ...member,
    accessibleName: medallionLabel(member),
    showStage: member.available && member.stage !== null && member.stage !== "normal",
    fill: member.available ? Math.max(0, Math.min(100, member.reserve)) : 0,
  })),
);
</script>

<template>
  <ul class="party-medallions" aria-label="隊伍" data-testid="party-medallions">
    <li
      v-for="m in rows"
      :key="m.key"
      class="party-medallion"
      :class="{
        'is-controlled': m.controlled,
        'is-asleep': m.asleep,
        'is-unavailable': !m.available,
      }"
      data-testid="party-medallion"
      :data-identity="m.key"
      :data-stage="m.stage"
      :data-asleep="m.asleep ? 'true' : 'false'"
      :data-controlled="m.controlled ? 'true' : 'false'"
      :aria-label="m.accessibleName"
    >
      <span class="party-medallion__ring" aria-hidden="true">
        <span class="party-medallion__face">
          <AvatarArtwork
            :artwork="m.artwork"
            :panel="m.panel"
            :has-reference="m.hasReference"
            :name="m.name"
            :failure-text-id="`party-medallion-${m.key}-failure`"
          />
        </span>
        <span v-if="m.asleep" class="party-medallion__moon" data-testid="party-medallion__moon"></span>
      </span>
      <span class="party-medallion__name" aria-hidden="true">{{ m.name }}</span>
      <span
        class="party-medallion__bar"
        aria-hidden="true"
        data-testid="party-medallion__bar"
        :data-reserve="m.available ? m.reserve : null"
      >
        <span v-if="m.available" class="party-medallion__fill" :style="{ width: `${m.fill}%` }"></span>
        <i v-for="notch in RESERVE_NOTCHES" :key="notch" class="party-medallion__notch" :style="{ left: `${notch}%` }"></i>
      </span>
      <span v-if="m.showStage" class="party-medallion__stage" aria-hidden="true">{{ m.label }}</span>
      <span v-else-if="!m.available" class="party-medallion__stage party-medallion__stage--missing" aria-hidden="true">無資料</span>
    </li>
  </ul>
</template>

<style>
/* The strip: the dock's own feathered ink, so the medallions read as part of
   the same instrument column instead of a second box. */
.party-medallions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: calc(10px * var(--ui-scale)) calc(8px * var(--ui-scale));
  margin: 0;
  padding: calc(12px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(10px * var(--ui-scale));
  list-style: none;
  /* Dense where the faces stand, thinning towards the top and right edge,
     so map chips passing under the strip never compete with a name. */
  background: radial-gradient(150% 170% at 22% 100%, rgba(11, 13, 16, 0.95), rgba(11, 13, 16, 0.72) 52%, rgba(11, 13, 16, 0) 86%);
  backdrop-filter: blur(3px);
  -webkit-mask-image: radial-gradient(135% 150% at 24% 100%, #000 62%, transparent 98%);
  mask-image: radial-gradient(135% 150% at 24% 100%, #000 62%, transparent 98%);
}
.party-medallion {
  display: grid;
  justify-items: center;
  gap: calc(4px * var(--ui-scale));
  width: calc(64px * var(--ui-scale));
}
.party-medallion__ring {
  position: relative;
  display: block;
  width: calc(54px * var(--ui-scale));
  height: calc(54px * var(--ui-scale));
  padding: calc(2px * var(--ui-scale));
  border-radius: 50%;
  background: linear-gradient(160deg, var(--gold-400), var(--gold-600) 60%, rgba(143, 113, 60, 0.6));
  box-shadow: 0 0 0 calc(2px * var(--ui-scale)) var(--ink-950), 0 calc(6px * var(--ui-scale)) calc(16px * var(--ui-scale)) rgba(0, 0, 0, 0.55);
  box-sizing: border-box;
}
/* The controlled body: a brighter rim and a second, outer hairline. */
.party-medallion.is-controlled .party-medallion__ring {
  background: linear-gradient(160deg, var(--paper-50), var(--gold-300) 45%, var(--gold-500));
  box-shadow:
    0 0 0 calc(2px * var(--ui-scale)) var(--ink-950),
    0 0 0 calc(3.5px * var(--ui-scale)) rgba(228, 200, 142, 0.7),
    0 0 calc(14px * var(--ui-scale)) var(--gold-glow),
    0 calc(6px * var(--ui-scale)) calc(16px * var(--ui-scale)) rgba(0, 0, 0, 0.55);
}
.party-medallion__face {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  overflow: hidden;
  background: var(--ink-800);
  transition: filter var(--motion-base) var(--ease-standard);
}
/* Stages lower saturation and brightness, so the face itself shows the
   weariness the label names. */
.party-medallion[data-stage="light"] .party-medallion__face { filter: saturate(0.82); }
.party-medallion[data-stage="moderate"] .party-medallion__face { filter: saturate(0.6) brightness(0.88); }
.party-medallion[data-stage="severe"] .party-medallion__face,
.party-medallion.is-asleep .party-medallion__face { filter: saturate(0.35) brightness(0.72); }
.party-medallion.is-unavailable .party-medallion__face { filter: grayscale(1) brightness(0.6); }
/* The crescent: a moon cut by the ink, on the rim's upper right. */
.party-medallion__moon {
  position: absolute;
  right: calc(-5px * var(--ui-scale));
  top: calc(-5px * var(--ui-scale));
  width: calc(21px * var(--ui-scale));
  height: calc(21px * var(--ui-scale));
  border-radius: 50%;
  background: radial-gradient(circle at 66% 38%, var(--ink-900) 46%, transparent 47.5%), #cdd7ee;
  box-shadow: 0 0 0 calc(2px * var(--ui-scale)) var(--ink-950), 0 0 calc(12px * var(--ui-scale)) rgba(170, 190, 230, 0.5);
}
.party-medallion__name {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font: var(--text-xs)/1.2 var(--f-serif);
  color: var(--paper-50);
  text-shadow: 0 1px 3px #000;
}
.party-medallion.is-controlled .party-medallion__name {
  color: var(--gold-300);
}
.party-medallion__bar {
  position: relative;
  width: 100%;
  height: calc(5px * var(--ui-scale));
  border-radius: var(--radius-pill);
  background: rgba(36, 38, 42, 0.95);
  overflow: hidden;
  box-shadow: inset 0 0 0 1px rgba(58, 56, 51, 0.9);
}
.party-medallion__fill {
  position: absolute;
  inset: 0 auto 0 0;
  background: linear-gradient(90deg, #a98432, var(--vit-sp));
  transition: width var(--motion-slow) var(--ease-standard);
}
.party-medallion[data-stage="light"] .party-medallion__fill { background: var(--warn); }
.party-medallion[data-stage="moderate"] .party-medallion__fill,
.party-medallion[data-stage="severe"] .party-medallion__fill,
.party-medallion[data-stage="forced_sleep"] .party-medallion__fill { background: var(--crit); }
.party-medallion__notch {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(11, 13, 16, 0.9);
}
.party-medallion__stage {
  max-width: calc(80px * var(--ui-scale));
  font: var(--text-xs)/1.1 var(--f-sans);
  color: var(--warn);
  white-space: nowrap;
  text-shadow: 0 1px 3px #000;
}
.party-medallion[data-stage="moderate"] .party-medallion__stage,
.party-medallion[data-stage="severe"] .party-medallion__stage,
.party-medallion[data-stage="forced_sleep"] .party-medallion__stage { color: #e8957a; }
.party-medallion[data-stage="sleeping"] .party-medallion__stage { color: #c3cde6; }
.party-medallion__stage--missing { color: var(--paper-400); }
</style>
