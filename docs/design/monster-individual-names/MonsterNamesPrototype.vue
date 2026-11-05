<script setup>
// Design/MonsterIndividualNames: how a monster's name, its variant, and a
// boss's individual name read on the stage (reference only, synthetic data;
// not imported by the app). PresenceRail and FigurePlate are the real
// components. The named treatment is applied here by selector, standing in
// for the production `data-named` attribute. The readout and the target prompt
// are local copies of their markup, because the tag does not exist in them yet.
//
// The treatment reads as rank, not selection: GuildRankCard's inner double rule
// on the medallion, and two fading gold hairlines around the name. Every rule
// takes no layout space and the name keeps the ordinary font size, line height
// and spacing, so no named box differs from an unnamed one.
import { computed, ref } from "vue";
import FigurePlate from "../../../web/webclient-app/components/FigurePlate.vue";
import PresenceRail from "../../../web/webclient-app/components/PresenceRail.vue";
import {
  ART_PANEL,
  FOES,
  LONG_NAMED,
  NAMED_IDENTITY,
  RAIL_ENTRIES,
  monsterDetailTag,
  monsterName,
} from "./monster-names-fixtures.js";

const props = defineProps({
  // exploration | combat | specimen
  view: { type: String, default: "exploration" },
});

// Bound, so the Vue template compiler leaves this served path alone.
const FIGURE_ART = "/art/defaults/monster_anon.webp";

const initial = RAIL_ENTRIES[0];
const hovered = ref(initial);

function onHover(content) {
  hovered.value = content
    ? RAIL_ENTRIES.find((row) => row.label === content.lead && row.summary === content.text) ?? initial
    : initial;
}

const focusedFoe = ref(FOES[1]);
const stageH = 450;
const boxFor = (foe) => {
  const height = stageH * foe.h;
  const width = height * 0.66;
  const left = 1451 * foe.x - width / 2;
  const top = stageH - height;
  return { width, height, left, top };
};
const plateBox = (foe) => {
  const box = boxFor(foe);
  return {
    left: box.left + box.width / 2 - 56,
    top: Math.max(box.top - 8, 2),
    width: 112,
    height: 52,
  };
};
const repeats = computed(() => {
  const names = FOES.map((foe) => monsterName(foe.identity));
  return (name) => names.filter((value) => value === name).length > 1;
});
const isNamed = (row) => row.identity.individual_name !== null;
</script>

<template>
  <div class="mn-proto" :data-view="view">
    <template v-if="view === 'specimen'">
      <div class="mn-specimen">
        <div class="mn-specimen__scene">
          <PresenceRail :entries="RAIL_ENTRIES" :art-panel="ART_PANEL" motion-level="off" />
        </div>
        <div class="mn-specimen__plates">
          <FigurePlate
            v-for="foe in FOES"
            :key="foe.id"
            :name="monsterName(foe.identity)"
            :token="foe.token"
            :show-token="repeats(monsterName(foe.identity))"
            :identity="foe.id"
            :hp-current="foe.hp"
            :hp-maximum="foe.max"
          />
          <FigurePlate
            :name="monsterName(LONG_NAMED.identity)"
            :token="LONG_NAMED.token"
            :identity="LONG_NAMED.id"
            :hp-current="LONG_NAMED.hp"
            :hp-maximum="LONG_NAMED.max"
          />
          <FigurePlate
            :name="monsterName(FOES[1].identity)"
            :token="FOES[1].token"
            :identity="NAMED_IDENTITY"
            :hp-current="0"
            :hp-maximum="FOES[1].max"
            fallen="defeated"
          />
        </div>
        <div class="mn-specimen__reads">
          <div
            v-for="row in RAIL_ENTRIES.slice(0, 2)"
            :key="row.key"
            class="mn-readout"
            :data-named="isNamed(row) ? 'true' : null"
          >
            <span class="mn-readout__lead">
              <span class="mn-name">{{ monsterName(row.identity) }}</span>
              <span class="mn-tag">{{ monsterDetailTag(row.identity) }}</span>
            </span>
            <p class="mn-readout__text">{{ row.summary }}</p>
          </div>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="mn-stage">
        <div class="mn-stage__scene"></div>
        <div v-if="view === 'combat'" class="mn-stage__veil"></div>

        <div v-if="view === 'exploration'" class="mn-rail">
          <PresenceRail :entries="RAIL_ENTRIES" :art-panel="ART_PANEL" motion-level="full" @hover="onHover" />
        </div>

        <div v-else class="mn-field">
          <img
            v-for="foe in FOES"
            :key="foe.id"
            class="mn-figure"
            :src="FIGURE_ART"
            alt=""
            :data-dim="foe.id === focusedFoe.id ? null : 'true'"
            :style="{
              left: `${boxFor(foe).left}px`,
              top: `${boxFor(foe).top}px`,
              width: `${boxFor(foe).width}px`,
              height: `${boxFor(foe).height}px`,
            }"
            @mouseenter="focusedFoe = foe"
          />
          <FigurePlate
            v-for="foe in FOES"
            :key="`plate-${foe.id}`"
            :name="monsterName(foe.identity)"
            :token="foe.token"
            :show-token="repeats(monsterName(foe.identity))"
            :identity="foe.id"
            :hp-current="foe.hp"
            :hp-maximum="foe.max"
            :box="plateBox(foe)"
            :target="foe.id === focusedFoe.id"
          />
        </div>
      </div>

      <div class="mn-band">
        <div v-if="view === 'exploration'" class="mn-band__panel">
          <div class="mn-readout" :data-named="isNamed(hovered) ? 'true' : null">
            <span class="mn-readout__lead">
              <span class="mn-name">{{ monsterName(hovered.identity) }}</span>
              <span class="mn-tag">{{ monsterDetailTag(hovered.identity) }}</span>
            </span>
            <p class="mn-readout__text">{{ hovered.summary }}</p>
          </div>
        </div>
        <div v-else class="mn-band__panel">
          <div class="mn-prompt">
            <p class="mn-prompt__head">
              <span><strong>裂潮斬</strong><span class="mn-prompt__verb">‧ 選擇目標</span></span>
              <span class="mn-prompt__esc"><kbd>Esc</kbd> 返回</span>
            </p>
            <p class="mn-prompt__focus" :data-named="isNamed(focusedFoe) ? 'true' : null">
              <span class="mn-prompt__glyph" aria-hidden="true">▸</span>
              <span class="mn-name">{{ monsterName(focusedFoe.identity) }}</span>
              <span class="mn-tag">{{ monsterDetailTag(focusedFoe.identity) }}</span>
              <span class="mn-prompt__side">敵方</span>
            </p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style>
.mn-proto {
  position: fixed;
  inset: 0;
  overflow: auto;
  background: var(--ink-950);
  color: var(--paper-100);
  font-family: var(--f-sans);
}

/* --- stage --------------------------------------------------------- */
.mn-stage {
  position: absolute;
  left: 0;
  right: 0;
  top: var(--header-h);
  bottom: var(--band-h);
  overflow: hidden;
}
.mn-stage__scene {
  position: absolute;
  inset: 0;
  background:
    linear-gradient(0deg, #0b0d10 2%, #0b0d1000 45%),
    url(/art/scenes/coastal_path.webp) center 62% / cover;
}
.mn-stage__veil {
  position: absolute;
  inset: 0;
  background: var(--stage-combat-veil);
}
.mn-rail {
  position: absolute;
  right: calc(28px * var(--ui-scale));
  bottom: calc(14px * var(--ui-scale));
}
.mn-field {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 1451px;
  height: 450px;
}
.mn-figure {
  position: absolute;
  object-fit: contain;
  object-position: bottom;
  filter: drop-shadow(0 calc(10px * var(--ui-scale)) calc(18px * var(--ui-scale)) rgba(0, 0, 0, 0.6));
  transition: filter var(--motion-fast) var(--ease-standard);
}
.mn-figure[data-dim] {
  filter: brightness(0.55) saturate(0.7);
}

/* --- command band -------------------------------------------------- */
.mn-band {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: var(--band-h);
  border-top: 1px solid var(--band-edge);
  background: linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel));
}
.mn-band__panel {
  width: min(calc(720px * var(--ui-scale)), 100%);
  margin: calc(22px * var(--ui-scale)) auto 0;
}

/* --- shared name and tag ------------------------------------------- */
.mn-name {
  flex: none;
  color: var(--paper-50);
  /* Fixed, so swapping to the display family cannot move the line below. */
  line-height: calc(24px * var(--ui-scale));
}
.mn-tag {
  flex: none;
  padding: 0 calc(7px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.55);
  border-radius: var(--radius-sm);
  background: rgba(185, 154, 96, 0.1);
  color: var(--gold-300);
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  font-weight: 400;
  line-height: calc(20px * var(--ui-scale));
  letter-spacing: 0.04em;
}

/* --- readout (copy of ExplorationReadout's scoped rules) ------------ */
.mn-readout {
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: calc(4px * var(--ui-scale));
  min-height: calc(64px * var(--ui-scale));
  padding: calc(4px * var(--ui-scale)) calc(14px * var(--ui-scale));
  border-left: 2px solid var(--gold-500);
  background: linear-gradient(90deg, rgba(185, 154, 96, 0.08), transparent 70%);
}
.mn-readout__lead {
  display: flex;
  align-items: center;
  gap: calc(14px * var(--ui-scale));
  min-height: calc(24px * var(--ui-scale));
  font-size: var(--text-sm);
  letter-spacing: 0.08em;
}
.mn-readout__text {
  margin: 0;
  color: var(--paper-100);
  font-size: var(--text-sm);
  line-height: 1.45;
}

/* --- target prompt (copy of ActionDock's scoped rules) -------------- */
.mn-prompt {
  display: flex;
  flex-direction: column;
  gap: calc(6px * var(--ui-scale));
  font-size: var(--text-sm);
  line-height: calc(22px * var(--ui-scale));
}
.mn-prompt p {
  margin: 0;
}
.mn-prompt__head {
  display: flex;
  justify-content: space-between;
  color: var(--paper-300);
}
.mn-prompt__head strong {
  color: var(--gold-300);
  font-weight: 500;
}
.mn-prompt__verb {
  margin-left: calc(6px * var(--ui-scale));
  color: var(--paper-500);
}
.mn-prompt__esc kbd {
  font-family: var(--f-sans);
  color: var(--paper-200);
}
.mn-prompt__focus {
  display: flex;
  align-items: center;
  gap: calc(14px * var(--ui-scale));
  white-space: nowrap;
}
.mn-prompt__glyph {
  color: var(--gold-400);
}
.mn-prompt__side {
  padding: 0 calc(6px * var(--ui-scale));
  border: 1px solid currentColor;
  border-radius: var(--radius-pill);
  background: rgba(150, 40, 36, 0.22);
  color: #f0a59a;
  font-size: var(--text-xs);
  line-height: calc(18px * var(--ui-scale));
}

/* --- specimen board ------------------------------------------------ */
.mn-specimen {
  display: flex;
  flex-direction: column;
  gap: calc(20px * var(--ui-scale));
  min-width: 1100px;
  padding: calc(var(--header-h) + 20px * var(--ui-scale)) calc(32px * var(--ui-scale)) calc(32px * var(--ui-scale));
}
.mn-specimen__scene {
  display: flex;
  justify-content: center;
  padding: calc(44px * var(--ui-scale)) 0 calc(18px * var(--ui-scale));
  border-radius: var(--radius-sm);
  background:
    linear-gradient(0deg, #0b0d10 2%, #0b0d1000 70%),
    url(/art/scenes/coastal_path.webp) center 60% / cover;
}
.mn-specimen__plates {
  display: flex;
  justify-content: center;
  gap: calc(44px * var(--ui-scale));
  padding: calc(16px * var(--ui-scale));
  border-radius: var(--radius-sm);
  background: rgba(64, 84, 92, 0.45);
}
.mn-specimen__reads {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: calc(16px * var(--ui-scale));
}

/* ===================================================================
   The named treatment: rank language, never selection language. Selection in
   this client is a vertical side rule, a single underline, or an outer ring,
   so nothing below uses those. The medallion takes the inner double rule of
   GuildRankCard's stamp, and the name sits between two horizontal gold
   hairlines that fade at both ends, like ChoiceCard's crest and the figure
   plate's crown. Every rule is an out-of-flow overlay or a background layer, and
   the name only swaps its colour and family, so no box differs from an unnamed
   one.
   =================================================================== */
.mn-proto {
  --mn-rule: linear-gradient(90deg, transparent, var(--gold-400) 22%, var(--gold-400) 78%, transparent);
}

/* Rail: an inner rule inside the medallion's clip, hairlines on the name. */
[data-entry-key="target-named"] .presence-rail__medal {
  border-color: var(--gold-300);
}
[data-entry-key="target-named"] .presence-rail__medal::after {
  content: "";
  position: absolute;
  inset: calc(2px * var(--ui-scale));
  z-index: 1;
  border: 1px solid var(--gold-400);
  border-radius: 50%;
  pointer-events: none;
}
[data-entry-key="target-named"] .presence-rail__name {
  border-radius: 0;
  background:
    var(--mn-rule) top / 100% 1px no-repeat,
    var(--mn-rule) bottom / 100% 1px no-repeat,
    linear-gradient(90deg, transparent, rgba(10, 11, 14, 0.82) 12%, rgba(10, 11, 14, 0.82) 88%, transparent);
  color: var(--gold-400);
  font-family: var(--f-display);
}

/* Plate: the crest joins the brass crown, which stays single (a doubled crown
   already means the acting foe). */
.figure-plate[data-identity$="1"] .figure-plate__name-text {
  color: var(--gold-400);
  font-family: var(--f-display);
}
.figure-plate[data-identity$="1"] .figure-plate__name::before {
  content: "";
  position: absolute;
  left: 6%;
  right: 6%;
  top: 0;
  height: 1px;
  background: var(--mn-rule);
}

/* Readout and target prompt: the same two hairlines on the name. */
.mn-readout[data-named] .mn-name,
.mn-prompt__focus[data-named] .mn-name {
  padding: 0 calc(8px * var(--ui-scale));
  margin: 0 calc(-8px * var(--ui-scale));
  background:
    var(--mn-rule) top / 100% 1px no-repeat,
    var(--mn-rule) bottom / 100% 1px no-repeat;
  color: var(--gold-400);
  font-family: var(--f-display);
}
</style>
