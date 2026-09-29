<script setup>
// Display-only, server-ordered combat identities. Playback substitutes only
// the HP numerator addressed by the participant's catalog reference.
import { computed } from "vue";
import { faceObjectPosition } from "./face-rect.js";
import { portraitGlyph } from "./character-identity.js";
import { gaugeRatio } from "./vitals.js";

const props = defineProps({
  participants: { type: Array, default: () => [] },
  artPanel: { type: Object, default: null },
  displayHp: { type: Object, default: null },
});
const groups = computed(() => [
  { team: "party", label: "我方", rows: props.participants.filter((p) => p.team === "party") },
  { team: "foes", label: "敵方", rows: props.participants.filter((p) => p.team === "foes") },
]);
function hpCurrent(p) {
  const displayed = p.portrait_ref == null ? undefined : props.displayHp?.[p.portrait_ref];
  return typeof displayed === "number" ? displayed : p.hp_current;
}
function hpWidth(p) {
  return `${gaugeRatio({ current: hpCurrent(p), maximum: p.hp_maximum })}%`;
}
const STATE_MARKERS = { fled: "已逃離", knocked_out: "倒地", defeated: "已敗退" };
function portraitFor(p) {
  if (p.portrait_ref == null || !props.artPanel || props.artPanel.available === false) return null;
  return props.artPanel.portrait_catalog?.[p.portrait_ref] || { placeholder: true };
}
function portraitLabel(p) {
  const portrait = portraitFor(p);
  const state = { pending: "肖像生成中", failed: "肖像生成失敗", missing: "無肖像" }[portrait?.status];
  return `${p.display_name}，${state || portrait?.placeholder?.label || "無肖像"}`;
}
</script>

<template>
  <div class="participant-frame" data-testid="participant-frame">
    <template v-for="group in groups" :key="group.team">
      <div v-if="group.rows.length" class="participant-frame__group">
        <div class="participant-frame__group-label">{{ group.label }}</div>
        <div v-for="p in group.rows" :key="p.identity" class="participant-frame__row"
          :class="{ 'participant-frame__row--muted': p.state !== 'active' }">
          <span class="participant-frame__token"
            :class="group.team === 'party' ? 'participant-frame__token--ally' : 'participant-frame__token--foe'">{{ p.token }}</span>
          <span class="participant-frame__name" :title="p.display_name">{{ p.display_name }}</span>
          <span class="participant-frame__hp">{{ hpCurrent(p) }}/{{ p.hp_maximum }}</span>
          <span v-if="p.state !== 'active'" class="participant-frame__state">{{ STATE_MARKERS[p.state] || "未知狀態" }}</span>
          <template v-if="portraitFor(p)">
            <img v-if="portraitFor(p).url" class="participant-frame__portrait"
              :src="portraitFor(p).url" :alt="p.display_name"
              :style="{ objectPosition: faceObjectPosition(portraitFor(p).face_rect) }" />
            <span v-else class="participant-frame__portrait-placeholder" data-testid="participant-portrait-placeholder"
              role="img" :aria-label="portraitLabel(p)" :title="portraitLabel(p)">{{ portraitGlyph(p.display_name) }}</span>
          </template>
          <span class="participant-frame__hairline" aria-hidden="true"><span :style="{ width: hpWidth(p) }"></span></span>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.participant-frame {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  font-family: var(--f-sans);
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: thin;
}
.participant-frame__group { display: flex; flex-direction: column; gap: 3px; }
.participant-frame__group-label { color: var(--gold-400); font-size: var(--text-xs); }
.participant-frame__row {
  position: relative;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) 28px;
  gap: 0 6px;
  align-items: center;
  padding: 3px 4px 5px;
  border-radius: var(--radius-sm);
  background: #1b1d2150;
}
.participant-frame__row--muted { opacity: 0.7; }
.participant-frame__token {
  grid-column: 1; grid-row: 1 / 3;
  display: grid; place-items: center;
  width: 28px; height: 28px;
  font: var(--text-xs) var(--f-mono);
  border: 1px solid var(--ink-600); border-radius: 5px;
  box-sizing: border-box;
}
.participant-frame__token--ally { color: var(--vit-mp); }
.participant-frame__token--foe { color: var(--seal-400); }
.participant-frame__name {
  grid-column: 2; grid-row: 1; min-width: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  font: var(--text-sm)/1.2 var(--f-serif); color: var(--paper-50);
}
.participant-frame__hp {
  grid-column: 2; grid-row: 2;
  font: var(--text-xs)/1.2 var(--f-num); color: var(--paper-300);
  font-variant-numeric: tabular-nums lining-nums;
}
.participant-frame__state { grid-column: 2 / 4; color: var(--warn); font-size: var(--text-xs); }
.participant-frame__portrait, .participant-frame__portrait-placeholder {
  grid-column: 3; grid-row: 1 / 3;
  width: 28px; height: 28px; box-sizing: border-box;
  border: 1px solid var(--ink-600); border-radius: 5px;
  object-fit: cover;
}
.participant-frame__portrait-placeholder {
  display: grid; place-items: center;
  background: var(--ink-780); color: var(--paper-300); font-size: var(--text-sm);
}
.participant-frame__hairline { position: absolute; bottom: 1px; left: 38px; right: 4px; height: 2px; background: var(--ink-600); }
.participant-frame__hairline > span { display: block; height: 100%; background: var(--vit-hp); }
</style>
