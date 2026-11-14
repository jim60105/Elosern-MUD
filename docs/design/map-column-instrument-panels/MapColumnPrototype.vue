<script setup>
// MapColumnPrototype (design prototype, reference only): the right-hand
// island column on a mock stage, in the instrument panel style of
// docs/development/hud-instrument-panels.md. Mock data, not wired to any
// payload.
//
// `layout` picks what stands on the stage:
// - "instrument": the proposal, three separate instrument panels stacked in
//   the column (MapColumnStack only lays them out);
// - "current": the live PlaceCard, LocalMap and ObjectiveTracker, for an
//   A/B flip against the proposal at the same position;
// - "compare": both, side by side, each under its caption.
// The live vitals dock stands lower-left so the two instruments can be
// judged as one HUD.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import LocalMap from "../../../web/webclient-app/components/LocalMap.vue";
import ObjectiveTracker from "../../../web/webclient-app/components/ObjectiveTracker.vue";
import PlaceCard from "../../../web/webclient-app/components/PlaceCard.vue";
import StatusPanel from "../../../web/webclient-app/components/StatusPanel.vue";
import MapColumnStack from "./MapColumnStack.vue";
import LocalMapInstrument from "./LocalMapInstrument.vue";
import ObjectiveLineInstrument from "./ObjectiveLineInstrument.vue";
import PlaceCardInstrument from "./PlaceCardInstrument.vue";

const props = defineProps({
  layout: { type: String, default: "instrument" },
  backdrop: { type: String, default: "city_street" },
  locationLabel: { type: String, default: "城門廣場" },
  timeLabel: { type: String, default: "春季 3 日 ‧ 12:00" },
  actionsEnabled: { type: Boolean, default: true },
  // A derived `local_map` model, or null to leave the minimap out.
  localMap: { type: Object, default: null },
  // The `objectives.rows` array; empty leaves the objective line out.
  rows: { type: Array, default: () => [] },
  // A `status` panel payload for the lower-left vitals dock, or null.
  status: { type: Object, default: null },
  visible: { type: Boolean, default: true },
  motionLevel: { type: String, default: "full" },
});

const log = ref("");
function note(text) {
  log.value = text;
}

const showProposal = computed(() => props.layout !== "current");
const showCurrent = computed(() => props.layout !== "instrument");
const backdropUrl = computed(() => `url("/art/scenes/${props.backdrop}.webp")`);

// An over-tall proposal column scrolls without a scrollbar: a bar would
// stand across the three spines and take its width from the panels, which
// cuts the minimap's short feather to a hard edge. Instead the column's
// clipped edge fades out (the edge with more content behind it), which is
// the same feather the panels use and tells the player there is more.
const proposalSlot = ref(null);
const moreAbove = ref(false);
const moreBelow = ref(false);
function measureEdges() {
  const el = proposalSlot.value;
  if (!el) {
    moreAbove.value = false;
    moreBelow.value = false;
    return;
  }
  moreAbove.value = el.scrollTop > 1;
  moreBelow.value = el.scrollTop + el.clientHeight < el.scrollHeight - 1;
}
let resizeObserver = null;
function observe() {
  resizeObserver?.disconnect();
  const el = proposalSlot.value;
  if (!el || typeof ResizeObserver === "undefined") {
    return;
  }
  resizeObserver = new ResizeObserver(measureEdges);
  resizeObserver.observe(el);
  for (const child of el.children) {
    resizeObserver.observe(child);
  }
  measureEdges();
}
onMounted(observe);
watch(proposalSlot, observe, { flush: "post" });
onBeforeUnmount(() => resizeObserver?.disconnect());
</script>

<template>
  <div class="mcp-stage" :class="`mcp-stage--${layout}`" :style="{ '--mcp-backdrop': backdropUrl }">
    <div v-if="showCurrent" class="mcp-slot mcp-slot--current">
      <p v-if="layout === 'compare'" class="mcp-caption">現行</p>
      <div class="mcp-current">
        <PlaceCard
          :location-label="locationLabel"
          :time-label="timeLabel"
          :actions-enabled="actionsEnabled"
          :motion-level="motionLevel"
        />
        <LocalMap v-if="localMap" :local-map="localMap" :motion-level="motionLevel" />
        <ObjectiveTracker :rows="rows" />
      </div>
    </div>

    <div
      v-if="showProposal"
      ref="proposalSlot"
      class="mcp-slot mcp-slot--proposal"
      :data-more-above="moreAbove || null"
      :data-more-below="moreBelow || null"
      @scroll.passive="measureEdges"
    >
      <p v-if="layout === 'compare'" class="mcp-caption">提案</p>
      <MapColumnStack :visible="visible" :motion-level="motionLevel">
        <PlaceCardInstrument
          :location-label="locationLabel"
          :time-label="timeLabel"
          :actions-enabled="actionsEnabled"
          :motion-level="motionLevel"
          @look-room="note('查看房間')"
          @wait="note('休息')"
        />
        <LocalMapInstrument
          v-if="localMap"
          :local-map="localMap"
          :motion-level="motionLevel"
          @open-map="note('開啟地圖')"
          @move="note('移動')"
        />
        <ObjectiveLineInstrument :rows="rows" />
      </MapColumnStack>
    </div>

    <div v-if="status" class="mcp-vitals">
      <StatusPanel :status="status" :visible="true" />
    </div>
    <div class="mcp-band" aria-hidden="true"></div>
    <p class="mcp-log" role="status">{{ log }}</p>
  </div>
</template>

<style scoped>
.mcp-stage {
  position: relative;
  height: calc(100vh - var(--header-h));
  min-height: calc(560px * var(--ui-scale));
  overflow: hidden;
  background:
    linear-gradient(180deg, rgba(11, 13, 16, 0.1), rgba(11, 13, 16, 0.35)),
    var(--mcp-backdrop) center / cover no-repeat;
}
/* The `map` anchor's geometry as the live client sets it (app-shell.css). */
.mcp-slot {
  position: absolute;
  top: var(--stage-inset-y, calc(16px * var(--ui-scale)));
  right: calc(16px * var(--ui-scale));
  width: calc(var(--right-column, 22vw) - 28px * var(--ui-scale));
  /* The live anchor's bound: above the band, scrolling inside, clipped
     sideways, so a too-tall column behaves here as it does in the client. */
  max-height: calc(100% - var(--band-h, 27.85vh) - 2 * var(--stage-inset-y, 16px));
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-width: thin;
}
/* The proposal's column is never narrower than the minimap instrument
   needs (canvas 240 + spine clearance 22 + feather 20): the live width at
   1451x790, 282px at 1280x720. */
.mcp-slot--proposal {
  --mcp-fade-top: 0px;
  --mcp-fade-bottom: 0px;
  width: max(calc(var(--right-column, 22vw) - 28px * var(--ui-scale)), calc(282px * var(--ui-scale)));
  scrollbar-width: none;
}
.mcp-slot--proposal::-webkit-scrollbar {
  display: none;
}
/* The clipped edge feathers out only while content is behind it, so a
   column that fits keeps its own panels' edges untouched. */
.mcp-slot--proposal[data-more-above] {
  --mcp-fade-top: calc(32px * var(--ui-scale));
}
.mcp-slot--proposal[data-more-below] {
  --mcp-fade-bottom: calc(32px * var(--ui-scale));
}
.mcp-slot--proposal[data-more-above],
.mcp-slot--proposal[data-more-below] {
  -webkit-mask-image: linear-gradient(180deg, transparent 0, #000 var(--mcp-fade-top), #000 calc(100% - var(--mcp-fade-bottom)), transparent 100%);
  mask-image: linear-gradient(180deg, transparent 0, #000 var(--mcp-fade-top), #000 calc(100% - var(--mcp-fade-bottom)), transparent 100%);
}
.mcp-stage--compare .mcp-slot--current {
  right: calc(var(--right-column, 22vw) + 40px * var(--ui-scale));
}
.mcp-current {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: calc(14px * var(--ui-scale));
}
.mcp-caption {
  margin: 0 0 calc(6px * var(--ui-scale));
  text-align: right;
  font: var(--text-xs)/1.2 var(--f-serif);
  letter-spacing: 0.18em;
  color: var(--paper-100);
  text-shadow: 0 1px 2px #000;
}
.mcp-vitals {
  position: absolute;
  left: calc(16px * var(--ui-scale));
  bottom: var(--band-h, 27.85vh);
  width: var(--vitals-dock-w, 25vw);
}
.mcp-band {
  position: absolute;
  inset: auto 0 0 0;
  height: var(--band-h, 27.85vh);
  background: linear-gradient(180deg, rgba(15, 12, 18, 0.94), rgba(11, 9, 13, 0.98));
  border-top: 1px solid var(--band-edge);
}
.mcp-log {
  position: absolute;
  left: calc(20px * var(--ui-scale));
  bottom: calc(14px * var(--ui-scale));
  margin: 0;
  font: var(--text-xs)/1.3 var(--f-mono);
  color: var(--paper-500);
}
</style>
