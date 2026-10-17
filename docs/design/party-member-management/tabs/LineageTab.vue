<script setup>
// Approved visual prototype (party member management §6.5): the 系譜 tab.
// The unit is a connected skill graph (lineage v2): grouped by element or
// style, one diamond per node (filled capped, half owned, dashed locked),
// owned/total, 可解鎖 when a prerequisite is met. The detail draws the graph
// by depth with merge nodes once and leveled edges.
import { computed, ref, watch } from "vue";
import PmGlyph from "../PmGlyph.vue";
import { LINEAGE } from "../prototype-data.js";

const props = defineProps({
  member: { type: Object, required: true },
  initialGraph: { type: String, default: null },
});
const emit = defineEmits(["open-skill"]);

const ELEMENT = {
  ice: { glyph: "ice", color: "#8fc6e0" },
  holy: { glyph: "holy", color: "var(--gold-300)" },
  wind: { glyph: "wind", color: "#8fd0a8" },
  staff: { glyph: "staff", color: "#c9a46a" },
};

const graphs = computed(() => LINEAGE[props.member.id] ?? []);
const grouped = computed(() => {
  const out = [];
  for (const g of graphs.value) {
    let bucket = out.find((b) => b.group === g.group);
    if (!bucket) out.push((bucket = { group: g.group, element: g.element, graphs: [] }));
    bucket.graphs.push(g);
  }
  return out;
});
const owned = (g) => g.nodes.filter((n) => n.state !== "locked").length;
// 可解鎖: an unowned node whose prerequisite is met (empty prerequisite text).
const ready = (g) => g.nodes.some((n) => n.state === "locked" && !n.prereq);
const total = computed(() => graphs.value.reduce((n, g) => n + g.nodes.length, 0));
const learned = computed(() => graphs.value.reduce((n, g) => n + owned(g), 0));

const selected = ref(null);
watch(
  () => props.member.id,
  () => {
    selected.value = graphs.value.find((g) => g.id === props.initialGraph)?.id ?? graphs.value[0]?.id ?? null;
  },
  { immediate: true },
);
const graph = computed(() => graphs.value.find((g) => g.id === selected.value) ?? null);

// Layout: columns from each node's `col`, rows from its depth.
const layout = computed(() => {
  if (!graph.value) return null;
  const cols = Math.max(...graph.value.nodes.map((n) => n.col)) + 1;
  const rows = Math.max(...graph.value.nodes.map((n) => n.depth)) + 1;
  const pos = Object.fromEntries(
    graph.value.nodes.map((n) => [n.key, { x: ((n.col + 0.5) / cols) * 100, y: ((n.depth + 0.5) / rows) * 100 }]),
  );
  const edges = graph.value.edges.map(([from, to, level]) => {
    const a = pos[from];
    const b = pos[to];
    const mid = (a.y + b.y) / 2;
    return { key: `${from}-${to}`, d: `M${a.x} ${a.y} C${a.x} ${mid} ${b.x} ${mid} ${b.x} ${b.y}`, level, lx: (a.x + b.x) / 2, ly: mid, locked: graph.value.nodes.find((n) => n.key === to).state === "locked" };
  });
  return { rows, pos, edges };
});
</script>

<template>
  <div class="pm-col pm-list">
    <div class="ln-head">
      <span class="ln-total">{{ learned }} / {{ total }}</span>
    </div>
    <template v-for="b in grouped" :key="b.group">
      <div class="pm-sech" :style="{ color: ELEMENT[b.element].color }"><span class="ln-el" :style="{ borderColor: ELEMENT[b.element].color }"><PmGlyph :name="ELEMENT[b.element].glyph" /></span>{{ b.group }}</div>
      <button
        v-for="g in b.graphs"
        :key="g.id"
        type="button"
        role="option"
        class="pm-row ln-row"
        :class="{ 'is-selected': g.id === selected }"
        :aria-selected="g.id === selected"
        @click="selected = g.id"
      >
        <span>
          <span class="pm-row__name">{{ g.roots.join(" ‧ ") }}</span><span v-if="ready(g)" class="pm-tag pm-tag--new">可解鎖</span>
          <span class="ln-pips" :aria-label="`${owned(g)} / ${g.nodes.length}`">
            <i v-for="n in g.nodes" :key="n.key" class="ln-pip" :class="`is-${n.state}`" />
          </span>
        </span>
        <span class="pm-row__end">{{ owned(g) }} / {{ g.nodes.length }}</span>
      </button>
    </template>
  </div>

  <div class="pm-col pm-detail">
    <template v-if="graph && layout">
      <span class="pm-ribbon"><PmGlyph :name="ELEMENT[graph.element].glyph" />{{ graph.group }} ‧ {{ graph.roots.join(" ‧ ") }}</span>
      <div class="ln-canvas" :style="{ '--rows': layout.rows }">
        <svg class="ln-edges" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path v-for="e in layout.edges" :key="e.key" :d="e.d" :class="{ 'is-locked': e.locked }" vector-effect="non-scaling-stroke" />
        </svg>
        <span v-for="e in layout.edges" :key="`l-${e.key}`" class="ln-edge-label" :style="{ left: `${e.lx}%`, top: `${e.ly}%` }">Lv {{ e.level }}</span>
        <button
          v-for="n in graph.nodes"
          :key="n.key"
          type="button"
          class="ln-node"
          :class="[`is-${n.state}`, { 'is-current': n.current }]"
          :style="{ left: `${layout.pos[n.key].x}%`, top: `${layout.pos[n.key].y}%` }"
          @click="n.state !== 'locked' && emit('open-skill', n.key)"
        >
          <b>{{ n.name }}</b>
          <template v-if="n.state === 'capped'">見頂<span class="pm-meter pm-meter--capped"><i style="width: 100%" /></span></template>
          <template v-else-if="n.state === 'owned'">Lv {{ n.level }} ‧ {{ Math.round(n.progress * 100) }}%<span class="pm-meter"><i :style="{ width: `${Math.round(n.progress * 100)}%` }" /></span></template>
          <template v-else-if="n.prereq">{{ n.prereq }}</template>
          <template v-else><span class="ln-ready">可解鎖</span></template>
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ln-head { display: flex; align-items: center; gap: var(--sp-4); margin-bottom: var(--sp-2); color: var(--paper-500); font-size: var(--text-xs); }
.ln-total { margin-left: auto; font-variant-numeric: tabular-nums; }
.ln-el { display: grid; place-items: center; width: calc(24px * var(--ui-scale)); height: calc(24px * var(--ui-scale)); border: 1px solid; border-radius: 50%; font-size: calc(14px * var(--ui-scale)); }
.ln-row { grid-template-columns: minmax(0, 1fr) auto; }
.ln-pips { display: flex; flex-wrap: wrap; gap: calc(8px * var(--ui-scale)); margin-top: var(--sp-2); padding-left: 2px; }
.ln-pip {
  display: inline-block;
  width: calc(11px * var(--ui-scale));
  height: calc(11px * var(--ui-scale));
  transform: rotate(45deg);
  border: 1px solid var(--gold-600);
}
.ln-pip.is-capped { background: var(--gold-400); border-color: var(--gold-300); }
.ln-pip.is-owned { background: linear-gradient(135deg, var(--gold-500) 50%, transparent 50%); }
.ln-pip.is-locked { border-style: dashed; border-color: var(--paper-700); }
.ln-canvas { position: relative; flex: 1; min-height: calc(var(--rows) * 96px * var(--ui-scale)); max-height: calc(var(--rows) * 150px * var(--ui-scale)); margin-top: var(--sp-2); }
.ln-edges { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
.ln-edges path { fill: none; stroke: rgba(185, 154, 96, 0.5); stroke-width: 1.5; }
.ln-edges path.is-locked { stroke-dasharray: 4 4; stroke: rgba(170, 166, 158, 0.4); }
.ln-edge-label { position: absolute; transform: translate(6px, -50%); color: var(--paper-500); font: var(--text-xs) var(--f-num); pointer-events: none; }
.ln-node {
  position: absolute;
  transform: translate(-50%, -50%);
  width: calc(150px * var(--ui-scale));
  padding: var(--sp-2) var(--sp-2);
  color: var(--paper-400);
  font-size: var(--text-xs);
  text-align: center;
  line-height: 1.5;
  background: var(--pm-list-bg);
  border: 1px solid var(--pm-line);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.ln-node b { display: block; color: var(--paper-50); font: 500 var(--text-sm) var(--f-serif); }
.ln-node .pm-meter { display: block; margin-top: var(--sp-1); }
.ln-node.is-capped { border-color: var(--gold-400); box-shadow: 0 0 8px rgba(228, 200, 142, 0.25); }
.ln-node.is-current { border-color: var(--seal-500); box-shadow: 0 0 0 1px var(--seal-700); }
.ln-node.is-locked { color: var(--paper-700); border-style: dashed; cursor: default; }
.ln-node.is-locked b { color: var(--paper-500); }
.ln-ready { color: var(--seal-400); }
</style>
