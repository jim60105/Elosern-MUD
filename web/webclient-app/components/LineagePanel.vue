<script setup>
// LineagePanel (skill-lineage-panel v2): the transitional big-window skill
// graph view rendered inside OverlayHost's body slot. Every rendered value
// comes from the committed `lineage` panel payload alone — the client
// recomputes no growth rules: levels, XP bands, 見頂/可解鎖 marks,
// prerequisite lines, graph counts and the header counts are the server's
// derived view, serialized verbatim. A graph omitted from the payload
// (truncated) or the whole panel unavailable renders no placeholder graph and
// no invented progress.
//
// Graph interaction is client-local view state only: which graphs are
// expanded. A collapsed graph renders its identity and owned/total count;
// expanding renders the per-node rows. The chain meter is gone: progress is
// the server's owned/total count and each node's own level band.
import { computed, ref } from "vue";

const props = defineProps({
  // The committed `lineage` panel payload (schema version 2), or null when
  // no panel has ever been committed.
  lineage: { type: Object, default: null },
});

const available = computed(
  () => !!props.lineage && props.lineage.available !== false,
);

// The fallback line for a panel that was never committed at all; a panel
// delivered in its unavailable form always carries the registry reason.
const FALLBACK_REASON = "技能系譜目前無法顯示";

const graphs = computed(() =>
  available.value && Array.isArray(props.lineage.graphs)
    ? props.lineage.graphs
    : [],
);

// Client-local expand/collapse state, keyed by graph id. The default is
// collapsed (the ledger reads as a per-graph progress board first).
const expanded = ref(new Set());

function toggleGraph(graphId) {
  const next = new Set(expanded.value);
  if (next.has(graphId)) {
    next.delete(graphId);
  } else {
    next.add(graphId);
  }
  expanded.value = next;
}

// Display-only normalization: practice XP is a float, the payload's
// xp_into_level / xp_to_next_level pair is the node's own level band. No
// growth rule is evaluated here — only the stored pair is formatted.
function formatXp(value) {
  return Number.isInteger(value) ? String(value) : String(Math.round(value * 10) / 10);
}

// The graph's disambiguating subtitle (webclient-contextual-hud): the
// supplied root nodes' display names joined with ‧, so two graphs sharing an
// element/style label stay distinguishable. Omitted when absent or equal to
// the label; no name is ever derived from a skill key.
function rootSubtitle(graph) {
  const byKey = new Map(
    (Array.isArray(graph.nodes) ? graph.nodes : []).map((node) => [
      node.skill_key,
      node.display_name_zh,
    ]),
  );
  const names = (Array.isArray(graph.root_keys) ? graph.root_keys : [])
    .map((key) => byKey.get(key))
    .filter((name) => typeof name === "string" && name);
  const joined = names.join("‧");
  return joined && joined !== graph.group_label_zh ? joined : "";
}

function nodeMeter(node) {
  return `${formatXp(node.xp_into_level)}/${formatXp(node.xp_into_level + node.xp_to_next_level)} → 下一階`;
}
</script>

<template>
  <div class="lineage-panel" data-testid="lineage-panel">
    <p
      v-if="!available"
      class="lineage-panel__unavailable"
      data-testid="lineage-panel-unavailable"
    >
      {{ (lineage && lineage.reason && lineage.reason.message) || FALLBACK_REASON }}
    </p>
    <template v-else>
      <p class="lineage-panel__header" data-testid="lineage-panel-header">
        已完成 {{ lineage.completed_count }} / {{ lineage.total_count }} 樹
      </p>
      <p
        v-if="graphs.length === 0"
        class="lineage-panel__empty"
        data-testid="lineage-panel-empty"
      >
        目前尚無可追蹤的技能系譜。
      </p>
      <section
        v-for="graph in graphs"
        :key="graph.graph_id"
        class="lineage-graph"
        :data-testid="`lineage-graph-${graph.graph_id}`"
      >
        <button
          type="button"
          class="lineage-graph__head"
          :aria-expanded="expanded.has(graph.graph_id) ? 'true' : 'false'"
          :data-testid="`lineage-graph-toggle-${graph.graph_id}`"
          @click="toggleGraph(graph.graph_id)"
        >
          <svg
            class="lineage-graph__chevron"
            :class="{ 'lineage-graph__chevron--open': expanded.has(graph.graph_id) }"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.9"
            aria-hidden="true"
          >
            <path d="M9 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span class="lineage-graph__identity">
            <span class="lineage-graph__label">{{ graph.group_label_zh }}</span>
            <span
              v-if="rootSubtitle(graph)"
              class="lineage-graph__root"
              :data-testid="`lineage-graph-root-${graph.graph_id}`"
              >{{ rootSubtitle(graph) }}</span
            >
          </span>
          <span
            v-if="graph.consumed"
            class="lineage-graph__consumed"
            data-testid="lineage-graph-consumed"
            >已全數見頂</span
          >
          <span
            v-else
            class="lineage-graph__count"
            :data-testid="`lineage-graph-count-${graph.graph_id}`"
            >{{ graph.owned_count }}/{{ graph.total_count }}</span
          >
        </button>
        <ul
          v-if="expanded.has(graph.graph_id)"
          class="lineage-graph__nodes"
          :data-testid="`lineage-graph-nodes-${graph.graph_id}`"
        >
          <li
            v-for="node in graph.nodes"
            :key="node.skill_key"
            class="lineage-node"
            :class="{ 'lineage-node--locked': !node.usable }"
            :data-testid="`lineage-node-${node.skill_key}`"
          >
            <span class="lineage-node__name"
              >{{ node.display_name_zh }} Lv.{{ node.level }}</span
            >
            <span
              v-if="node.capped"
              class="lineage-node__tip"
              data-testid="lineage-node-tip"
              >（見頂）</span
            >
            <span
              v-else-if="node.owned"
              class="lineage-node__meter"
              :data-testid="`lineage-node-meter-${node.skill_key}`"
              >{{ nodeMeter(node) }}</span
            >
            <span
              v-if="node.ready"
              class="lineage-node__ready"
              :data-testid="`lineage-node-ready-${node.skill_key}`"
              >（可解鎖）</span
            >
            <span
              v-if="node.prereq_text_zh"
              class="lineage-node__prereq"
              :data-testid="`lineage-node-prereq-${node.skill_key}`"
              >{{ node.prereq_text_zh }}</span
            >
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.lineage-panel {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  min-width: 0;
}

.lineage-panel__unavailable,
.lineage-panel__empty {
  margin: 0;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.lineage-panel__header {
  margin: 0;
  padding: 0 0 var(--sp-3);
  border-bottom: var(--line);
  font-family: var(--f-serif);
  font-size: var(--text-2xl);
  color: var(--gold-400);
}

.lineage-graph {
  border: var(--line);
  border-radius: var(--radius);
  background: var(--panel);
  overflow: hidden;
}

/* The collapsed graph row (webclient-contextual-hud): a compact ~56px row —
   chevron, identity (label over its joined root-node subtitle), then the
   owned/total count (or 已全數見頂) right beside it. The identity column is
   shared by every row, so the counts align; there is no chain meter. */
.lineage-graph__head {
  display: grid;
  grid-template-columns: calc(14px * var(--ui-scale)) minmax(0, 1fr) auto;
  align-items: center;
  column-gap: var(--sp-3);
  width: 100%;
  min-height: calc(56px * var(--ui-scale));
  box-sizing: border-box;
  padding: var(--sp-2) var(--sp-4);
  color: var(--paper-100);
  background: transparent;
  border: 0;
  cursor: pointer;
  text-align: left;
  font: inherit;
}

.lineage-graph__head:hover {
  background: var(--gold-glow);
}

.lineage-graph__head:focus-visible {
  outline: 1px solid var(--gold-400);
  outline-offset: -2px;
}

.lineage-graph__chevron {
  flex: none;
  width: calc(14px * var(--ui-scale));
  height: calc(14px * var(--ui-scale));
  color: var(--paper-500);
  transition: transform var(--motion-fast) ease;
}

.lineage-graph__chevron--open {
  transform: rotate(90deg);
}

.lineage-graph__identity {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 2px var(--sp-2);
  min-width: 0;
}

.lineage-graph__label {
  overflow-wrap: anywhere;
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  color: var(--paper-50);
}

.lineage-graph__root {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--paper-500);
  font-size: var(--text-sm);
}

.lineage-graph__consumed {
  color: var(--gold-400);
  font-size: var(--text-sm);
  white-space: nowrap;
}

.lineage-graph__count {
  min-width: 5ch;
  color: var(--paper-300);
  font-size: var(--text-sm);
  font-variant-numeric: tabular-nums lining-nums;
  white-space: nowrap;
}

.lineage-graph__nodes {
  margin: 0;
  padding: 0 var(--sp-4) var(--sp-4) calc(42px * var(--ui-scale));
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.lineage-node {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  padding: var(--sp-2) var(--sp-3);
  border-left: 2px solid var(--gold-500);
  background: var(--ink-900);
  overflow-wrap: anywhere;
  gap: calc(6px * var(--ui-scale)) var(--sp-3);
  font-size: var(--text-sm);
}

.lineage-node__name {
  color: var(--paper-50);
}

.lineage-node--locked .lineage-node__name {
  color: var(--paper-500);
}

.lineage-node__tip {
  color: var(--gold-400);
}

.lineage-node__ready {
  color: var(--gold-300, var(--gold-400));
}

.lineage-node__meter {
  color: var(--paper-300);
  font-variant-numeric: tabular-nums lining-nums;
}

.lineage-node__prereq {
  flex-basis: 100%;
  color: var(--paper-300);
  line-height: 1.7;
}
</style>
